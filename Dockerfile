FROM --platform=linux/amd64 ubuntu:latest
COPY ui.patch /tmp
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get -y install software-properties-common &&\
    add-apt-repository 'deb https://ppa.launchpadcontent.net/nicotine-team/stable/ubuntu jammy main' && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y nicotine binutils ca-certificates curl dbus fonts-noto-cjk locales openbox patch supervisor tigervnc-standalone-server tigervnc-tools tzdata --no-install-recommends && \
    dbus-uuidgen > /etc/machine-id && \
    locale-gen en_US.UTF-8 && \
    mkdir /usr/share/novnc && \
    curl -fL# https://github.com/novnc/noVNC/archive/master.tar.gz -o /tmp/novnc.tar.gz && \
    tar -xf /tmp/novnc.tar.gz --strip-components=1 -C /usr/share/novnc && \
    mkdir /usr/share/novnc/utils/websockify && \
    curl -fL# https://github.com/novnc/websockify/archive/master.tar.gz -o /tmp/websockify.tar.gz && \
    tar -xf /tmp/websockify.tar.gz --strip-components=1 -C /usr/share/novnc/utils/websockify && \
    curl -fL# https://site-assets.fontawesome.com/releases/v6.0.0/svgs/solid/cloud-arrow-down.svg -o /usr/share/novnc/app/images/downloads.svg && \
    curl -fL# https://site-assets.fontawesome.com/releases/v6.0.0/svgs/solid/folder-music.svg -o /usr/share/novnc/app/images/shared.svg && \
    curl -fL# https://site-assets.fontawesome.com/releases/v6.0.0/svgs/solid/comments.svg -o /usr/share/novnc/app/images/logs.svg && \
    bash -c 'sed -i "s/<path/<path style=\"fill:white\"/" /usr/share/novnc/app/images/{downloads,logs,shared}.svg' && \
    patch /usr/share/novnc/vnc.html < /tmp/ui.patch && \
    sed -i 's/10px 0 5px/8px 0 6px/' /usr/share/novnc/app/styles/base.css && \
    useradd -u 1000 -U -d /data -s /bin/false nicotine && \
    usermod -G users nicotine && \
    mkdir /data && \
    apt-get purge -y binutils curl dbus patch && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    XDG_RUNTIME_DIR=/data
COPY etc /etc
COPY usr /usr
COPY init.sh /init.sh
ENTRYPOINT ["/init.sh"]
