# syntax=docker/dockerfile:1

ARG BASE_IMAGE=ghcr.io/linuxserver/baseimage-selkies:ubuntunoble
FROM ${BASE_IMAGE}

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="fletchto99"

ENV \
  LSIO_FIRST_PARTY="false" \
  TITLE="Nicotine+" \
  LISTENING_PORT="2234" \
  CUSTOM_PORT="6080" \
  CUSTOM_HTTPS_PORT="6081" \
  HARDEN_DESKTOP="true" \
  HARDEN_OPENBOX="true" \
  NO_GAMEPAD="true"

RUN \
  echo "**** install nicotine+ ****" && \
  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    librsvg2-bin \
    unzip && \
  curl -o /tmp/debian-package.zip -L \
    "https://github.com/nicotine-plus/nicotine-plus/releases/download/${VERSION}/debian-package.zip" && \
  unzip /tmp/debian-package.zip -d /tmp/nicotine && \
  DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    /tmp/nicotine/*.deb && \
  echo "**** add icon ****" && \
  rsvg-convert -w 256 -h 256 \
    /usr/share/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine.svg \
    -o /usr/share/selkies/www/icon.png && \
  echo "**** cleanup ****" && \
  printf \
    "version: ${VERSION}\nBuild-date: ${BUILD_DATE}" \
    > /build_version && \
  apt-get purge -y --autoremove \
    unzip && \
  apt-get autoclean && \
  rm -rf \
    /tmp/* \
    /var/lib/apt/lists/*

# add local files
COPY root/ /

# ports and volumes
VOLUME /config
EXPOSE 6080 6081

# healthcheck via the Selkies web UI
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:6080/ || exit 1
