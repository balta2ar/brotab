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
