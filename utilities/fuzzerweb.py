#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import fuzzer, sys, os, threading
import logging
logger = logging.getLogger()

try:
    import flask
    templates = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    app = flask.Flask(__name__, template_folder=templates)
    logger.info("Flask init: template_folder: %s" % templates)
except ImportError:
    logger.warning("Flask not installed, disabling web mode")
    sys.exit(1)


f = fuzzer.configFuzzer()
executor = fuzzer.TestExecutor(fuzzer=f)
 
@app.route("/")
def index():
    return flask.render_template("index.html", status = executor.status(), config = f._config.info)

@app.route("/download/")
@app.route("/download/<artefact>")
def download(artefact = None):
    """ Download a file -- only artefacts allowed """

    artefactDir = fuzzer._config.artefacts
    print("downlaod '%s'" % artefact)
    if artefact == None or artefact.strip() == "":
        # file listing
        print("filelist")
        return flask.render_template("listing.html", files = sorted(os.listdir(artefactDir), reverse=True) )

    insecure_fullpath = os.path.realpath(os.path.join(artefactDir, artefact))
    # Now check that the path is a subdir of artefact idr
    if not insecure_fullpath.startswith(artefactDir):
        return "Meh, nice try"

    return flask.send_from_directory(artefactDir, artefact, as_attachment=True)

def flaskRunner(host, port ):
    app.run(host, port)

def main():
    host = "localhost"
    port = 8080

    thread = threading.Thread(target=flaskRunner, args = (host, port))
    thread.start()

    # Start all docker daemons that we'll use during the execution
    f.start_daemons()
    executor.startFuzzing()


if __name__ == '__main__':
#    testSummary()
    main()
