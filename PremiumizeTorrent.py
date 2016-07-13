import os, sys, time, shutil, atexit
from os.path import split, join, expanduser
import urllib
import requests
import shelve
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from clint.textui import progress

from PremiumizeConnector import PremiumizeConnector
from PremiumizeTorrentConfig import config

global obs
global watchlist

class TorrentAdder(FileSystemEventHandler):
    def __init__(self, prem, config, torrentList):
        self.prem = prem
        self.config = config
        self.torrentList = torrentList

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.torrent'):
            file = event.src_path
            torrent = split(event.src_path)[1]
            print "Found torrent: ", torrent
            newTorrent = prem.addTorrent(file)
            shutil.move(file, join(config['done_dir'], torrent))
            if newTorrent:
                print "Added torrent: ", torrent
                self.torrentList['list'].append(newTorrent)

def cleanup():
    if watchlist:
        watchlist.close()
    if obs:
        obs.stop()
        obs.join()

if __name__ == '__main__':
    atexit.register(cleanup)

    #ensure dirs are there
    for path in ['watch_dir', 'done_dir', 'output_dir']:
        if not os.path.isdir(config[path]):
            os.makedirs(config[path])

    global obs
    global watchlist

    watchlist = shelve.open(join(expanduser('~'), 'PremiumizeTorrentWatchlist.db'), writeback=True)
    if 'list' not in watchlist:
        watchlist['list'] = []
    if len(watchlist['list']) == 0:
        print "Nothing to resume"
    else:
        print "Resuming previous waitlist: ", watchlist['list']

    prem = PremiumizeConnector(config['prem_id'], config['prem_pass'])
    adder = TorrentAdder(prem, config, watchlist)
    obs = Observer()
    obs.schedule(adder, config['watch_dir'])
    obs.start()

    while True:
        finished = prem.getFinished(watchlist['list'])
        for torrent in finished:
            url = prem.getBiggestFileDownload(torrent['hash'])
            if not url:
                print "ERROR getting download URL for", torrent['name']
                continue
            filename = urllib.unquote_plus(url.split('/')[-1])
            outpathTmp = join(config['done_dir'], filename)
            outpath = join(config['output_dir'], filename)
            print "Torrent ready:", url
            print "Saving as", filename
            r = requests.get(url, stream=True, verify=False)
            chunksize = 1*1024*1024
            with open(outpathTmp, "wb") as f:
                total_length = int(r.headers.get('content-length'))
                for chunk in progress.bar(r.iter_content(chunk_size=chunksize), expected_size=(total_length / chunksize) + 1):
                    if chunk:
                        f.write(chunk)
            shutil.move(outpathTmp, outpath)
            watchlist['list'].remove(torrent['id'])
        try:
            time.sleep(config['sleeptime'])
        except KeyboardInterrupt:
            obs.stop()
            sys.exit(0)
    print 'end'
