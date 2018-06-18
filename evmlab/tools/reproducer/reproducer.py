#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import sys, os
import argparse
import re
import zipfile
import tempfile
import logging

from evmlab import reproduce, utils
from evmlab import vm as VMUtils

logger = logging.getLogger(__name__)

try:
    import flask
    app = flask.Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    logger.info("Flask init: template_folder: %s" % os.path.join(os.path.dirname(__file__), 'templates'))
except ImportError:
    logger.warning("Flask not installed, disabling web mode")
    app = None

OUTPUT_DIR = tempfile.mkdtemp(prefix="evmlab")


def create_zip_archive(input_files, output_archive):
    """
    Bundles artefacts into a zip-file

    @param input_artefacts - map of files to save
    @param output_archive prefix to zip-file name
    """
    logger.debug("creating zip archive %s for input artefacts:")
    zipf = zipfile.ZipFile(output_archive, 'w', zipfile.ZIP_DEFLATED)
    for location, name in input_files:
        logger.debug("adding %s as %s to archive..." % (location, name))
        zipf.write(location, name)
    zipf.close()


if app:
    hash_regexp = re.compile("0x[0-9a-f]{64}")


    @app.route("/")
    def test():
        logger.debug("rendering index...")
        return flask.render_template("index.html")


    @app.route('/reproduce/<txhash>')
    def reproduce_tx(txhash):
        logger.debug("reproducing transaction %s" % txhash)

        # Verify input
        if not hash_regexp.match(txhash):
            logger.debug("rendering index(invalid tx hash)...")
            return flask.render_template("index.html", message="Invalid tx hash")

        try:
            artefacts, vm_args = reproduce.reproduceTx(txhash, app.vm, app.api)
            logger.debug("done reproducing transaction trace...")
        except Exception as e:
            logger.exception("exception thrown while reproducing transaction...")
            return flask.render_template("index.html", message=str(e))

        logger.debug("saving artefacts to %s" % OUTPUT_DIR)
        saved_files = utils.saveFiles(OUTPUT_DIR, artefacts)

        # Some tricks to get the right command for local replay
        p_gen = saved_files['parity genesis']['name']
        g_gen = saved_files['geth genesis']['name']
        vm_args['genesis'] = g_gen
        command = app.vm.makeCommand(**vm_args)
        logger.debug("vm command: %s" % command)

        logger.debug("creating zip archive for artefacts")
        prefix = txhash[:8]
        output_archive = os.path.join(OUTPUT_DIR, "%s.zip" % prefix)

        # create a list of files to pack with zipFiles
        input_files = [(os.path.join(v['path'], v['name']), v['name']) for v in saved_files]

        create_zip_archive(input_files=input_files, output_archive=output_archive)

        logger.debug("rendering reproduce_tx...")
        return flask.render_template("index.html",
                                     files=saved_files, zipfile="%s.zip" % prefix,
                                     message="Transaction tracing seems to have been successfull. Use the following command to execute locally",
                                     code=" \\\n\t".join(command))


    @app.route('/download/<path:filename>')
    def download_file(filename):
        logger.debug("rendering download_file...")
        return flask.send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


def test(vm, api):
    print("Doing tests")
    # Jumpdest-analysis attack
    tx = ""
    # Parity-wallet attack
    tx = "0x9dbf0326a03a2a3719c27be4fa69aacc9857fd231a8d9dcaede4bb083def75ec"
    # tenx token transfer (should include SLOADS)
    tx = "0xd6d519043d40691a36c9e718e47110309590e6f47084ac0ec00b53718e449fd3"

    return reproduce.reproduceTx(tx, vm, api)


