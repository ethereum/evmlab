
import os
import requests
import json

here = os.path.dirname(os.path.abspath(__file__))

def log(x):
    print("[+] %s" % x)


def savejson(fname, obj):
    fqfn = '%s/datastore/%s' % (here, fname)
    with open(fqfn, 'w+') as outfile:
        outfile.write(json.dumps(obj))

    log("Wrote file %s" % fqfn)

def loadjson(fname):
#   return None
    try:
        with open('%s/datastore/%s' % (here, fname), 'r') as infile:
            return json.loads(infile.read())
    except Exception, e:
        print(e)
        return None


class EtherChainAPI():

    def __init__(self, offline = False):
        self.offline = offline
        self.cachedBlocks = None
        self.flushcounter = 0

    def getBlockInfo(self, blockNumberOrHash):
        """
        Fields :
            {"number":101010
            ,"hash":"0x3e5c2f13bc01a0a32c7eda3560ec3ede19c9d2f6c0fda8436999eee2914e862d"
            ,"parentHash":"0x8290679004240a002dcf274bf56310c2654b5137c643e5c20ff647ebda61033b"
            ,"uncleHash":"0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347"
            ,"coinbase":"0xc603ab5ef41fc61aa8b76beddb09e3cfcbb174bd"
            ,"root":"0x3df3a270c940336f7585d9b62a37fa04b2e2794f3267915f65b202e37a93c4e5"
            ,"txHash":"0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421"
            ,"difficulty":3871451743585
            ,"gasLimit":3141592
            ,"gasUsed":0
            ,"time":"2015-08-17T12:53:09.000Z"
            ,"extra":"0x476574682f76312e302e312f77696e646f77732f676f312e342e32"
            ,"mixDigest":null
            ,"nonce":"0xeaedaa0e2baa6334"
            ,"tx_count":0
            ,"uncle_count":0
            ,"size":544
            ,"blockTime":1
            ,"reward":5000000000000000000}      
        """
        # Load cached data
        if self.cachedBlocks == None:
            self.cachedBlocks = loadjson(".blocks.json") or {}

        if(self.cachedBlocks.has_key(blockNumberOrHash)):
            return self.cachedBlocks[blockNumberOrHash]


        url = "https://etherchain.org/api/block/%s"  % str(blockNumberOrHash)
        log(url)
        data = requests.get(url).json()['data'][0]

        #save
        self.cachedBlocks[data['hash']] = data
        self.cachedBlocks[data['number']] = data

        self.flushcounter = self.flushcounter+1
        if self.flushcounter > 50:#Always on now
            savejson('.blocks.json', self.cachedBlocks)
            self.flushcounter =0 

        return data
    def getBlockTime(self, blockNumberOrHash):
        return self.getBlockInfo(blockNumberOrHash)['time']


    def getTransaction(self, txhash):
        return requests.get("https://etherchain.org/api/tx/%s" % txhash).json()['data'][0]

    def getAllTransactions(self, address):
        """ Returns an iterator of all transactions to/from the specified address
            Internally, this shelves transactions to disk, and only queries for new 
            transactions
        """
        # Load cached data
        cachedTransactions = loadjson(".%s-transactions.json" % address) or {'byhash':{}}

        tx_byhash = cachedTransactions['byhash']

        stats = {"added" : 0}
        
        def insert(tx):
            if not tx_byhash.has_key(tx['hash']):
                tx_byhash[tx['hash']] = tx
                stats['added'] = stats['added']+1
                return True
            return False

        #Fetch new data
        abort = self.offline
        while not abort:
            offset = len(tx_byhash)

            url = "https://etherchain.org/api/account/%s/tx_asc/%d" % (address, offset)
            log(url)
            resp = requests.get(url)
            if resp.status_code == 200 :
                jsondata = resp.json()['data']
                for tx in jsondata:
                    if not insert(tx): 
                        log("Error, we got a tx we already have. Probably missing earlier transactions for %s" % address)
                        abort = True

                if len(jsondata) < 50:
                    abort = True

            else:
                raise Exception("Failed to get %s history" % instr)


        #Save cache
        if stats['added'] > 0:
            savejson(".%s-transactions.json" % address, cachedTransactions)
            print("Added %d transactions for %s" % (stats['added'], address))

        # Return txs starting at lowest nonce
        for h,tx in tx_byhash.items():
            yield tx


    def outgoingTransactions(self, address):
        for tx in self.getAllTransactions(address):
            if tx['sender'].lower() == address.lower():
                yield tx

    def contractCreateTransactions(self, address):
        for tx in self.outgoingTransactions(address):
            if tx['newContract'] != 0:
                yield tx

    def contractCreationTransaction(self, address):
        for tx in self.incomingTransactions(address):
            if tx['newContract'] != 0:
                yield tx
        return


    def incomingTransactions(self, address):
        for tx in self.getAllTransactions(address):
            if tx['recipient'].lower() == address.lower():
                yield tx

    def sendersTo(self, address):
        address = address.lower()
        allTxs = []
        totalCost =0
        senders = set()
        
        log("Loading senders to %s" % address)
        
        for tx in self.incomingTransactions(address):
            gasUsed = float(tx['gasUsed'])
            price = float(tx['price'])
            cost = (gasUsed * price)
            senders.add(tx['sender'])
            allTxs.append(tx['time'])
            #print(tx)
            totalCost = totalCost + cost

        allTxs.sort()
        return (senders, totalCost, allTxs)

    def getAccount(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]


    def getBalance(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]['balance']

    def getCode(self, address):
        return requests.get("https://etherchain.org/api/account/%s" % address).json()['data'][0]['code']


    def getBalances(self,addresses):
        return [(address,self.getBalance(address)) for address in addresses]


    def findNewContracts(self, address):
        """ Finds all contracts created by a given address
        Returns all previously unseen contract"""

        foundContracts = {}

        # Find them all
        for tx in self.contractCreateTransactions(address):
            newC = tx['recipient'].lower()
            foundContracts[newC] = tx

        #Check which we already know about
        knownContracts = loadjson(".%s-contracts.json" % address) or {}

        diff = []
        for k,v in foundContracts.iteritems():
            if not k in knownContracts.keys():
                diff.append(v)
                knownContracts[k] = v
        # Save
        if len(diff) > 0:
            savejson(".%s-contracts.json" % address, knownContracts)
        return diff

    def getAllContracts(self, address):
        """ Finds all contracts created by a given address"""
        self.findNewContracts(address)
        knownContracts = loadjson(".%s-contracts.json" % address) or {}
        return knownContracts.values()

