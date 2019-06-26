#!/bin/bash

ACTIVE_WINDOW=/tmp/rofi_active_window.txt
SELECTED_LINES=/tmp/rofi_selected_lines.txt
ACTION=/tmp/rofi_action.txt
MODE=${1:-rt}

# Reset state
echo -n "" > $SELECTED_LINES
echo -n "" > $ACTION
xdotool getactivewindow > $ACTIVE_WINDOW

DEFAULT_WIDTH=90

MODI=""
SELECT=""
if [ "$MODE" == "tab" ]; then
    MODI+=",activate_tab:rofi_activate_tab.sh"
    MODI+=",close_tabs:rofi_close_tabs.sh"
    DEFAULT_MODE=activate_tab
else
    echo "Unknown mode: $MODE. Known modes: rt, tab"
    exit 1
fi

# source $HOME/rc.arch/bz/.config/fzf/bz-completion.zsh
# Mode scripts will use this var
export SECOND_COL_WIDTH=97

tab_menu_mode() {
    mode=$(echo -e "activate\nclose" | rofi -dmenu -p "What would you like to do with browser tabs?" -width $DEFAULT_WIDTH)
    if [ "$mode" == "activate" ]; then
        rofi_activate_tab.sh
    elif [ "$mode" == "close" ]; then
        rofi_close_tabs.sh
    fi
}

if [ "$MODE" == "tab" ]; then
    tab_menu_mode
fi
