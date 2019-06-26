#!/bin/bash

source $HOME/rc.arch/bz/brotab/brotab.sh

DEFAULT_WIDTH=90

if [ "$@" ]; then
    echo "$@" | cut -d$'\t' -f1 | xargs -L1 bt close
    bt list
else
    active_window=`bt active | \grep firefox | awk '{print $1}'`
    selected=`cached_bt_list \
        | rofi -dmenu -i -multi-select -select "$active_window" -p "Close tab" -width $DEFAULT_WIDTH \
        | cut -d$'\t' -f1`
    if [ "$selected" ]; then
        echo "$selected" | xargs -L1 bt close
    fi
fi
