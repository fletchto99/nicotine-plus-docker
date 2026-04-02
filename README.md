# Nicotine-plus-docker

![Build Status](https://github.com/fletchto99/nicotine-plus-docker/actions/workflows/publish_release.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/nicotine-plus-docker)

[Nicotine+](https://nicotine-plus.org/) is an open source graphical client for the Soulseek peer-to-peer network. As per their website, Nicotine+ aims to be a pleasant, Free and Open Source (FOSS) alternative to the official Soulseek client, providing additional functionality while keeping current with the Soulseek protocol.

## Supported Architectures

| Architecture | Available | Tag |
| :----: | :----: | ---- |
| x86-64 | ✅ | latest |
| arm64 | ✅ | latest |

## Application Setup

The application can be accessed at:

* `http://yourhost:6080/`
* `https://yourhost:6081/`

### Options in all Selkies-based GUI containers

This container is based on LinuxServer's [Docker Baseimage Selkies](https://github.com/linuxserver/docker-baseimage-selkies) which means there are additional environment variables and run configurations to enable or disable specific functionality.

#### Optional environment variables

| Variable | Description |
| :----: | --- |
| `LISTENING_PORT` | Listening port allows other peers on the network to connect to your client and share files. Default is `2234`. |
| `NICOTINE_CLI` | Additional CLI flags to pass to Nicotine+. |
| `CUSTOM_PORT` | Internal port the container listens on for HTTP if it needs to be swapped from the default `6080`. |
| `CUSTOM_HTTPS_PORT` | Internal port the container listens on for HTTPS if it needs to be swapped from the default `6081`. |
| `CUSTOM_USER` | HTTP Basic auth username, `abc` is default. |
| `PASSWORD` | HTTP Basic auth password, `abc` is default. If unset there will be no auth. |
| `SUBFOLDER` | Subfolder for the application if running a subfolder reverse proxy, need both slashes IE `/subfolder/`. |
| `TITLE` | The page title displayed on the web browser, default `Nicotine+`. |
| `FILE_MANAGER_PATH` | Modifies the default upload/download file path, must have proper permissions for `abc` user. |
| `NO_DECOR` | If set, the application will run without window borders for use as a PWA. |
| `LC_ALL` | Set the language for the container IE `fr_FR.UTF-8`. |

### Security Hardening

This container ships with sensible security defaults enabled:

| Variable | Default | Description |
| :----: | :----: | --- |
| `HARDEN_DESKTOP` | `true` | Disables sudo, terminal emulators, and `xdg-open`/`exo-open`. Also hides file transfer and app launcher UI in Selkies sidebar. |
| `HARDEN_OPENBOX` | `true` | Disables close button, right-click/middle-click menus, and escape keybinds. Automatically enables `RESTART_APP` so Nicotine+ restarts if closed. |

These can be overridden by setting the variable to `false` in your environment if needed.

#### Additional hardening options

| Variable | Description |
| :----: | --- |
| `SELKIES_MASTER_TOKEN` | Enables token-based authentication instead of basic auth. See [Selkies docs](https://docs.linuxserver.io/images/docker-baseimage-selkies/#control-plane-api-for-token-management) for details. |
| `SELKIES_CLIPBOARD_ENABLED` | Set to `false` to disable clipboard sync between host and container. |

> **Note:** The built-in basic auth (`PASSWORD`) is a convenience feature, not a robust security mechanism. For internet-facing deployments, place the container behind a reverse proxy with proper authentication (e.g. [SWAG](https://github.com/linuxserver/docker-swag)).

#### Optional run configurations

| Variable | Description |
| :----: | --- |
| `--device /dev/dri:/dev/dri` | Mount a GPU into the container for hardware acceleration. Only **Open Source** drivers are supported (Intel, AMDGPU, Radeon, ATI, Nouveau). |
| `--shm-size=1gb` | Recommended for stability. Sets the shared memory size available to the container. |

## Usage

Here are some example snippets to help you get started creating a container.

### docker-compose (recommended)

```yaml
---
services:
  nicotine-plus:
    image: ghcr.io/fletchto99/nicotine-plus-docker:latest
    container_name: nicotine-plus
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - PASSWORD= #optional
      - LISTENING_PORT=2234 #optional
    volumes:
      - /path/to/data:/config
      - /path/to/downloads:/data/downloads
      - /path/to/incomplete:/data/incomplete_downloads
      - /path/to/shared:/data/shared #optional
    ports:
      - 6080:6080
      - 6081:6081
      - 2234-2239:2234-2239
    shm_size: "1gb"
    restart: unless-stopped
```

### docker cli

```bash
docker run -d \
  --name=nicotine-plus \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=Etc/UTC \
  -e PASSWORD= `#optional` \
  -e LISTENING_PORT=2234 `#optional` \
  -p 6080:6080 \
  -p 6081:6081 \
  -p 2234-2239:2234-2239 \
  -v /path/to/data:/config \
  -v /path/to/downloads:/data/downloads \
  -v /path/to/incomplete:/data/incomplete_downloads \
  -v /path/to/shared:/data/shared `#optional` \
  --shm-size="1gb" \
  --restart unless-stopped \
  ghcr.io/fletchto99/nicotine-plus-docker:latest
```

## Parameters

Container images are configured using parameters passed at runtime (such as those above). These parameters are separated by a colon and indicate `<external>:<internal>` respectively. For example, `-p 3001:3001` would expose port `3001` from inside the container to be accessible from the host's IP on port `3001` outside the container.

| Parameter | Function |
| :----: | --- |
| `-p 6080` | Nicotine+ desktop gui (HTTP). |
| `-p 6081` | Nicotine+ desktop gui (HTTPS). |
| `-p 2234-2239` | Nicotine+ P2P ports. |
| `-e PUID=1000` | for UserID - see below for explanation. |
| `-e PGID=1000` | for GroupID - see below for explanation. |
| `-e TZ=Etc/UTC` | specify a timezone to use, see this [list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List). |
| `-e PASSWORD=` | Optionally set a password for the gui. |
| `-e LISTENING_PORT=2234` | Set the P2P listening port (default 2234). |
| `-e NICOTINE_CLI=` | Pass additional CLI flags to Nicotine+. |
| `-v /config` | Where Nicotine+ should store configuration and queue data. |
| `-v /data/downloads` | Where Nicotine+ should store complete downloads. |
| `-v /data/incomplete_downloads` | Where Nicotine+ should store data during the download process. |
| `-v /data/shared` | A location for you to share data (files/folders) on Nicotine+. |
| `--shm-size=1gb` | Recommended for stability. |

## Environment variables from files (Docker secrets)

You can set any environment variable from a file by using a special prepend `FILE__`.

As an example:

```bash
-e FILE__PASSWORD=/run/secrets/mysecretpassword
```

Will set the environment variable `PASSWORD` based on the contents of the `/run/secrets/mysecretpassword` file.

## Umask for running applications

For all of our images we provide the ability to override the default umask settings for services started within the containers using the optional `-e UMASK=022` setting.
Keep in mind umask is not chmod it subtracts from permissions based on its value it does not add. Please read up [here](https://en.wikipedia.org/wiki/Umask) before asking for support.

## User / Group Identifiers

When using volumes (`-v` flags) permissions issues can arise between the host OS and the container, we avoid this issue by allowing you to specify the user `PUID` and group `PGID`.

Ensure any volume directories on the host are owned by the same user you specify and any permissions issues will vanish like magic.

In this instance `PUID=1000` and `PGID=1000`, to find yours use `id user` as below:

```bash
  $ id username
    uid=1000(dockeruser) gid=1000(dockergroup) groups=1000(dockergroup)
```

## Support Info

* Shell access whilst the container is running: `docker exec -it nicotine-plus /bin/bash`
* To monitor the logs of the container in realtime: `docker logs -f nicotine-plus`
* container version number
  * `docker inspect -f '{{ index .Config.Labels "build_version" }}' nicotine-plus`
* image version number
  * `docker inspect -f '{{ index .Config.Labels "build_version" }}' ghcr.io/fletchto99/nicotine-plus-docker:latest`

## Building locally

If you want to make local modifications to these images for development purposes or just to customize the logic:

```bash
git clone https://github.com/fletchto99/nicotine-plus-docker.git
cd nicotine-plus-docker
docker build \
  --no-cache \
  --pull \
  -t ghcr.io/fletchto99/nicotine-plus-docker:latest .
```

## Versions

* **02.04.26:** - Migrated to baseimage-selkies (from baseimage-kasmvnc). Arch Linux base with Wayland support.
* **19.07.23:** - Initial release.