def convertDataformat():
    import glob
    files = glob.glob('./datastore/.*-transactions.json')
    for f in files:

        tx_byhash = {}
        data = {}
        with open(f, "r") as fil:
            print("opening %s" % f)
            data = json.load(fil)
            del data['bynonce']

            print("newname %s" % f[:-2])
            with open(f[:-2], "w+") as fil2:
                fil2.write(json.dumps(data))    
                print("Converted %s into" % f)


if __name__ == '__main__':
    api = EtherChainAPI(offline=True)
    addresses = [
        "0x4CE312538AA0B69740CBABFBFD8A2A8E628F660D",
        "0x89AD4426E629368ECB9D63AB01E5CA538FBDC1A4",
        "0xD38AF0F92DDE2BC5C6C94C6083A9167507AEC37B",
        "0x679D434B06DEE1686EB044CC721D41E20E298ABC",
        "0xACE25FF1EECA76317D3BAF12D426624B5298C4E5",
        "0xFBD5DF4FF4790F881B3AD7F64EDBA082D75A449B",
        "0x629FB9AA6DAEF7E0CAF641A6A9E9DF796ED83CE7",
        "0x78CC9E707D760B6693BB114A2259D435FE19B937",
        "0xBE90F452775A16749C225542501A67065DCB6DB7",
        "0x96AB58C915EE9264C4DA5D2F0C92972BB5E1A23A",
        "0xC1371FB167DCA98266CC357952F0F9AD2FF72303",
        "0xDC0426D50398FD4847AE886DEF8DB0C7F32FC165",
        "0xEE92E5C794C08581AA92B4A7E78DFF62D343AFB7",
        "0xC72C3EBD888AC1970A8712FEF74A1F9B9BEECAD3",
        "0x13BC06227D1BCFF708065491B8E0D7794E0E7DE5",
        "0xD90B72526E124075805BBB472B70D96DA5E4D747",
        "0xA9AC072B051C00FA940164949CF6106076D26758",
        "0xFBEAAFD60C6102583AF45FBAE9E5C423EFA661AB",
        "0x296516205B5FCDEAB789D90F307FFAD120F2D457",
        "0x04E11D27DE725F7E9601167B5E3696DA9CE40D7A",
        "0xEDA6F8F6D6B2E7DAF7A11F62E51A72449BD2DAF1",
        "0xFABCDAEEDC07D8013F006E6280E72D1F51DCDD26",
        "0x1DBC58DB158A3A027DF480FAFFDC65A6BFEDBBEC",
        "0x3F456E749863E7BF1A00E11A7DE3F6B47CE99932",
        "0xAD523418157DE7BB715AC689EF099DFCED7AB1E6",
        "0x43EBDEAFE1F5F30ED91F26DFC88AF7ACC113F012",
        "0x7E022766CAA162007AEA9FC3B429E3D9E49314B4",
        "0x888BEE4C8478E74BF6E066E73BA14179AC741427",
        "0x9BF986BF345894F30FF0D22B11BC28BB1FE098C1",
        "0x123BC327B0A97CFC77074100933AAD0EC642BEB4",
        "0xBD674FC9B32EB1099B1AFFCCFC624CB8AFCF1C02",
        "0x389F0C87F72D7EED2EDCF8893CD0ABD3B669F8DD",
        "0x8BA43F7E6CC99F15C51B724D774A4E908768CAEF",
        "0x9B9B19947ABDD56B902672C50121D793D9FCEEA9",
        "0x96CE5896B217A5D43EFE133DE63B03B105B66EF6",
        "0x5C0EB5D9AB93E3A8978E19308E52C140887B7B18",
        "0x1B4F6B2A9BDAB71BFDF24AA87272841BDE969EE0",
        "0xE6A2B33E1F00D73609C3E998F5983B558E76541F",
        "0xD5F8364F460CD1E7143B06E02F23512244B135B7",
        "0xD2FCD0803D95BD5974109A9B6A37028CBF180B6E",
        "0x3E3BBDA21848FA0E6778E36B2FBF1533B80502F8",
        "0xAF8FC22C1C1DC40E35DBF8B9A320A40BF53AB0AF",
        "0x6F7C51628C3690D59BC2E179C3137735CADAB198",
        "0x47F0D4362A266FCF985B8EA0E282C754FFC0D7BF",
        "0xAD45B966235CEDE0A2684E93C05201B383D76484",
        "0xFA4ABFD676CAEBE39F1FB8804F33BF2BB405069B",
        "0xC18564061499477DF278327ED1C7D31A46CE7519",
        "0x4CA8641E969D6892767640B9AC4BEADCA2736F80",
        "0xDE07B141354CB7DC5CE3A0B65557484C34D72018",
        "0x41A7FB9C3FB74001B43816A8D70107AE2844A09F",
        "0xAC0FA2DE9320E0A850BA888FA05CD86367F63B93",
        "0xF163279ADF52338218067B59900E752F08617C40",
        "0xF9697F38B6A7C311D8A358A4DF493123BABBD584",
        "0x647EC6495F4D958B80A8C7584910B586543FBDAC",
        "0x3317203629861DA4F62A04EA70221BDCDF7074CD",
        "0x45C2A5216E5B4F132096F64B50AC05F201925E61",
        "0xD1C8B08B0E13504976ECFDCC407661556BDE6EC6",
        "0xF4E06D554038FEDB3A6C6E04278E5129C4E5959B",
        "0x85068541D456D2AF6683474CB7323BEEF24C4AAC",
        "0x81C2680B6BE2988875B120630FAC20C398E1D9DE",
        "0x40C680B29B369AF25E247276538241098B5B1F30",
        "0x7B9FD32A0A809DEE2D8A819D40002FE33AEDA21E",
        "0xEF279FB1B4E402320E70967A4F93FD81C9F69133",
        "0x9F90E33211226686CE5D0E8065EC046637EEC92E",
        "0x69B636398CE39425FCC43FC10CD0CC4B4E06323E",
        "0xAB97422E6352B453EEE862626451F8138339943E",
        "0x51161DAE22A7012751FF4A4D38EF4B6455A3FDD3",
        "0x31EE3CE13A0F1F9231E2D213864B336FD406BD20",
        "0x3FD26BCEF008744941D9EA6D11B233138813695A",
        "0x63BF6FBD344045F3E1B18BF676D824B8D52218C2",
        "0xC66313B9EF38CAFE541FA7EC3D4D700A1C8C5CFE",
        "0x47A37C10A74ECDFEF7F359FBA5991D9EF279A15B",
        "0x044D77FC514C7F566051CAFB248AC3F8DC8B36FE",
        "0x0428CEA98D32C6620F4C84206B84B895B20095F5",
        "0x4BAB60362FDC1C064D69628391F87495ECF9CA73",
        "0x731AEED483E75D644A975FD3257FC07C7118CC88",
        "0x32FE59A975A091540BFBF327F0EDF1CED997627B",
        "0xED0C2024896A2564AE69AA3E9F107E4E8BE2944A",
        "0xF604F282A9BF0772A294BE1A481FF2C0E437245D",
        "0xF70CF9BE2CCF10B39B93C95FDC16F4B9972F1B64",
        "0x1A9559716CAFDED0B9573768EA52EE29E922B687",
        "0x526634CDE83E541BA851A402E5C85BD0838505EB",
        "0x15B593E70E0172A3FAA046EEC8AEC3E629610B1C",
        "0x3D408586C7B4DD5D79459D857FF5995C2515FB4D",
        "0xF99B0919121A7B8EC0716996030BFE3E0B805E2D",
        "0xF440008157CA3744F4E65E42FA31151617E7E02E",
        "0x07F3738BC35A76E3EAFAF2A261E2DB81263481FD",
        "0xCD2895627A599B27B50DFE6775CB25678861FA4D",
        "0x6203146B89AF87443C864B39FC679B4EA13DBBCA",
        "0x02EC139ED20216BAC58E1EFA8189839522564FED",
        "0xF10BAA92C88B2F03181CFF070B95E62C8AB52DCB",
        "0x86D79BA60E0DF4AB15AADA5615B6764F231A68D1",
        "0x532F2F3FDED63798246F6C512E18A5E33468B2CF",
        "0x4B2CD9BAA98E977304B1BB96640C257AA38A9AF1",
        "0x150295D2D7717CD6328214309BCB09474080273F",
        "0x61EFBA685735F700D077CE1A82DDA58758549AD7",
        "0x750E9763D585FD5278C4A2F17653E324C3719522",
        "0x25F9F251AF7A1EB271925F4318F418830DD6BE5E",
        "0xBFC526D0197ABC3BE3BC719367EC2333BC235D22",
        "0xB171781675D320498B1CDDC0FB938B5FB8CFD62B",
    ]
    addresses = [

        "0xDB612C93DB5B7EB723EFE7E1C36F6218A9FAB0F4",
        "0xC44B69462FF01F58A213B2B869E6E4986B16EEBE",
        "0xDEA73406763D54DD3CBBBF085F01E982857CBE12",
        "0xF488A5AB7C585AD5F2E0B01F6E795FF6C6BB2389",
        "0x0B888E3C8054A4F27AE1487B7A860CEA2B028C34",
        "0xE5DF0B99F54617D418EFF951B95297D68525F3B2",
        "0x3CE7B807EF48633F237AE299B0A5254069E48FC9",
        "0x01034E0934FB0B6BE1983A99853D99E48504BE0D",
        "0x777E8856746CCFCCB41A765F7F3352552299CF98",
        "0x9823F095D46813758E03EB92A730930AEDEB5FF2",
        "0x6FC89B75946D19A64FDD38CDC44506F6A2452E47",
        "0x483DC11A58D20DD8124FE9433306C1B1EDA1C611",
        "0x4E6F639DCA3E8C4605E133DFFD411CDEE0954F2A",
        "0xDA9B76A445CE0FBCF0D140A18A7F03E34DDCB919",
        "0x89E3A5877C20319A61F1B9ED82A99F4582E56BD8",
        "0x8B0C49FC86BC30C8EC3812F572B15CE324F32C64",
        "0xD18C87B2437D072987CEF0196B39BB2F5199A3E7",
        "0x212217E54D586BA0F3861BDF32EEFC82B70A5579",
        "0xF328D83FE2088FD28BF61ADACC64E674DB137FC3",
        "0x77FFFFF98FD8DE50D3FE717291F05E82B5C00746",
        "0x17E212028A4EBE580269A5A8E8A1B3EC08BB0335",

    ]
    for address in addresses:
        tx= api.contractCreationTransaction(address).next()
        t = tx['time']
        b = tx['block_id']
        print("%d : %s created at %s" % (b,address, t))
    #convertDataformat()