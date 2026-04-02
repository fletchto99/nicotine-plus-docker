# syntax=docker/dockerfile:1

FROM ghcr.io/linuxserver/baseimage-selkies:arch

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
  HARDEN_OPENBOX="true"

RUN \
  echo "**** install packages ****" && \
  pacman -Sy --noconfirm \
    "nicotine+" && \
  echo "**** add icon ****" && \
  rsvg-convert -w 256 -h 256 \
    /usr/share/icons/hicolor/scalable/apps/org.nicotine_plus.Nicotine.svg \
    -o /usr/share/selkies/www/icon.png && \
  echo "**** cleanup ****" && \
  printf \
    "version: ${VERSION}\nBuild-date: ${BUILD_DATE}" \
    > /build_version && \
  pacman -Scc --noconfirm && \
  rm -rf \
    /tmp/* \
    /var/cache/pacman/pkg/* \
    /var/lib/pacman/sync/*

# add local files
COPY root/ /

# ports and volumes
VOLUME /config
EXPOSE 6080 6081
