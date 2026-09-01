FROM ubuntu:24.04

ARG CTNG_UID=1000
ARG CTNG_GID=1000
ARG CTNG_VERSION=1.29.0
ARG CTNG_SHA256=36e4d221088205ee08166d4f8f2f76965117d9f4e6661ec1030ee1e01c62e38c

ENV DEBIAN_FRONTEND=noninteractive

# pkg-config: binutils' configure needs it to find the zstd crosstool-NG builds internally.
RUN apt-get update && apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        bison \
        bzip2 \
        ca-certificates \
        flex \
        g++ \
        gawk \
        gcc \
        git \
        gperf \
        help2man \
        libncurses-dev \
        libstdc++6 \
        libtool \
        libtool-bin \
        make \
        meson \
        ninja-build \
        patch \
        pkg-config \
        python3-dev \
        rsync \
        texinfo \
        unzip \
        wget \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

# ubuntu:24.04 ships a default "ubuntu" user at UID/GID 1000; drop it before reusing that ID.
RUN (getent passwd ubuntu >/dev/null && userdel -r ubuntu || true) \
    && (getent group ubuntu >/dev/null && groupdel ubuntu || true) \
    && groupadd -g "${CTNG_GID}" ctng \
    && useradd -d /home/ctng -m -g "${CTNG_GID}" -u "${CTNG_UID}" -s /bin/bash ctng

# crosstool-NG refuses to run as root.
USER ctng
WORKDIR /home/ctng

RUN wget -q "https://github.com/crosstool-ng/crosstool-ng/archive/refs/tags/crosstool-ng-${CTNG_VERSION}.tar.gz" \
    && echo "${CTNG_SHA256}  crosstool-ng-${CTNG_VERSION}.tar.gz" | sha256sum -c - \
    && tar xzf "crosstool-ng-${CTNG_VERSION}.tar.gz" \
    && rm "crosstool-ng-${CTNG_VERSION}.tar.gz" \
    && mv "crosstool-ng-crosstool-ng-${CTNG_VERSION}" crosstool-ng \
    && cd crosstool-ng \
    && ./bootstrap \
    && ./configure --enable-local \
    && make

ENV PATH="/home/ctng/crosstool-ng:${PATH}"

WORKDIR /home/ctng/build
