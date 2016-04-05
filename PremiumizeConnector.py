import time
import requests

class PremiumizeConnector:
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.headers = {'cookie': 'login={0}:{1}'.format(self.user, self.passwd)}


    def getList(self):
        url = r'https://www.premiumize.me/api/transfer/list'
        request = requests.post(url,
                                headers=self.headers)
        request_json = request.json()
        if request_json['status'] == 'error':
            print "getList:", request_json
            raise ValueError(['message'])
        return request_json['transfers']

    def updateWatchlist(self, list):
        hashes = [t['hash'] for t in list]
        newList = self.getList()
        list[:] = [t for t in newList if t['hash'] in hashes]

    def getContents(self, hash):
        url = r'https://www.premiumize.me/api/torrent/browse'
        params = {'hash': hash}
        request = requests.post(url,
                                headers=self.headers,
                                params = params)

        request_json = request.json()
        if request_json['status'] == 'error':
            print "getContents:", request_json
            raise ValueError(['message'])
        return request_json['content']

    def getBiggestFileDownload(self, hash):
        contents = self.getContents(hash)
        biggest, biggestsize = self.__getBiggestHelper(contents, -1)
        return biggest

    def __getBiggestHelper(self, obj, biggestSize):
        biggest = None
        for entry in obj.keys():
            if obj[entry]['type'] == 'dir':
                biggest, biggestSize = self.getBiggestHelper(obj[entry]['children'], biggestSize)
            else:
                assert obj[entry]['type'] == 'file', 'unknown entry type'
                size = obj[entry]['size']
                if size > biggestSize:
                    biggest = obj[entry]['url']
                    biggestSize = size
        return biggest, biggestSize

    def addTorrent(self, file):
        currentTransfers = self.getList()

        url = r'https://www.premiumize.me/api/transfer/create?type=torrent'
        with open(file, 'rb') as torrent:
            payload = {'src': torrent}
            request = requests.post(url,
                                headers=self.headers,
                                files=payload)
            request_json = request.json()

        if request_json['status'] == 'error':
            print "addTorrent:", request_json
            return None

        time.sleep(0.1)
        newList = self.getList()
        myTorrent = [x for x in newList if x not in currentTransfers]
        assert len(myTorrent) == 1, 'Cannot determine added torrent'
        myTorrent = myTorrent[0]

        return myTorrent