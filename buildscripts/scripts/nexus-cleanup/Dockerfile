FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y python3-pip \
    && pip3 install nexus3-cli \
    && rm -rf /var/lib/apt/lists/*

COPY nexus3-del-artifacts.py /usr/local/bin/
