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
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    poppler-utils \
    python3 \
    python3-xdg \
    software-properties-common \
    ttf-wqy-zenhei \
    wget \
    xz-utils && \
    apt-get install -y \
    speech-dispatcher && \
    echo "**** install nicotine ****" && \
    add-apt-repository 'deb https://ppa.launchpadcontent.net/nicotine-team/stable/ubuntu jammy main' && \
    apt-get update &&\
    apt-get install -y nicotine && \
    dbus-uuidgen > /etc/machine-id && \
    sed -i 's|</applications>|  <application title="nicotine plus" type="normal">\n    <maximized>yes</maximized>\n  </application>\n</applications>|' /etc/xdg/openbox/rc.xml && \
    echo "**** cleanup ****" && \
    apt-get clean && \
    rm -rf \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*

# add local files
COPY root/ /