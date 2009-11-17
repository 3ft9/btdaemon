#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Modified from btlaunchmany.py which was written by John Hoffman
# Modified by Stuart Dallas
# HTTPd based on code from http://cvs.sourceforge.net/viewcvs.py/linkchecker/linkchecker/linkcheck/ftests/httptest.py?rev=1.6&view=auto

import sys
import os
import SimpleHTTPServer
import BaseHTTPServer
import httplib
import urllib
import time
import shutil
from datetime import datetime

from BitTorrent.daemoncore import Daemon
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent import configfile
from BitTorrent import version
from BitTorrent import BTFailure

from cherrytemplate import renderTemplate
from cherrypy import cpg
from cherrypy.lib import httptools

version = "BTDaemon/1.0"
files = []
messages = ['']
stopflag = False
scanflag = False
restartflag = True
defaulttitle = 'BTDaemon'

def fmttime(n):
    if n <= 0:
        return None
    n = int(n)
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    if h > 1000000:
        return 'connecting to peers'
    return 'ETA in %d:%02d:%02d' % (h, m, s)

def fmtsize(n):
    n = float(n)
    unit = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    i = 0
    while n > 999:
        i += 1
        n /= 1024

    if i > 0:
        size = '%.1f' % n + '%s' % unit[i]
    else:
        size = '%.0f' % n + '%s' % unit[i]
    return size

class Page:
    headertxt = ''
    footertxt = ''

    def header(self):
        if len(self.headertxt) == 0:
            f = open(os.path.join(config['template_dir'], 'header.html'), 'r')
            self.headertxt = f.read()
            f.close()
        return self.headertxt

    def footer(self):
        if len(self.footertxt) == 0:
            f = open(os.path.join(config['template_dir'], 'footer.html'), 'r')
            self.footertxt = f.read()
            f.close()
        return self.footertxt
    
    def Get(self, body, pagetitle = None):
        title = defaulttitle
        loggedin = cpg.request.sessionMap.has_key('authenticated')
        if pagetitle:
            title = title + ' :: ' + pagetitle
        return renderTemplate(template = self.header() + body + self.footer())
        
    def GetTemplate(self, filename):
        f = open(os.path.join(config['template_dir'], filename), 'r')
        retval = f.read()
        f.close()
        return retval

p = Page()

def passwordProtected(fn):
    def _wrapper(*args, **kwargs):
        global config
        if config['http_password'] == '':
            cpg.request.sessionMap['authenticated'] = 1
        if cpg.request.sessionMap.has_key('authenticated'):
            return fn(*args, **kwargs)
        else:
            reason = ''
            submiturl = cpg.request.browserUrl
            try:
                pwd = kwargs['pwd']
            except KeyError:
                return p.Get(renderTemplate(p.GetTemplate('login.html')), 'Authenticate')

            if pwd != config['http_password']:
                reason = 'Incorrect password'
                return p.Get(renderTemplate(p.GetTemplate('login.html')), 'Authenticate')
            cpg.request.sessionMap['authenticated'] = 1

            return fn(*args, **kwargs)
    return _wrapper

