import os, shutil
from web3 import Web3, RPCProvider
from urllib.parse import urlparse
from . import multiapi, etherchain

def getApi(providerUrl):
    parsed_web3 = urlparse(providerUrl)
    if not parsed_web3.hostname:
        #User probably omitted 'http://'
        parsed_web3 = urlparse("http://%s" % providerUrl)

    ssl = (parsed_web3.scheme == 'https')
    port = parsed_web3.port

    if not port:
        #Not explicitly defined
        if ssl:
            port = 443
        else:
            port = 80
    web3 = Web3(RPCProvider(host = parsed_web3.hostname,port= port ,ssl= ssl))
    api = multiapi.MultiApi(web3 = web3, etherchain = etherchain.EtherChainAPI())

    return api

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
