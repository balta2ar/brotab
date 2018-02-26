# Notes

Use this command to print current tabs in firefox:

echo -e 'repl.load("file:///home/ybochkarev/rc.arch/bz/.config/mozrepl/mozrepl.js"); hello(300);' | nc -q0 localhost 4242 | sed '/repl[0-9]*> .\+/!d' | sed 's/repl[0-9]*> //' | rev | cut -c2- | rev | cut -c2- J -C G '"title"' F --no-sort

fr (FiRefox) usage (or br - BRowser):

fr open     open a tab by title
fr close    mark and close multiple tabs

fc close
fo open
fs search

## CompleBox

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

## Multiple extensions/browsers/native apps

[_] differentiate browser instances, how?
[_] support gathering data from multiple mediators
    [+] native mediator should try binding to a free port [4625..4635]
    [_] brotab.py should try a range of ports
[_] build a unified interface for different browsers in background.js
[+] try putting window id into list response

## Roadmap

Install/devops
[_] put helpers (colors) into brotab.sh
[_] create helpers bt-list, bt-move, etc
[_] add integration with rofi
[_] zsh completion for commands
[+] add file with fzf integration: brotab-fzf.zsh
[+] add setup.py, make sure brotab, bt binary is available (python code)

Testing:
[_] how to setup integration testing? w chromium, firefox
    use docker

## Product features

[_] all current operations should be supported on multiple browsers at a time
[_] move should work with multiple browsers and multiple windows
[_] ability to move within window of the same browser
[_] ability to move across windows of the same browser
[_] ability to move across windows of different browsers

## Release procedure

```
$ pandoc --from=markdown --to=rst --output=README.rst README.md
$ python setup.py sdist bdist_wheel --universal
$ twine upload dist/*
```


