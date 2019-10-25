# Development

## Installation in development mode

cd brotab
pip install --user -e .
bt install --tests

In firefox go to: about:debugging#/runtime/this-firefox -> Load temporary addon

In Chrome/Chromium go to: chrome://extensions/ -> Developer mode -> Load
unpacked

You should see the following output:

```txt
$ bt clients
a.      localhost:4625  23744   firefox
b.      localhost:4626  28895   chrome/chromium
```

## Rest

This document serves the purpose of being a reminder to dev

Chrome extension IDs:

Debug:
    "chrome-extension://knldjmfmopnpolahpmmgbagdohdnhkik/"

Prod:
    "chrome-extension://mhpeahbikehnfkfnmopaigggliclhmnc/"

## TODO, things to implement

[_] add config and allow setting debug level.  prod in release, debug in dev
[_] automake deployment of extensions and pypi packaging
[_] automate switching to environments (dev, prod)
[_] add regexp argument to bt words command
    this will allow configuration on vim plugin side

- rofi: close multiple tabs (multiselect), should be opened with current tab
  selected for convenience

## Notes

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

- insert
  - rt ticket number
  - rt ticket: title
  - ticket url
  - ? insert all: ticket: title (url)
- open rt ticket in a browser

- open sheet ticket in a browser

- activate browser tab
- close browser tab

## Multiple extensions/browsers/native apps

[+] differentiate browser instances, how? use prefixes ('a.', 'b.', ...)
[+] support gathering data from multiple mediators
    [+] native mediator should try binding to a free port [4625..4635]
    [+] brotab.py should try a range of ports
[+] build a unified interface for different browsers in background.js
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

[_] full-text search using extenal configured service (e.g. solr)
[_] all current operations should be supported on multiple browsers at a time
[_] move should work with multiple browsers and multiple windows
[_] ability to move within window of the same browser
[_] ability to move across windows of the same browser
[_] ability to move across windows of different browsers

## Bugs

[_] bt move hangs after interacting with chromium
[_] bt close, chromium timeout
[_] bt active is broken with chromium extension
    [_] rofi, activate, close tabs: should select currently active tab
[_] rofi, close tabs: should be multi-selectable

## Release procedure

```bash
$ pandoc --from=markdown --to=rst --output=README.rst README.md
$ python setup.py sdist bdist_wheel --universal
$ twine upload dist/*
```

## Commands

chromium-browser --pack-extension=chrome

To make sure that extension works under selenium, copy brotab_mediator.json to:
/etc/opt/chrome/native-messaging-hosts
