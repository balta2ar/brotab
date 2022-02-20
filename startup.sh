#!/usr/bin/env bash

IF_PUBLIC=172.17.0.2
IF_PRIVATE=127.0.0.1

socat TCP4-LISTEN:9222,fork,reuseaddr,bind=$IF_PUBLIC TCP4:$IF_PRIVATE:9222 &
socat TCP4-LISTEN:4625,fork,reuseaddr,bind=$IF_PUBLIC TCP4:$IF_PRIVATE:4625 &

cd /brotab \
  && pip install -e . \
  && bt install --tests \
  && chromium --no-sandbox --disable-gpu --remote-debugging-address=$IF_PRIVATE --remote-debugging-port=9222 --load-extension=/brotab/brotab/extension/chrome file:///
