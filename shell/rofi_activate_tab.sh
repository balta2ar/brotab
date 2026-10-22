#!/bin/bash

source $HOME/rc.arch/bz/brotab/brotab.sh

DEFAULT_WIDTH=90

if [ "$@" ]; then
    echo "$@" | cut -d$'\t' -f1 | xargs -L1 brotab activate
else
    active_window=`brotab active | \grep firefox | awk '{print $1}'`
    selected=`cached_bt_list \
        | rofi -dmenu -i -multi-select -select "$active_window" -p "Activate tab" -width $DEFAULT_WIDTH \
        | head -1 \
        | cut -d$'\t' -f1`
    if [ "$selected" ]; then
        echo "$selected" | xargs -L1 brotab activate
    fi
fi