class op:
    @cpg.expose
    @passwordProtected
    def login(self, *args, **kwargs):
        return httptools.redirect("/")

    @cpg.expose
    def logout(self, *args, **kwargs):
        del cpg.request.sessionMap['authenticated']
        return httptools.redirect("/")

    @cpg.expose
    @passwordProtected
    def stop(self, *args, **kwargs):
        global scanflag
        f = kwargs['f']
        os.remove(os.path.join(config['torrent_dir'], urllib.unquote_plus(f)))
        scanflag = True
        time.sleep(2)
        return httptools.redirect("/")

    @cpg.expose
    @passwordProtected
    def pause(self, *args, **kwargs):
        global scanflag
        f = kwargs['f']
        os.rename(os.path.join(config['torrent_dir'], urllib.unquote_plus(f)), os.path.join(config['paused_torrent_dir'], urllib.unquote_plus(f)))
        scanflag = True
        time.sleep(2)
        return httptools.redirect("/")

    @cpg.expose
    @passwordProtected
    def resume(self, *args, **kwargs):
        global scanflag
        f = kwargs['f']
        os.rename(os.path.join(config['paused_torrent_dir'], urllib.unquote_plus(f)), os.path.join(config['torrent_dir'], urllib.unquote_plus(f)))
        scanflag = True
        time.sleep(2)
        return httptools.redirect("/")

    @cpg.expose
    @passwordProtected
    def shutdown(self, *args, **kwargs):
        global stopflag, restartflag
        restartflag = False
        stopflag = True
        return p.Get(p.GetTemplate('shutdown.html'), 'Shutdown')
    
    @cpg.expose
    @passwordProtected
    def addhttp(self, *args, **kwargs):
        global scanflag
        filename = kwargs['url'].split('/')[-1]
        inf = urllib.urlopen(kwargs['url'])
        outf = open(os.path.join(config['torrent_dir'], urllib.unquote_plus(filename)), 'wb')
        outf.write(inf.read())
        outf.close()
        inf.close()
        scanflag = True
        time.sleep(2)
        return httptools.redirect("/")

    @cpg.expose
    @passwordProtected
    def addfile(self, *args, **kwargs):
        global scanflag
        outf = open(os.path.join(config['torrent_dir'], urllib.unquote_plus(cpg.request.filenameMap['thefile'])), 'wb')
        outf.write(kwargs['thefile'])
        outf.close()
        scanflag = True
        time.sleep(2)
        return httptools.redirect("/")

class RootHandler:
    @cpg.expose
    def index(self):
        basedirlen = len(config['torrent_dir'])
        dottorrentlen = len('.torrent')
        tpl = p.GetTemplate('torrentrow.html')
        totalupamt = 0
        totaluprate = 0
        totaldnamt = 0
        totaldnrate = 0
        rows = ''
        for (name, status, progress, peers, seeds, seedsmsg, dist, uprate, dnrate, upamt, dnamt, size, t, msg, path) in files:
            t = fmttime(t)
            if t:
                status = t

            progress = float(progress.replace('%', ''))
            # derive downloaded figure from percentage done so it's overall rather than just this session
            dnamt = (size / 100) * progress
            totalupamt += upamt
            totaluprate += uprate
            totaldnamt += dnamt
            totaldnrate += dnrate

            rows += renderTemplate(tpl)
        
        paused_tpl = p.GetTemplate('pausedrow.html')
        paused = ''
        try:
            dir_contents = os.listdir(config['paused_torrent_dir'])
            for f in dir_contents:
                if f.endswith('.torrent'):
                    paused += renderTemplate(paused_tpl)
        except (IOError, OSError), e:
            pass

        return p.Get(renderTemplate(p.GetTemplate('index.html')), 'Status')
        
class DaemonData:
    def __init__(self):
        self.counter = 0

    def display(self, data):
        global files, stopflag, scanflag
        files = data
        if stopflag:
            return 1
        elif scanflag:
            scanflag = False
            return 2
        return 0

    def message(self, s):
        global messages
        messages.append([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s.replace(config['torrent_dir'], '').replace('.torrent', '').replace("\n", '<br />')])

    def exception(self, s):
        self.message('EXCEPTION: '+s)


if __name__ == '__main__':
    uiname = 'btdaemon'
    defaults = get_defaults(uiname)
    try:
        if len(sys.argv) < 2:
            printHelp(uiname, defaults)
            sys.exit(1)
        config, args = configfile.parse_configuration_and_args(defaults,
                                      uiname, sys.argv[1:], 0, 1)
        if args:
            config['torrent_dir'] = args[0]
        if not os.path.isdir(config['torrent_dir']):
            raise BTFailure("Warning: "+args[0]+" is not a directory")
    except BTFailure, e:
        print 'error: ' + str(e) + '\nrun with no args for parameter explanations'
        sys.exit(1)

    # Start the HTTP server
    cpg.root = RootHandler()
    cpg.root.op = op()
    try:
        import threading
    except ImportError:
        self.fail("HTTP server requires threading support")
    t = threading.Thread(None, cpg.server.start, None, ('cherrypy.conf', None, {'logToScreen': 0, 'socketPort': config['http_listen_port'], 'staticContent': (('images', 'images'))}))
    t.start()
    time.sleep(3)

    # Start the BT process
    Daemon(config, DaemonData(), 'btdaemon')

    # Kill the HTTP server
    time.sleep(3)
    cpg.server.stop()