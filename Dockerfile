FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install --yes software-properties-common python-software-properties \
    python-setuptools python-dev build-essential apt-transport-https curl \
    chromium-browser firefox curl xvfb python3-pip sudo mc net-tools htop \
    less lsof
#RUN add-apt-repository ppa:chromium-daily/stable
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get update
#RUN apt-get install --yes chromium-browser firefox curl xvfb python3-pip sudo mc net-tools htop less
# RUN apt-get install --yes xvfb
# This will install latest Firefox
#RUN apt-get upgrade

#RUN curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add -
#RUN echo "deb https://deb.nodesource.com/node_8.x xenial main" | sudo tee /etc/apt/sources.list.d/nodesource.list
#RUN echo "deb-src https://deb.nodesource.com/node_8.x xenial main" | sudo tee -a /etc/apt/sources.list.d/nodesource.list

RUN apt-get install --yes nodejs

# RUN mkdir /root/.npm-global
# ENV PATH=/root/.npm-global/bin:$PATH
# ENV NPM_CONFIG_PREFIX=/root/.npm-global

RUN npm install --global web-ext --unsafe

RUN easy_install pip
RUN pip3 install flask httpie
# RUN pip3 install -r /brotab/requirements.txt
#RUN cd /brotab && pip3 install -e .

ADD xvfb-chromium /usr/bin/xvfb-chromium
# RUN ln -s /usr/bin/xvfb-chromium /usr/bin/google-chrome
# RUN ln -s /usr/bin/xvfb-chromium /usr/bin/chromium-browser

# RUN useradd --create-home --shell /bin/bash user
RUN adduser --disabled-password --gecos '' user
# USER user
#WORKDIR /home/user
WORKDIR /brotab

# xvfb-run chromium-browser --no-sandbox --no-first-run --disable-gpu --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
# curl localhost:9222/json/list
# python3 -m http.server

# cd /brotab && pip3 install -e . && cd /brotab/brotab/firefox_mediator && make install
# chromium-browser --headless --no-sandbox --no-first-run --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
# cat ~/.config/chromium/NativeMessagingHosts/brotab_mediator.json
# py.test brotab/tests/test_integration.py

# docker run -it --rm -v "$(pwd):/brotab" -p 127.0.0.1:10222:9222 brotab
# docker run -it --rm -v "$(pwd):/brotab" -p 10222:9222 brotab

# run this on host to be able to view chromimum GUI:
# xhost local:docker
# xhost local:root

# docker run -ti --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix firefox
# docker run -it --rm -v "$(pwd):/brotab" -p 10222:9222 -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix brotab
# xvfb-run chromium-browser --no-sandbox --no-first-run --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
# xvfb-run chromium-browser --no-sandbox --no-first-run --disable-gpu --load-extension=/brotab/brotab/extension/chrome

# cd /brotab/brotab/firefox_extension
# web-ext run

# test list tabs:
# curl 'http://localhost:4625/list_tabs'

# EXPOSE 10222:9222
#EXPOSE 10222
# EXPOSE 8000

RUN /bin/bash

