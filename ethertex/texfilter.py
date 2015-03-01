#!/usr/bin/python
# Beautify LaTeX output and convert to HTML
import sys
import re
err = False
warn = False
bib = False
ignoreNext = False
if len(sys.argv) > 1:
    if sys.argv[1] == 'warn': # show warnings that might be spurrious in draft mode
        warn = True
    elif sys.argv[1] == 'bib': # process as bibtex output
        bib = True
        warn = True

for line in sys.stdin.readlines():
    if ignoreNext:
        ignoreNext = False
        continue
    # Lines to completely ignore
    if re.match("^(\* hyperref using|No file .*\.aux|Babel|Transcript written|Type *(H|X)|or enter new name|Enter file name:|See the (pdf|LaT)|Implicit mode|entering extended|\(see the transcript)|For additional information on amsmath", line):
        continue
    if not warn: # Ignore unless showing warnings
        if re.match("^(Over|Under)full .hbox", line):
            ignoreNext = True
            continue
        if re.match("^(Over|Under)full .vbox", line):
            continue
        if  re.match("^(LaTeX Warning: Citation|LaTeX Warning: Reference|LaTeX Warning: There were undefined references.|LaTeX Warning: Label\(s\) may have changed.|pdfTeX warning: \\pdfdraftmode)", line):
            continue
    # Substrings to erase
    line = re.sub('\(/usr/local/texlive/.*\)', '', line)
    line = re.sub('\{/usr/local/texlive/.*\}', '', line)
    line = re.sub('\</usr/local/texlive/.*\>', '', line)
    line = line.replace("/usr/local/texlive/2009/bin/x86_64-linux/pdflatex", "");
    line = line.replace("<", "&lt;").replace(">", "&gt;")
    if not warn:
        line = re.sub('\[\d+\]', '', line)
    line = line.strip()
    if line == '...' or not line:
        continue

    # Color errors red
    if line[0] == '!':
        line = "<span style='color:red; font-weight:bold;'>%s</span>" % (line)
        err = True
    elif err:
        pass
    elif bib and re.match("^I'|I ", line):
        line = "<span style='color:red; font-weight:bold;'>%s</span>" % (line)
    elif bib and re.match("^\(There (was|were) \d+ error", line):
        line = "<span style='color:red; font-weight:bold;'>%s</span>" % (line)
    elif bib and re.match('^: |\(Error|"', line):
        pass
    elif re.match("^((LaTeX W|pdfTeX w)arning:|Warning--)", line):
        if not warn:
            continue
        pass
    else:
        line = "<span style='color:gray;'>%s</span>" % (line)        
    print line


