# syntax=docker/dockerfile:1

FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntujammy

# set version label
ARG BUILD_DATE
ARG VERSION
ARG CALIBRE_RELEASE
LABEL build_version="Linuxserver.io version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="fletchto99"

ENV \
    CUSTOM_PORT="6080" \
    HOME="/config" \
    TITLE="Nicotine" \
    LISTENING_PORT="2234"

RUN \
    echo "**** install runtime packages ****" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        dbus \
        fcitx-rime \
        fonts-wqy-microhei \
        libnss3 \
        libopengl0 \
        libqpdf28 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-xinerama0 \
        libxkbcommon-x11-0 \
        poppler-utils \
        python3 \
        python3-xdg \
        software-properties-common \
        speech-dispatcher \
        ttf-wqy-zenhei \
        unzip \
        wget \
        xz-utils && \
    echo "**** install nicotine ****" && \
    wget -O debian-package.zip "https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/debian-package.zip" && \
    unzip debian-package.zip -d nicotine_unzip && \
    chmod +x nicotine_unzip/*.deb && \
    apt-get install -y ./nicotine_unzip/*.deb < /dev/null && \
    echo "**** configure system ****" && \
    dbus-uuidgen > /etc/machine-id && \
    sed -i 's|</applications>|  <application title="nicotine plus" type="normal">\n    <maximized>yes</maximized>\n  </application>\n</applications>|' /etc/xdg/openbox/rc.xml && \
    echo "**** cleanup ****" && \
    apt-get autoremove -y && \
    apt-get autoclean && \
    apt-get clean && \
    rm -rf \
        debian-package.zip \
        nicotine_unzip \
        /tmp/* \
        /var/lib/apt/lists/* \
        /var/tmp/* \
        /var/cache/apt/archives/* \
        /var/log/* \
        /usr/share/doc/* \
        /usr/share/man/* \
        /usr/share/locale/* \
        ~/.cache

# add local files
COPY root/ /