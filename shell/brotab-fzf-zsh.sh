#!/bin/bash

#FZF_COMMON="-m --no-sort --reverse --header-lines=1 --inline-info --toggle-sort=\`"

# Tab ID completion for bt close
_fzf_complete_bt() {
  ARGS="$@"
  if [[ $ARGS == 'bt close'* ]] || \
        [[ $ARGS == 'bt activate'* ]] || \
        [[ $ARGS == 'bt words'* ]]; \
  then
    _fzf_complete "-m --no-sort --inline-info --toggle-sort=\`" "$@" < <(
      { bt list }
    )
  else
    eval "zle ${fzf_default_completion:-expand-or-complete}"
  fi
}

_fzf_complete_bt_post() {
  cut -f1 -d$'\t'
}

