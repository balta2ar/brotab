Unreleased

* Fix `bruvtab query` printing nothing for any filter, and `bruvtab update` with property flags crashing

2.0.7 (2026-05-05)

* Fix native messaging timeout handling with buffered browser messages
* Reattach browser extension listeners after native host reconnects

2.0.6 (2026-05-05)

* Fix Firefox screenshot handling and avoid wedging mediator communication on add-on errors
* Add global client/browser targeting flags for CLI commands
* Add raw image output for `bruvtab screenshot --raw`

2.0.5 (2026-05-04)

* Raise Firefox minimum version to 142.0 for AMO data collection permission metadata

2.0.4 (2026-05-04)

* Publish self-distributed Firefox XPIs with the plain `bruvtab-firefox-$VERSION.xpi` release asset name

2.0.3 (2026-05-04)

* Publish listed AMO releases and separate self-distributed Firefox XPIs
* Fetch signed Firefox XPIs from GitHub release assets for Nix packaging

2.0.2 (2026-04-23)

* Switch Firefox releases to self-distributed signed XPI uploads on GitHub releases
* Fix Chrome CRX packaging in GitHub Actions and upload browser artifacts from the release workflow
* Simplify flake browser outputs and clean up shared browser IDs / version variables

2.0.1 (2026-04-23)

* Sign Firefox add-on and package the signed XPI for Home Manager / NixOS
* Rename Firefox mediator host to `bruvtab_mediator`
* Fix single-tab close behavior and Chrome browser detection

2.0.0 (2025-01-22)

* manifest v3 support for Google Chrome extension
* json output for "bruvtab list" command

1.5.0 (2025-01-22)

* Added "bruvtab screenshot" command
* Fixed some dependencies in requirements/base.txt

1.4.2 (2022-05-29)

* Support config file in `$XDG_CONFIG_HOME/bruvtab/bruvtab.env`:
```env
HTTP_IFACE=0.0.0.0
MIN_HTTP_PORT=4625 
MAX_HTTP_PORT=4635 
```
  This is useful if you want to change interface mediator is binding to.

1.4.1 (2022-05-29)

* Better syntax for navigate and update:
  > bruvtab navigate b.1.862 "https://google.com"
  > bruvtab update -tabId b.1.862 -url="http://www.google.com" 

1.4.0 (2022-05-29)

* Added "bruvtab navigate" and "bruvtab update" commands

* Fix "bruvtab open" and "bruvtab new": now they print tab IDs of the created tabs, one
  per line

1.3.0 (2020-06-02)

* Added "bruvtab html" command #31, #34

1.2.2 (2020-05-05)

* Added Brave Browser support #29

1.2.1 (2020-02-19)

* fix setup.py and add smoke integration tests to build package and run the app

1.2.0 (2020-02-16)

* add "--target" argument to disable automatic mediator discovery and be
  able to specify mediator's host:port address. Multiple entries are
  separated with a comma, e.g. --target "localhost:2000,127.0.0.1:3000"
* add "--focused" argument to "activate" tab command. This will bring browser
  into focus
* automatically register native app manifest in the Windows Registry when doing
  "bruvtab install" (Windows only)
* detect user's temporary directory (Windows-related fix)
* use "notepad" editor for "bruvtab move" command on Windows
* add optional tab_ids filter to "bruvtab text [tab_id]" command

1.1.0 (2019-12-15)

* add "query" command that allows for more fine-tuned querying of tabs

1.0.6 (2019-12-08)

* print all active tabs from all windows (#8)
* autorotate mediator logs to make sure it doesn't grow too large
* make sure mediator (flask) works in single-threaded mode
* bruvtab words, bruvtab text, bruvtab index now support customization of regexpes
  that are used to match words, split text and replacement/join strings

0.0.5 (2019-10-27)

Console client requests only those mediator ports that are actually available.
