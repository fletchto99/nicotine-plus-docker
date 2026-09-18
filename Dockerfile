# syntax=docker/dockerfile:1

FROM ghcr.io/linuxserver/baseimage-selkies:debiantrixie

ARG VERSION

ENV \
  LSIO_FIRST_PARTY="false" \
  TITLE="Nicotine+" \
  LISTENING_PORT="2234" \
  CUSTOM_PORT="6080" \
  CUSTOM_HTTPS_PORT="6081" \
  HARDEN_DESKTOP="true" \
  HARDEN_OPENBOX="true" \
  NO_GAMEPAD="true" \
  START_DOCKER="false" \
  SELKIES_SECOND_SCREEN="false" \
  SELKIES_MICROPHONE_ENABLED="false" \
  SELKIES_GAMEPAD_ENABLED="false" \
  SELKIES_ENABLE_PLAYER2="false" \
  SELKIES_ENABLE_PLAYER3="false" \
  SELKIES_ENABLE_PLAYER4="false" \
  SELKIES_UI_SIDEBAR_SHOW_GAMEPADS="false" \
  SELKIES_UI_SIDEBAR_SHOW_GAMING_MODE="false" \
  SELKIES_UI_SIDEBAR_SHOW_SHARING="false" \
  SELKIES_UI_SIDEBAR_SHOW_TRACKPAD="false"

RUN \
  if [ -z "$VERSION" ]; then \
    echo "ERROR: VERSION is required. Pass --build-arg VERSION=<Nicotine+ release>." >&2; \
    exit 1; \
  fi && \
  echo "**** install nicotine+ ****" && \
  apt-get -o Acquire::Retries=3 update && \
  curl --fail --show-error --location \
    --retry 3 --connect-timeout 15 --max-time 120 \
    -o /tmp/debian-package.zip \
    "https://github.com/nicotine-plus/nicotine-plus/releases/download/${VERSION}/debian-package.zip" && \
  curl --fail --show-error --location \
    --retry 3 --connect-timeout 15 --max-time 120 \
    -o /tmp/debian-package.zip.sha256 \
    "https://github.com/nicotine-plus/nicotine-plus/releases/download/${VERSION}/debian-package.zip.sha256" && \
  (cd /tmp && sha256sum --check --strict debian-package.zip.sha256) && \
  python3 -m zipfile -e /tmp/debian-package.zip /tmp/nicotine && \
  DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 install --no-install-recommends -y \
    librsvg2-common \
    /tmp/nicotine/*.deb && \
  echo "**** cleanup ****" && \
  apt-get autoclean && \
  rm -rf \
    /tmp/* \
    /var/lib/apt/lists/*

# add local files
COPY root/ /

ARG BUILD_DATE
LABEL \
  build_version="version:- ${VERSION} Build-date:- ${BUILD_DATE}" \
  maintainer="fletchto99" \
  org.opencontainers.image.source="https://github.com/fletchto99/nicotine-plus-docker" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}"

RUN printf 'version: %s\nBuild-date: %s\n' "$VERSION" "$BUILD_DATE" > /build_version

# ports and volumes
VOLUME /config
EXPOSE 6080 6081

# healthcheck via the Selkies web UI
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl --fail --silent --show-error "http://localhost:${CUSTOM_PORT:-6080}/" || exit 1
