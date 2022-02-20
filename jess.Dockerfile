# Adjusted based on: https://github.com/jessfraz/dockerfiles/blob/master/chromium/Dockerfile

FROM debian:bullseye-slim
LABEL maintainer "Jessie Frazelle <jess@linux.com>"

RUN apt-get update && apt-get install -y \
      chromium \
      chromium-l10n \
      fonts-liberation \
      fonts-roboto \
      hicolor-icon-theme \
      libcanberra-gtk-module \
      libexif-dev \
      libgl1-mesa-dri \
      libgl1-mesa-glx \
      libpangox-1.0-0 \
      libv4l-0 \
      fonts-symbola \
      python3 python3-pip \
      socat curl net-tools \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/chromium.d/ \
    && /bin/echo -e 'export GOOGLE_API_KEY="AIzaSyCkfPOPZXDKNn8hhgu3JrA62wIgC93d44k"\nexport GOOGLE_DEFAULT_CLIENT_ID="811574891467.apps.googleusercontent.com"\nexport GOOGLE_DEFAULT_CLIENT_SECRET="kdloedMFGdGla2P1zacGjAQh"' > /etc/chromium.d/googleapikeys

# Add chromium user
# RUN groupadd -r chromium && useradd -m -r -g chromium -G audio,video chromium \
#     && mkdir -p /home/chromium/Downloads && chown -R chromium:chromium /home/chromium \
#     && mkdir /brotab && chown -R chromium:chromium /brotab
# # Run as non privileged user
# USER chromium

COPY requirements/base.txt /tmp/base.txt
RUN pip3 install -r /tmp/base.txt

COPY startup.sh /bin/startup.sh
WORKDIR /brotab
ENTRYPOINT [ "/bin/startup.sh" ]
#ENTRYPOINT [ "/bin/bash" ]
# ENTRYPOINT [ "/usr/bin/chromium" ]
# CMD [ "--user-data-dir=/data" ]
