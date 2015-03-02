#!/usr/bin/python

# usage: ethertex.py basename pad_url

import urllib, urllib2
import sys, getopt
import re
import os
import cPickle as pickle
import threading
from collections import deque
import cookielib
import traceback

basename = sys.argv[1]
cachefile = "../" + basename + ".cache"

cj = cookielib.LWPCookieJar()
urllib2.install_opener(urllib2.build_opener(
        urllib2.HTTPSHandler(debuglevel=0),
        urllib2.HTTPCookieProcessor(cj)
        ))

class VerError(Exception):
    pass
class AuthError(Exception):
    pass
class FetchError(Exception):
    pass
class SyntaxError(Exception):
    pass

def _u(text):
    return text.replace("<", "%3C").replace(">", "%3E")
def _h(text):
    return text.replace("<", "&lt;").replace(">", "&gt;")

def writeFile(name, data):
    if not re.match("^[a-zA-Z0-9\._\-]+$", name):
      raise NameError("Illegal characters in filename &ldquo;<tt>%s</tt>&rdquo;" % (_h(name)))
    name = name.strip()
    f = open(name, 'w')
    f.write(data)
    f.close()

def fetchPadURL(url):
    req = urllib2.Request(url=padURLToTextURL(url))
    res = urllib2.urlopen(req)
    if "/account/" in res.geturl():
        raise AuthError(url)
    else:
        data = res.read()
    return data

def padURLToTextURL(url):
    (base,pad) = re.findall("^(.*/)([^/]*)$", url)[0]
    pad = pad.replace(".", "-")
    return base + "ep/pad/export/" + pad + "/latest?format=txt"

def fetchPadText(url):
    try:
        data = fetchPadURL(url)
    except urllib2.HTTPError as e:
        print "<div class=exception><h3>HTTP Error %d</h3>" % (e.code),
        print "Could not retrieve <a href='%s'>%s</a></div>" % (_u(url),_h(url)),
        print "</div>",
        raise FetchError(url)
    return data

class CachingImporter(object):
    def __init__(self, filename):
        try:
            self.cache = pickle.load(open(filename, 'r'))
        except Exception:
            self.cache = {}

    def import_file(self, name, url, once):
        cache = self.cache
        req = urllib2.Request(url)
        if os.path.exists(name) and name in cache and once:
            print "Using cached <tt>%s</tt> from <a href='%s'>%s</a> (check skipped by <tt>-once</tt>)" \
                % (_h(name),_u(url),_h(url))
            return
        if os.path.exists(name) and name in cache:
            req.add_header("If-None-Match", cache[name])
        try:
            res = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            if e.code == 304:
                print "Using cached <tt>%s</tt> from <a href='%s'>%s</a>" % (_h(name),_u(url),_h(url))
            else:
                print "<div class=exception><h3>HTTP Error %d</h3>" % (e.code),
                print "Could not retrieve <a href='%s'>%s</a></div>" % (_u(url),_h(url)),
                print "</div>",
            return
        cache[name] = res.info().getheader("ETag")
        writeFile(name, res.read())
        print "Fetched <tt>%s</tt> from <a href='%s'>%s</a>" % (_h(name),_u(url),_h(url))

    def close(self):
        f = open(cachefile, "w")
        pickle.dump(self.cache, f)
        f.close()

def isPadUrl(url):
    if re.match("^https://[a-zA-Z0-9\-]+\.pad2\.jhalderm\.com/[a-zA-Z0-9\._\-]+$", url):
        return True
    return False

def urlBaseName(url):
    m = re.match("^https?://[^?]+/([^?#]+)", url)    
    if not m:
        raise NameError("Couldn't determine a filename for <a href='%s'>%s</a>" % (_u(url),_h(url)))
    return os.path.basename(m.group(1))

