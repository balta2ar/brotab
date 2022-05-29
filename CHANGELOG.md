1.4.1 (2022-05-29)

* Better syntax for navigate and update:
  > bt navigate b.1.862 "https://google.com"
  > bt update -tabId b.1.862 -url="http://www.google.com" 

1.4.0 (2022-05-29)

* Added "bt navigate" and "bt update" commands

* Fix "bt open" and "bt new": now they print tab IDs of the created tabs, one
  per line

1.3.0 (2020-06-02)

* Added "bt html" command #31, #34

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
  "bt install" (Windows only)
* detect user's temporary directory (Windows-related fix)
* use "notepad" editor for "bt move" command on Windows
* add optional tab_ids filter to "bt text [tab_id]" command

1.1.0 (2019-12-15)

* add "query" command that allows for more fine-tuned querying of tabs

1.0.6 (2019-12-08)

* print all active tabs from all windows (#8)
* autorotate mediator logs to make sure it doesn't grow too large
* make sure mediator (flask) works in single-threaded mode
* bt words, bt text, bt index now support customization of regexpes
  that are used to match words, split text and replacement/join strings

0.0.5 (2019-10-27)

Console client requests only those mediator ports that are actually available.
