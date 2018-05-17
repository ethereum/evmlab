import os, shutil
from web3 import Web3
from . import etherchain
from . import multiapi

def getApi(url):
    web3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 60}))
    chain = etherchain.EtherChainAPI()
    return multiapi.MultiApi(web3 = web3, etherchain = chain)

def checksumAddress(lcAddress):
    return Web3.toChecksumAddress(lcAddress)


def saveFiles(destination, artefacts):
    """
    Copies the supplied artefacts to the right folder

    TODO: Add option to save files into a zip file for download instead
    """

    print("Saving files")
    print("")
    saved = {}

    for desc, path in artefacts.items():
        if os.path.isfile(path):
            fname = os.path.basename(path)
            shutil.copy(path, destination)
            saved[desc] = {'path': destination,'name': fname}
            print("* %s -> %s%s" % (desc, destination, fname) )
        else:
            print("Failed to save %s - not a file" % path)

    return saved
