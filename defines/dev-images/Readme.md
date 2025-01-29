# Checkmk distro, build and reference images

This document describes the current use of Docker images in development workflows.

## Distro-Images

* pinned as image aliases
* from docker hub where available, homegrown for SLES
* located at `buildscripts/infrastructure/build-nodes`


## Build images

* Used for building CMK packages
* Nested builds to avoid leaking of credentials
* Tagged `<DISTRO>:<BRANCH>-latest` and `<DISTRO>:<BRANCH>-<DATE>-<GIT-SHA>`

This will create a 'build image' named `local-build-image-${DISTRO}` similar to
how `buildscripts/scripts/build-build-images.groovy` does it:
```
export NEXUS_USERNAME=frans.fuerst
export NEXUS_PASSWORD=...
(defines/dev-images/populate-build-context.sh build-context-dir \
&& DISTRO=ubuntu-22.04 BRANCH_VERSION=2.4.0 bash -c 'time \
  docker build \
    -t local-build-image-${DISTRO} \
    --build-context scripts=buildscripts/infrastructure/build-nodes/scripts \
    --build-context omd_distros=omd/distros \
    --build-context dev_images=defines/dev-images \
    --build-arg DISTRO="${DISTRO}" \
    --build-arg DISTRO_MK_FILE="$(echo ${DISTRO^^} | sed 's/-/_/g').mk" \
    --build-arg DISTRO_IMAGE_BASE=$(buildscripts/docker_image_aliases/resolve.py "IMAGE_$(echo ${DISTRO^^} | sed "s/[-\.]/_/g")") \
    --build-arg BRANCH_VERSION=${BRANCH_VERSION} \
    --build-arg VERS_TAG=vers__tag \
    --build-arg DOCKER_REGISTRY=artifacts.lan.tribe29.com:4000 \
    --build-arg NEXUS_ARCHIVES_URL=https://artifacts.lan.tribe29.com/repository/archives/ \
    --build-arg NEXUS_USERNAME="$NEXUS_USERNAME" \
    --build-arg NEXUS_PASSWORD="$NEXUS_PASSWORD" \
    --build-arg ARTIFACT_STORAGE=https://artifacts.lan.tribe29.com/ \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -f buildscripts/infrastructure/build-nodes/${DISTRO}/Dockerfile \
    build-context-dir \
')
```

Time/space needed:
```
real        7m9,887s
user        0m2,604s
sys         0m1,460s
Shared:         3.384GB
Private:        5.034GB
Reclaimable:    8.418GB
Total:          8.418GB
```


## Reference image (formerly called IMAGE_TESTING)

* Used for testing
* Used for building non distro-specifc stuff
* Made available locally via `defines/dev-images/reference-image-id`
* Which is wrapped by `scripts/run-in-docker.sh`

Time/space needed:
```
real        4m10,052s
user        0m0,864s
sys         0m0,462s
Shared:         5.874GB
Private:        5.034GB
Reclaimable:    10.91GB
Total:          10.91GB
```

## Left to do

* [ ] adapt this Readme
* [ ] check build image tag propagation
* [ ] check reference image for missing dependencies
* [ ] remove package list updates
* [ ] check: credentials needed for IMAGE_TESTING?
* [ ] remove unneeded packages
* [ ] provide tests for build/reference images
* [ ] make validate changes locally executable
* [ ] share pre-built reference image /
* [ ] activate docker build cache
    - https://stackoverflow.com/questions/77516243/reuse-docker-cache-from-another-machine
* [ ] move context relevant files to `defines`
* [ ] issue: `dpkg-sig` not available on 23:10+
* [ ] share logic with install-development script
* [x] remove references to IMAGE_TESTING
* [x] quieten docker build
* [x] split commits
* [x] use different build context

