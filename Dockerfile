FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install --yes software-properties-common python-software-properties
RUN add-apt-repository ppa:chromium-daily/stable
RUN apt-get install --yes chromium-browser firefox curl xvfb
RUN apt-get install --yes python3-pip sudo mc
RUN apt-get install --yes net-tools htop less
# RUN apt-get install --yes xvfb
# This will install latest Firefox
#RUN apt-get upgrade

ADD xvfb-chromium /usr/bin/xvfb-chromium
# RUN ln -s /usr/bin/xvfb-chromium /usr/bin/google-chrome
# RUN ln -s /usr/bin/xvfb-chromium /usr/bin/chromium-browser

# RUN useradd --create-home --shell /bin/bash user
RUN adduser --disabled-password --gecos '' user
# USER user
WORKDIR /home/user
# WORKDIR /brotab

# xvfb-run chromium-browser --no-sandbox --no-first-run --disable-gpu --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
# curl localhost:9222/json/list
# python3 -m http.server

# cd /brotab && pip3 install -e . && cd /brotab/brotab/firefox_mediator && make install
# chromium-browser --headless --no-sandbox --no-first-run --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
# cat ~/.config/chromium/NativeMessagingHosts/brotab_mediator.json
# py.test brotab/tests/test_integration.py

# docker run -it --rm -v "$(pwd):/brotab" -p 127.0.0.1:10222:9222 brotab
# docker run -it --rm -v "$(pwd):/brotab" -p 10222:9222 brotab

# EXPOSE 10222:9222
EXPOSE 10222
# EXPOSE 8000

RUN /bin/bash

