#!/bin/bash

#FZF_COMMON="-m --no-sort --reverse --header-lines=1 --inline-info --toggle-sort=\`"

# Tab ID completion for brotab close
_fzf_complete_bt() {
  ARGS="$@"
  if [[ $ARGS == 'brotab close'* ]] || \
        [[ $ARGS == 'brotab activate'* ]] || \
        [[ $ARGS == 'brotab text'* ]] || \
        [[ $ARGS == 'brotab html'* ]] || \
        [[ $ARGS == 'brotab words'* ]]; \
  then
    _fzf_complete --multi --no-sort --inline-info --toggle-sort=\` -- "$@" < <(
      { brotab list }
    )
  else
    eval "zle ${fzf_default_completion:-expand-or-complete}"
  fi
}

_fzf_complete_bt_post() {
  cut -f1 -d$'\t'
}