class Processor(object):
    def __init__(self):
        self.pads = {}
        self.files = {}
        self.imports = []

    def namePad(self,name,url):
        if name not in self.files:
            name = os.path.basename(name.strip())
            writeFile(name,self.pads[url])
            self.files[name] = url
            print "Fetched <tt>%s</tt> from <a href='%s'>%s</a>" % (_h(name),_u(url),_h(url))

    def process(self,queue):
        threads = []
        importer = CachingImporter(cachefile)
        while queue:
            (dataName,dataUrl) = queue.popleft()
            if not isPadUrl(dataUrl):
                raise Exception("<b>Internal Error:</b> Not a pad url (%s)" % (_h(dataUrl)))
            if dataUrl in self.pads:
                self.namePad(dataName,dataUrl)
                continue
            self.pads[dataUrl] = data = fetchPadText(dataUrl)
            self.namePad(dataName,dataUrl)

            m = re.search("%ethertex-(filename|import|link):", data)
            if m:
                raise VerError("<a href='%s'>%s</a> contains &ldquo;<tt>%s</tt>&rdquo;" \
                                   % (_h(dataUrl),_u(dataUrl),_h(m.group(0))))
            r = re.compile("%ethertex(-[a-z]+)?\:(.*)$$", re.MULTILINE)
            for m in r.findall(data):
                flag,v = m
                v = v.strip()
                name = url = None
                m = re.match("^([a-zA-Z0-9\-_.]+) *= *(https?://.+)$",v)
                if m:
                    url = m.group(2)
                    name = os.path.basename(m.group(1))
                elif re.match("^https?://.+$",v):
                    url = v
                    name = urlBaseName(url)
                else:
                    raise SyntaxError(("Couldn't parse &ldquo;<tt>ethertex%s: %s</tt>&rdquo; " + 
                                          "in <a href='%s'>%s</a>") \
                                          % (_h(flag), _h(v),_u(dataUrl),_h(dataUrl)))
                if not name or not url:
                    raise SyntaxError(("Couldn't parse a name and url from " + 
                                      " &ldquo;<tt>ethertex%s: %s</tt>&rdquo; in <a href='%s'>%s</a>") \
                                          % (_h(flag), _h(v),_u(dataUrl),_h(dataUrl)))
                if flag not in ['', '-once']:
                    raise SyntaxError(("I don't understand &ldquo;<tt>ethertex%s:</tt>&rdquo; " + 
                                      "in <a href='%s'>%s</a>") \
                                          % (_h(flag), _u(dataUrl),_h(dataUrl)))
                if isPadUrl(url):
                    if  "." not in name:
                        name = name + ".tex"
                    if name not in self.files:
                        queue.append((name,url))
                else: # non-pad url
                    if name not in self.files:
                        if url not in self.imports:
                            self.imports.append(url)
                            t = threading.Thread(target=importer.import_file,
                                                 args=(name, url, (flag=='-once')))
                            threads.append(t)
                            t.start()
        for t in threads:
            t.join()
            importer.close()

def main():
    print "<style>body { font-family: helvetica,arial; font-size: 9pt; line-height:12pt; }</style>",
    print "<style>div { display: table; margin: 6px 0; }</style>",
    print "<style>.exception { padding:6px 12px; background-color: #ffcccc; border: 3px solid red; }</style>",
    print "<style>h2 { margin:0 0 6px 0; padding: 0; font-size: 125%; }</style>",
    print "<style>h3 { margin:0 0 6px 0; padding: 0; font-size: 120%; }</style>",

    try:
        # This sets urllib to use the client's session cookie, which is
        # passed in to the script from the EtherPad plugin:
        cookie_path = "." + ".".join(sys.argv[4].split(".")[2:])
        cj.set_cookie(cookielib.Cookie(version=0, name='ES', value=sys.argv[5], port=None, port_specified=False, domain=cookie_path, domain_specified=True, domain_initial_dot=True, path='/', path_specified=True, secure=True, expires=None, discard=True, comment=None, comment_url=None, rest={}, rfc2109=False))
        Processor().process(deque([(sys.argv[3],sys.argv[2])]))
    except NameError as err:
        print "<div class=exception><h3>Name error</h3>",
        print err,
        print "</div>",
        sys.exit(1)
    except SyntaxError as err:
        print "<div class=exception><h3>Syntax error</h3>",
        print err,
        print "</div>",
        sys.exit(1)
    except VerError as err:
        print "<div class=exception><h3>Wrong EtherTeX version</h3>",
        print err, "<br>"
        print "This is deprecated EtherTeX 1 syntax.  I don't understand it, and it never really made much sense anyway.<br>Switch to the <b><a href='https://wiki.pad.jhalderm.com/ethertex'>EtherTeX 2 syntax</a></b> or change your build URL to <b>/build1/</b>."
        print "</div>",
        sys.exit(1)
    except AuthError as url:
        print "<div class=exception><h3>Pad authorization failed</h3>",
        print "Couldn't retrieve <a href='%s'>%s</a>" % (_u(str(url)),_h(str(url)))
        print "Are you sure you have permission to access that?</div>",
        sys.exit(1)
    except FetchError as e:
        sys.exit(1)
    except:
        print "<div class=exception><h3>EtherTeX internal error:</h3>",
        traceback.print_exc(file=sys.stdout)
        print "</div>",
        sys.exit(1)

if __name__ == "__main__":
    main()

