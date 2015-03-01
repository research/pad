/**
 * Copyright 2015 J. Alex Halderman <jhalderm@eecs.umich.edu>
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS-IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import("faststatic");
import("dispatch.{Dispatcher,PrefixMatcher,forward}");

import("fastJSON");
import("etherpad.utils.*");
import("etherpad.pad.padutils");
import("etherpad.collab.server_utils");
import("etherpad.globals.*");
import("etherpad.log");
import("etherpad.pad.padusers");
import("etherpad.pro.pro_utils");
import("etherpad.pro.pro_padmeta");
import("etherpad.helpers");
import("etherpad.pro.pro_accounts.getSessionProAccount");
import("sqlbase.sqlbase");
import("sqlbase.sqlcommon");
import("sqlbase.sqlobj");
import("etherpad.sessions");

jimport("java.io.File",
    "java.io.InputStreamReader",
    "java.io.DataInputStream",
    "java.io.FileInputStream",
    "java.io.BufferedInputStream",
    "java.io.OutputStreamWriter",
    "java.io.DataOutputStream",
    "java.io.FileOutputStream",
    "java.io.BufferedReader",
    "java.io.BufferedOutputStream",
    "java.lang.Integer",
    "java.lang.Byte",
    "java.lang.Runtime");

function _checkIfDeleted(pad) {
    // TODO: move to access control check on access?
    if (pro_utils.isProDomainRequest()) {
        pro_padmeta.accessProPad(pad.getId(), function(propad) {
            if (propad.exists() && propad.isDeleted()) {
                renderNoticeString("This pad has been deleted.");
                response.stop();
            }
        });
    }
}

function _sanitizeFilename(dirty)
{
    // Defensively written and paranoid.  Data from the input string
    // is never directly copied to the output string.  Each character
    // is tested for membership in a whitelist; if there's a purposed
    // match, that element of the whitelist is appended to the output.
    // If the final output is empty or does not match the input, the
    // function throws an exception.

    var safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-";

    var oked = [];
    for (var c in dirty.split("")) {
        var n = safe.indexOf(dirty[c]);
        if (0 < n) {
            oked.push(safe[n]);
        }
    }

    var clean = oked.join("");
    if ((0 < clean.length) && (dirty == clean)) {
        return "" + clean;
    }
    throw new Error();
}

function _getBuildName(subdomain, padid)
{
    return _sanitizeFilename(subdomain) + "-" 
        + _sanitizeFilename(padid);
}

function _getBuildPath(subdomain, padid)
{
    //var baseDir = "/var/ethertex/data"; // config
	var baseDir = appjet.config['ethertexBaseDir'];
	if (!baseDir) {
        throw new Error();
	}

    return baseDir + "/" 
        + _getBuildName(subdomain, padid) + "/";
}

function _getPadURL(subdomain, padid)
{
    //var baseURL = "pad.jhalderm.com"; // config
	var baseURL = appjet.config['ethertexBaseURL'];
	if (!baseURL) {
        throw new Error();
	}

    return "https://" + _sanitizeFilename(subdomain) + "."
        + baseURL + "/"
        + _sanitizeFilename(padid);
}

function _getFilename(subdomain, padid, ext)
{
    var path = _getBuildPath(subdomain, padid);
    var base = _sanitizeFilename(padid);
    return path + "/" + base + "." + ext;
}

function _fileExists(filename)
{
    var file = new Packages.java.io.File(filename);
    return file.isFile();
}

function _prepareBuild(subdomain, padid)
{
    var path = new Packages.java.io.File
    (_getBuildPath(subdomain, padid));
    if (!path.isDirectory()) {
    path.mkdir();
    }    
}

function _getScopedDomain(subDomain) {
  var d = request.domain;
  if (d.indexOf(".") == -1) {
    // special case for "localhost".  For some reason, firefox does not like cookie domains
    // to be ".localhost".
    return undefined;
  }
  if (subDomain) {
    d = subDomain + "." + d;
  }
  return "." + d;
}

function _runBuild(subdomain, padid)
{
    _prepareBuild(subdomain, padid);

    // pass the domain and session cookie to the script so that
    // it can try to retrieve files as the user
    var domain = _getScopedDomain();
    var cookie = sessions.getSessionId('ES', false, domain);

    var name = _getBuildName(subdomain, padid);
    var path = _getBuildPath(subdomain, padid);
    var url  = _getPadURL(subdomain, padid);
    
    //var cmd = "/var/ethertex/build2.sh"; // config
	var cmd = appjet.config['ethertexBuildCmd'];
	if (!cmd) {
        throw new Error();
	}
    
    var proc = Runtime.getRuntime().exec([cmd, path, _sanitizeFilename(padid), url, name, domain, cookie ]);

    var reader = new BufferedReader(new InputStreamReader(proc.getInputStream()));
    var output = [];
    var line;
    while ((line = reader.readLine()) != null) {
        output.push(line);
    }
    proc.waitFor();
    return output;
}

function _getFileBytes(file)
{
    var fi = new Packages.java.io.File(file);
    var fis = new Packages.java.io.FileInputStream(fi);
    var len = fi.length();
    var bytes = java.lang.reflect.Array.newInstance(Byte.TYPE, len);
    fis.read(bytes, 0, len);
    fis.close();
    return bytes;
}

function onRequest() {  
    var isPro = pro_utils.isProDomainRequest();
    if (!isPro) {
        render404();
    }
    var subdomain = pro_utils.getProRequestSubdomain();
    var userId = padusers.getUserId();
    var isProUser = (isPro && ! padusers.isGuest(userId));

    var names = request.path.split("/");
    var filename = names[names.length-1];
    try {
        var base = _sanitizeFilename(filename.split(".",1)[0]);
        var ext  = _sanitizeFilename(filename.split(".",2)[1]);
    } catch(e) {
        return false;
    }
    if (base + "." + ext != filename) {
        return false;
    }
    if (ext != "log" && ext != "tgz" && ext != "pdf") {
        return false;
    }

    var localPadId = base;
    var globalPadId;

    padutils.accessPadLocal(localPadId, function(pad) {
        if (pad.exists()) {
            globalPadId = pad.getId();
        } else {
            globalPadId = false;
        }
        _checkIfDeleted(pad);
    });
    if (!globalPadId) {
        return false;
    }

    response.neverCache();

    var output = _runBuild(subdomain, localPadId);

    var pdffile = _getFilename(subdomain, localPadId, "pdf");
    if (ext == "pdf") {
        if (_fileExists(pdffile)) {
            var bytes = _getFileBytes(pdffile);
            response.setContentType("application/pdf");
            response.writeBytes(bytes);
            return true;
        }
    }

    var tgzfile = _getFilename(subdomain, localPadId, "tgz");
    if (ext == "tgz") {
        if (_fileExists(tgzfile)) {
            var bytes = _getFileBytes(tgzfile);
            response.setContentType("application/x-gzip");
            response.writeBytes(bytes);
            return true;
        }
    }
    
    response.setContentType("text/html");
    if (!_fileExists(pdffile)) {
        response.writeBytes("<p><b>EtherTeX build failed. Showing output:</b></p>\n");
    }
    response.writeBytes(output.join("<br>\n"));
    if (!_fileExists(pdffile)) {
        response.writeBytes("<p><b>EtherTeX build failed.</b></p>\n");
        response.writeBytes("<script>window.setTimeout(function(){console.log('hello'); window.scrollTo(0,document.body.scrollHeight);}, 10);</script>");
    } else {
        response.writeBytes("<p><b>EtherTeX build succeeded.</b></p>\n");
    }
    return true;
}
