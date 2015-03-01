#!/bin/bash

PDFLATEX=/usr/local/texlive/2009/bin/x86_64-linux/pdflatex
BIBTEX=/usr/local/texlive/2009/bin/x86_64-linux/bibtex
# (Note: AppArmor should restrict these processes to /var/ethertex/data/*/**)

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export max_print_line=1048576
cd "$1" || exit 1
rm -f "$2.aux" "$2.pdf" "$2.tgz" "$2.bbl" || exit 1

echo -n "<h2>EtherTeX preprocessor</h2>"
/var/ethertex/ethertex2.py "$4" "$3" "$2.tex" "$5" "$6" 2>&1 || exit 1

echo -n "<br><h2>LaTeX</h2>"
$PDFLATEX -interaction=nonstopmode -halt-on-error -draft "$2"  | /var/ethertex/texfilter.py
if [ ${PIPESTATUS[0]} -ne "0" ]; then exit 1; fi

echo -n "<br><h2>BibTeX</h2>"
$BIBTEX "$2" | /var/ethertex/texfilter.py bib

echo -n "<br><h2>LaTeX</h2>"
$PDFLATEX -interaction=nonstopmode -halt-on-error -draft "$2" | /var/ethertex/texfilter.py
if [ ${PIPESTATUS[0]} -ne "0" ]; then exit 1; fi

echo -n "<br><h2>LaTeX (final pass)</h2>"
$PDFLATEX -interaction=nonstopmode -halt-on-error "$2" | /var/ethertex/texfilter.py warn
if [ ${PIPESTATUS[0]} -ne "0" ]; then exit 1; fi

cd ..
tar zcf "$4/$2.tgz" "$4" || exit 1
