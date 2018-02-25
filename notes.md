Use this command to print current tabs in firefox:

echo -e 'repl.load("file:///home/ybochkarev/rc.arch/bz/.config/mozrepl/mozrepl.js"); hello(300);' | nc -q0 localhost 4242 | sed '/repl[0-9]*> .\+/!d' | sed 's/repl[0-9]*> //' | rev | cut -c2- | rev | cut -c2- J -C G '"title"' F --no-sort

fr (FiRefox) usage (or br - BRowser):

fr open     open a tab by title
fr close    mark and close multiple tabs

fc close
fo open
fs search

# CompleBox

Desired modes:

* insert
    * rt ticket number
    * rt ticket: title
    * ticket url
    * ? insert all: ticket: title (url)
* open rt ticket in a browser

* open sheet ticket in a browser

* activate browser tab
* close browser tab
