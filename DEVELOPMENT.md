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

  // Extension ID: knldjmfmopnpolahpmmgbagdohdnhkik
  "key": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDcBHwzDvyBQ6bDppkIs9MP4ksKqCMyXQ/A52JivHZKh4YO/9vJsT3oaYhSpDCE9RPocOEQvwsHsFReW2nUEc6OLLyoCFFxIb7KkLGs
mfakkut/fFdNJYh0xOTbSN8YvLWcqph09XAY2Y/f0AL7vfO1cuCqtkMt8hFrBGWxDdf9CQIDAQAB",

Prod:
    "chrome-extension://mhpeahbikehnfkfnmopaigggliclhmnc/"

## TODO, things to implement

[_] provide zsh completion: ~/rc.arch/bz/.config/zsh/completion/_bt
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

Getting data from PDF page:

Firefox:
var d = await window.PDFViewerApplication.pdfDocument.getData()
Uint8Array(100194) [ 37, 80, 68, 70, 45, 49, 46, 51, 10, 37, … ]

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
# bump bersion in brotab/__version__.py
$ python setup.py sdist bdist_wheel
$ twine upload dist/*

$ nvim CHANGELOG.md
$ git ci -m 'Bump version from 0.0.3 to 0.0.5'
$ git tag 0.0.5
$ git push origin master && git push --tags
```

Go to Github tags and manually create a release from the tag:
https://github.com/balta2ar/brotab/tags

Load env file as follows:
set -o allexport; source .env; set +o allexport

## Commands

chromium-browser --pack-extension=chrome

To make sure that extension works under selenium, copy brotab_mediator.json to:
/etc/opt/chrome/native-messaging-hosts

## Testing extension

To perform integration tests for the extension, chromium and firefox have
different approaches to load it upon the start.

### Chromium

chromium: google-chrome-stable --disable-gpu --load-extension=./firefox_extension

Chromium is a bit more demading. Several conditions are required before you can
run Chromium in Xvfb in integration tests:

1. Use extension from brotab/extension/chrome-tests. It contains the correct
   fake Key and extension ID (knldjmfmopnpolahpmmgbagdohdnhkik). The same
   extension ID is installed when you run `bt install` command in Docker.
   This very extension ID is also present in
   brotab/mediator/chromium_mediator_tests.json, which is used in `bt install`.

firefox: use web-ext run
https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Getting_started_with_web-ext

