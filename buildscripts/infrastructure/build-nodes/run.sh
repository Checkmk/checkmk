#!/bin/bash
#
docker build . -f ubuntu-22.04/Dockerfile -t rusttest \
    --build-arg IMAGE_UBUNTU_22_04="ubuntu:22.04" \
    --build-arg BRANCH_VERSION="ubuntu:22.04" \
    --build-arg DISTRO="ubuntu-22.04" \
    --build-arg DOCKER_REGISTRY=artifacts.lan.tribe29.com:4000 \
    --build-arg NEXUS_ARCHIVES_URL=https://artifacts.lan.tribe29.com/repository/archives/ \
    --build-arg NEXUS_USERNAME=max.linke \
    --build-arg NEXUS_PASSWORD=H72tao8AGiwayHMGBY8j \
    --build-arg ARTIFACT_STORAGE=https://artifacts.lan.tribe29.com/ \
    --build-arg VERS_TAG=master-2023.06.05-222222222 \
    --build-arg BRANCH_VERSION=2.3.0
