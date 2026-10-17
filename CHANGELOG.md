2.0.15 (2026-10-17)

* Add `bruvtab close --playing` and `bruvtab close --muted` to close all audible or muted tabs
* Add the `query` filters (`-url`, `-title`, `+pinned`, ...) to `bruvtab close`, which then closes the tabs they match
* Fix `bruvtab query` printing nothing for any filter, and `bruvtab update` with property flags crashing
* Fix `bruvtab close` with several browsers connected closing tabs in the wrong browser
* Fix `bruvtab update -info` crashing, and accept a single JSON object as well as a list
* Fix `bruvtab move` failing with HTTP 500

2.0.14 (2026-06-03)

* Add `playing` and `muted` tab status to `bruvtab list` output, plus `--playing` / `--muted` filters
* Add `bruvtab play`, `pause`, `mute` and `unmute` media control commands; `pause` and `mute` default to the first audible tab, `play` and `unmute` to the active tab, and all accept a tab ID, a title/URL fragment, `--playing` or `--muted`
* Add `bruvtab activate --playing` to jump to the first audible tab
* Add `-j` as shorthand for `--json`
* Add `--debug` for details on failed commands, and report media control errors instead of failing silently
* Add `--no-wrap` to disable wrapping of table columns, and tidy up human-readable output
* Improve shell completion, including tab ID completion for media commands

2.0.13 (2026-05-05)

* Accept a title or URL fragment wherever a tab ID is expected
* Filter `bruvtab list` by title or URL fragments
* Add `bruvtab screenshot --wait SECONDS`
* Add bash and zsh completions via `argcomplete`
* Document installation and development with `uv`
* Publish to the Chrome Web Store in parallel with other release jobs

2.0.12 (2026-05-05)

* Fix tab-targeted screenshots

2.0.11 (2026-05-05)

* No user-visible changes (version bump)

2.0.10 (2026-05-05)

* Publish a self-hosted Chrome update manifest with GitHub releases, so Chromium can auto-update the extension

2.0.8 (2026-05-05)

* Add an optional tab ID to `bruvtab screenshot` to capture a specific tab
* Fetch only the requested tab when `bruvtab text` or `html` gets a single tab ID

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

* Rename the project from brotab to bruvtab (fork of https://github.com/balta2ar/brotab)
* Add a Nix flake with packages for the CLI, the Chrome CRX and the Firefox add-on
* Add a global `--json` flag with pretty, colored output
* Colorize `--help` output with `rich-argparse`
* Build and publish browser extension artifacts from CI
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
