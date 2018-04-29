#!/bin/bash

#
# These are shell helpers for browser tab client (brotab).
#

export BROTAB_CLIENT="$HOME/rc.arch/bz/brotab/brotab_client.py"


#
# Browser Close tabs script
#
function fcl() {
    if [ $# -eq 0 ]; then
        result=$(_list_tabs | _colorize_tabs | fzf --ansi -m --no-sort --prompt="close> " --toggle-sort=\`)
        if [ $? -ne 0 ]; then return $?; fi
    else
        result=`echo "$*" | tr " " "\n"`
    fi
    echo "$result" | while read -r line; do
        id=`echo "$line" | cut -f1 -d' '`
        # echo "Closing tab: $line" >&2
        echo "$id"
    done | xargs bt close
    #done | xargs $BROTAB_CLIENT close_tabs
}

function _colorize_tabs() {
    local YELLOW='\x1b[0;33m'
    local GREEN='\x1b[0;32m'
    local BLUE='\x1b[0;34m'
    local LIGHTGRAY='\x1b[0;37m'
    local NOCOLOR='\x1b[m'
    sed -r "s/(.+)\t(.+)\t(.+)/$YELLOW\1 $GREEN\2 $LIGHTGRAY\3/"
}

function _decolorize_tabs() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]//g"
}

function _activate_browser() {
    if [[ $1 == f.* ]]; then
        wmctrl -R firefox
    elif [[ $1 == c.* ]]; then
        wmctrl -R chromium
    fi
}

function _activate_tab() {
    local strWindowTab=$1
    # echo "Activating tab: $result"
    #$BROTAB_CLIENT activate_tab $strWindowTab
    bt activate $strWindowTab
    _activate_browser $strWindowTab
}

function _close_tabs() {
    bt close
    #$BROTAB_CLIENT close_tabs $*
}

function _list_tabs() {
    bt list
    #$BROTAB_CLIENT list_tabs 1000
}


#
# Browser Open tab script
#
function fo() {
    if [ $# -eq 0 ]; then
        result=$(_list_tabs | _colorize_tabs | fzf --ansi --no-sort --prompt="open> " --toggle-sort=\`)
        if [ $? -ne 0 ]; then return $?; fi
    else
        result=$*
    fi
    strWindowTab=`echo "$result" | cut -f1 -d' '`
    _activate_tab "$strWindowTab"
}


#
# Browser Search tab script
#
function fs() {
    if [ $# -eq 0 ]; then
        echo "Usage: fs <browser> <search query>"
        return 1
    fi

    $BROTAB_CLIENT new_tab $*
    if [ $? -ne 0 ]; then return $?; fi
    _activate_browser $1
}
