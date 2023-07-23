# [fletchto99/nicotine-plus-docker](fletchto99/nicotine-plus-docker)

![GHCR Build Status](https://github.com/fletchto99/nicotine-plus-docker/actions/workflows/ghcr.yml/badge.svg)
![Docker Build Status](https://github.com/fletchto99/nicotine-plus-docker/actions/workflows/docker.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/fletchto99/nicotine-plus-docker)

[Nicotine-plus](https://nicotine-plus.org/) is an open source graphical client for the Soulseek peer-to-peer network. As per their website, Nicotine+ aims to be a pleasent, Free and Open Source (FOSS) alternative to the official Soulseek client, providing additional functionality while keeping current with the Soulseek protocol.

## Application Setup

This image sets up the nicotine+ desktop app and makes its interface available via Guacamole server in the browser. The interface is available at `http://your-ip:6080`.

By default, there is no password set for the main gui. Optional environment variable `PASSWORD` will allow setting a password for the user `abc`, via http auth.

### Options in all KasmVNC based GUI containers

This container is based on LinuxServer's [Docker Baseimage KasmVNC](https://github.com/linuxserver/docker-baseimage-kasmvnc) which means there are additional environment variables and run configurations to enable or disable specific functionality.

#### Optional environment variables

| Variable | Description |
| :----: | --- |
| CUSTOM_PORT | Internal port the container listens on for http if it needs to be swapped from the default 8080. |
| CUSTOM_USER | HTTP Basic auth username, abc is default. |
| PASSWORD | HTTP Basic auth password, abc is default. If unset there will be no auth |
| SUBFOLDER | Subfolder for the application if running a subfolder reverse proxy, need both slashes IE `/subfolder/` |
| TITLE | The page title displayed on the web browser, default "KasmVNC Client". |
| FM_HOME | This is the home directory (landing) for the file manager, default "/config". |
| START_DOCKER | If set to false a container with privilege will not automatically start the DinD Docker setup. |
| DRINODE | If mounting in /dev/dri for [DRI3 GPU Acceleration](https://www.kasmweb.com/kasmvnc/docs/master/gpu_acceleration.html) allows you to specify the device to use IE `/dev/dri/renderD128` |

#### Optional run configurations

| Variable | Description |
| :----: | --- |
| `--privileged` | Will start a Docker in Docker (DinD) setup inside the container to use docker in an isolated environment. For increased performance mount the Docker directory inside the container to the host IE `-v /home/user/docker-data:/var/lib/docker`. |
| `-v /var/run/docker.sock:/var/run/docker.sock` | Mount in the host level Docker socket to either interact with it via CLI or use Docker enabled applications. |
| `--device /dev/dri:/dev/dri` | Mount a GPU into the container, this can be used in conjunction with the `DRINODE` environment variable to leverage a host video card for GPU accelerated appplications. Only **Open Source** drivers are supported IE (Intel,AMDGPU,Radeon,ATI,Nouveau) |

### Lossless mode

This container is capable of delivering a true lossless image at a high framerate to your web browser by changing the Stream Quality preset to "Lossless", more information [here](https://www.kasmweb.com/docs/latest/how_to/lossless.html#technical-background). If using a reverse proxy to port 80860800 specific headers will need to be set as outlined [here](https://github.com/linuxserver/docker-baseimage-kasmvnc#lossless).

## Usage

Here are some example snippets to help you get started creating a container.

### docker-compose (recommended)

```yaml
---
version: "2.1"
services:
  nicotine-plus:
    image: ghcr.io/fletchto99/nicotine-plus-docker:latest
    container_name: nicotine-plus
    security_opt:
      - seccomp:unconfined #optional
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - PASSWORD= #optional
    volumes:
      - /path/to/data:/config
      - /path/to/downloads:/data/downloads
      - /path/to/incomplete:/data/incomplete_downloads
      - /path/to/shared:/data/shared #optional
    ports:
      - 6080:6080
      - 2234-2239:2234-2239
    restart: unless-stopped
```

### docker cli

```bash
docker run -d \
  --name=nicotine-plus \
  --security-opt seccomp=unconfined `#optional` \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=Etc/UTC \
  -e PASSWORD= `#optional` \
  -p 6080:6080 \
  -p 2234-2239:2234-2239 \
  -v /path/to/data:/config \
  -v /path/to/downloads:/data/downloads \
  -v /path/to/incomplete:/data/incomplete_downloads \
  -v /path/to/shared:/data/shared `#optional` \
  --restart unless-stopped \
  ghcr.io/fletchto99/nicotine-plus-docker:latest

```

## Parameters

Container images are configured using parameters passed at runtime (such as those above). These parameters are separated by a colon and indicate `<external>:<internal>` respectively. For example, `-p 6080:80` would expose port `80` from inside the container to be accessible from the host's IP on port `6080` outside the container.

| Parameter | Function |
| :----: | --- |
| `-p 6080` | Nicotine plus desktop gui. |
| `-p 2234-2239` | Nicotine plu P2P Ports. |
| `-e PUID=1000` | for UserID - see below for explanation |
| `-e PGID=1000` | for GroupID - see below for explanation |
| `-e TZ=Etc/UTC` | specify a timezone to use, see this [list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List). |
| `-e PASSWORD=` | Optionally set a password for the gui. |
| `-v /config` | Where nicotine plus should store configuration and queue data. |
| `-v /data/downloads` | Where nicotine plus should store complete downloads |
| `-v /data/incomplete_downloads` | Where nicotine plus should store data during the download process |
| `-v /data/shared` | A location for you to share data (files/folders) on nicotine plus. |
| `--security-opt seccomp=unconfined` | For Docker Engine only, many modern gui apps need this to function as syscalls are unkown to Docker. |

## Environment variables from files (Docker secrets)

You can set any environment variable from a file by using a special prepend `FILE__`.

As an example:

```bash
-e FILE__PASSWORD=/run/secrets/mysecretpassword
```

Will set the environment variable `PASSWORD` based on the contents of the `/run/secrets/mysecretpassword` file.

## Umask for running applications

For all of our images we provide the ability to override the default umask settings for services started within the containers using the optional `-e UMASK=022` setting.
Keep in mind umask is not chmod it subtracts from permissions based on it's value it does not add. Please read up [here](https://en.wikipedia.org/wiki/Umask) before asking for support.

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
  * `docker inspect -f '{{ index .Config.Labels "build_version" }}' nicotine-plus-docker`
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

* **19.07.23:** - Initial release.