def main():
    description = """
Tool to reproduce on-chain events locally. 
This can run either as a command-line tool, or as a webapp using a built-in flask interface.
    """
    examples = """
Examples

# Reproduce a tx with a local evm binary
python3 reproducer.py --no-docker -g ~/go/src/github.com/ethereum/go-ethereum/build/bin/evm --hash 0xd6d519043d40691a36c9e718e47110309590e6f47084ac0ec00b53718e449fd3 

# Reproduce a tx with a docker evm
python3 reproducer.py -g holiman/gethvm --hash 0xd6d519043d40691a36c9e718e47110309590e6f47084ac0ec00b53718e449fd3

# Start the reproducer webapp using the default geth docker image: 
python3 reproducer.py -w localhost

Unfinished: 

* This does not _quite_ work with parity, yet, because parity does not load the code in genesis for the 'to'
  -account, it expects the code to be given as an argument. 

    """
    parser = argparse.ArgumentParser(description=description, epilog=examples,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    evmchoice = parser.add_mutually_exclusive_group()
    evmchoice.add_argument('-g', '--geth-evm', type=str,
                           help="Geth EVM binary or docker image name", default="holiman/gethvm")
    evmchoice.add_argument('-p', '--parity-evm', type=str, default=None,
                           help="Parity EVM binary or docker image name")

    parser.add_argument("--no-docker", action="store_true",
                        help="Set to true if using a local binary instead of a docker image")

    web_or_direct = parser.add_mutually_exclusive_group()
    web_or_direct.add_argument('-x', '--hash', type=str,
                               help="Don't run webapp, just lookup hash")
    if app:
        web_or_direct.add_argument('-w', '--www', type=str, help="Run webapp on given interface (interface:port)")
        parser.add_argument('-d', '--debug', action="store_true", default=False,
                            help="Run flask in debug mode (WARNING: debug on in production is insecure)")

    parser.add_argument('-t', '--test', action="store_true", default=False,
                        help="Dont run webapp, only local tests")

    web3settings = parser.add_argument_group('Web3', 'Settings about where to fetch information from (default infura)')
    web3settings.add_argument("--web3", type=str, default="https://mainnet.infura.io/",
                              help="Web3 API url to fetch info from (default 'https://mainnet.infura.io/'")

    args = parser.parse_args()

    # end of arg handling

    if args.parity_evm:
        vm = VMUtils.ParityVM(args.parity_evm, not args.no_docker)
    else:
        vm = VMUtils.GethVM(args.geth_evm, not args.no_docker)

    api = utils.getApi(args.web3)

    if args.test:
        artefacts = test(vm, api)
        import pprint
        pprint.PrettyPrinter().pprint(artefacts)
        sys.exit(0)

    if app and args.www:
        if ':' in args.www:
            host, port = args.www.split(':')
            port = port
        else:
            host = args.www
            port = 5000

        app.debug = args.debug
        app.api = api
        app.vm = vm
        app.run(host=host, port=port)

    elif args.hash:
        artefacts, vm_args = reproduce.reproduceTx(args.hash, vm, api)
        saved_files = utils.saveFiles(OUTPUT_DIR, artefacts)

        # Some tricks to get the right command for local replay
        p_gen = saved_files['parity genesis']['name']
        g_gen = saved_files['geth genesis']['name']
        vm_args['genesis'] = "%s/%s" % (OUTPUT_DIR, g_gen)

        print("\nCommand to execute locally (geth):\n")
        print("%s" % " ".join(vm.makeCommand(**vm_args)))
        print("\nWith memory:\n")
        vm_args['memory'] = True
        print("%s" % " ".join(vm.makeCommand(**vm_args)))
        vm_args.pop('json', None)
        vm_args.pop('memory', None)
        vm_args['statdump'] = "true"
        print("\nFor benchmarking:\n")
        print("%s" % " ".join(vm.makeCommand(**vm_args)))

        print("\nFor opviewing:\n")
        print("python3 opviewer.py -f %s/%s" % (saved_files['json-trace']['path'], saved_files['json-trace']['name']))

        print("\nFor opviewing with sources:\n")
        print(
            "python3 opviewer.py -f %s/%s --web3 '%s' -s path_to_contract_dir -j path_to_solc_combined_json --hash %s" % (
            saved_files['json-trace']['path'], saved_files['json-trace']['name'], args.web3, args.hash))

        logger.debug("creating zip archive for artefacts")
        prefix = args.hash[:8]
        output_archive = os.path.join(OUTPUT_DIR, "%s.zip" % prefix)
        # create a list of files to pack with zipFiles
        input_files = [(os.path.join(v['path'], v['name']), v['name']) for v in saved_files]
        create_zip_archive(input_files=input_files, output_archive=output_archive)

        print("\nZipped files into %s" % output_archive)

    else:
        parser.print_usage()


if __name__ == '__main__':
    logging.basicConfig(format='[%(filename)s - %(funcName)20s() ][%(levelname)8s] %(message)s',
                        level=logging.INFO)
    main()
