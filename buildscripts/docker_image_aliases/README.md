# Provide per-commit "Docker Image Aliases" 

## Goals

* pull from corporate registry whenever possible
** no Docker:pull operation should use the global Docker hub by default
* allow reproducability of exact images for every branch
** instead of (volatile) global names for images (e.g. `busybox:latest`) their shas should be used
** a git tracable text file contains mapping from aliases to image shas
* avoid redundancy
** updating one alias should be done in exactly one file
* allow parallelization
** alias -> sha mapping must not be part of global docker state
* allow work from outside of corporate network
** using the Docker hub should still be possible

see:
- Jira ticket: CMK-8148
- https://superuser.com/questions/1658083


## Usage

        # to register a new image ()
        register.py IMAGE_CMK_BASE debian:buster-slim

        # -> git add/commit/push `IMAGE_CMK_BASE/`

        # to use `IMAGE_CMK_BASE` with Dockerfile example
        docker build \
            --build-arg "IMAGE_CMK_BASE=$(./resolve.sh IMAGE_CMK_BASE)" \
            -t debian_example example

        # to update all or specified aliases to their respective upstreams
        update.py [IMAGE_CMK_BASE ..]


## Todo

* write uses cases and examples
* validate `docker_image_aliases.txt` (missing/multiple entries)
* implement `update`
