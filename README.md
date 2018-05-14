# BroTab

Control your browser's tabs from the terminal.

## About

```
No command has been specified
usage: bt [-h] {move,list,close,activate,search,open,words,dup,windows,clients} ...

bt (brotab = Browser Tabs) is a command-line tool that helps you manage browser tabs. It can
help you list, close, reorder, open and activate your tabs.

positional arguments:
  {move,list,close,activate,search,open,words,dup,windows,clients}
    move                move tabs around. This command lists available tabs and runs the
                        editor. In the editor you can 1) reorder tabs -- tabs will be moved
                        in the browser 2) delete tabs -- tabs will be closed 3) change window
                        ID of the tabs -- tabs will be moved to specified windows
    list                list available tabs. The command will request all available clients
                        (browser plugins, mediators), and will display browser tabs in the
                        following format: "<prefix>.<window_id>.<tab_id><Tab>Page
                        title<Tab>URL"
    close               close specified tab IDs. Tab IDs should be in the following format:
                        "<prefix>.<window_id>.<tab_id>". You can use "list" command to obtain
                        tab IDs (first column)
    activate            activate given tab ID. Tab ID should be in the following format:
                        "<prefix>.<window_id>.<tab_id>"
    search              Not implemented yet.
    open                open URLs from the stdin (one URL per line). One positional argument
                        is required: <prefix>.<window_id> OR <client>. If window_id is not
                        specified, URL will be opened in the active window of the specifed
                        client
    words               show sorted unique words from all active tabs of all clients. This is
                        a helper for webcomplete deoplete plugin that helps complete words
                        from the browser
    dup                 display reminder on how to show duplicate tabs using command-line
                        tools
    windows             display available prefixes and window IDs, along with the number of
                        tabs in every window
    clients             display available browser clients (mediators), their prefixes and
                        address (host:port)

optional arguments:
  -h, --help            show this help message and exit
```

## Demo

Features to show:

* list tabs
* close multiple tabs (fzf)
* move tabs, move, same window
* move tabs, move, different window
* move tabs, move, different browser (NOT IMPLEMENTED)
* move tabs, close
* words, complete in neovim
* open tabs by url
* open tab by google query, search (should be extendable, NOT IMPLEMENTED)
* integration with fzf:
  * activate tab
  * close tabs
* integration with rofi:
  * activate tab
  * close tabs
* show duplicate tabs and close them


## Testing extension

To perform integration tests for the extension, chromium and firefox have
different approaches to load it upon the start.

chromium: google-chrome-stable --disable-gpu --load-extension=./firefox_extension

firefox: use web-ext run
https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Getting_started_with_web-ext


## Author

Yuri Bochkarev

## License

