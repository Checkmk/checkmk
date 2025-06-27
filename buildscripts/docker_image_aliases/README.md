# Provide git-trackable "Docker Image Aliases"

## Goals

* pull from corporate registry whenever possible
** no Docker:pull operation should use the global Docker hub by default
* allow reproducability of exact images for every branch
** instead of (volatile) global names for images (e.g. `busybox:latest`) their SHAs should be used
** a git tracable text file contains mapping from aliases to image SHAs
* avoid redundancy
** updating one alias should be done in exactly one file
* allow parallelization
** alias -> SHA mapping must not be part of global docker state
* allow work from outside of corporate network
** using the Docker hub should still be possible

see:
- Jira ticket: CMK-8148
- https://superuser.com/questions/1658083


## Usage

Perform these steps inside the testing container or use a small rescue venv for it.
The rescue venv trick is especially helpfull if the image to register or update is the testing image.

```bash
scripts/run-in-docker.sh bash
make .venv
# or way faster
python3 -m venv .venvRescure
. .venvRescure/bin/activate
pip install docker pyyaml
```

### Register a new docker image alias

Just switch to `buildscripts/docker_image_aliases` and run `register.py` providing the name of
the image alias (preferably uppper case and prefixed with "`IMAGE_`" for consistancy).

This step has to be performed for every branch, e.g. `master`, `2.4.0`, `2.3.0`

Remember to login to the registry once by
`docker login artifacts.lan.tribe29.com:4000 --username USER.NAME` to create the required
`~/.docker/config.json` file

```bash
./register.py IMAGE_CMK_BASE debian:buster-slim
./register.py IMAGE_UBUNTU_24_10 ubuntu:24.10
```

In case of a SUSE image you might need to pull it from the SUSE registry and use the following command

```bash
./register.py IMAGES_SLES_15SP5 registry.suse.com/suse/sle15:15.5
```

A directory named after the image alias containing a `Dockerfile` and `meta.yml` gets created.
`git add` and `commit` them in order to make your image alias official.

You can now output the unique ID of a locally stored image by running
`buildscripts/docker_image_aliases/resolve.py` providing the alias name:

```bash
buildscripts/docker_image_aliases/resolve.py IMAGE_CMK_BASE
# df0140a4030c
```

### Update aliases

In order to update a specific or all aliases to their respective upstreams, run `update.sh`:

```bash
./update.sh [all, IMAGE_CMK_BASE, IMAGE_TESTING, IMAGE_UBUNTU_20_04, ...]
```

This script basically validates your input and updates all provided aliases by removing and
re-registering them (which can also be done manually).

After locally updating an image you have to commit/push changes to the respective `Dockerfile`.
In case there are no changes to any `Dockerfile` there had been no new image defined by upstream,
resulting in the exact same image ID.

### Use the image alias in Dockerfiles and scripts

Dockerfiles which shall be based on an image alias have to reference it using a build argument:

```
ARG IMAGE_CMK_BASE
# hadolint ignore=DL3006
FROM ${IMAGE_CMK_BASE} AS base
```

Note that you can choose a different name for the argument, but for consistancy please use the
same name as for the alias. This way it's easy to get the context.

There is an example Docker image contained in `buildscripts/docker_image_aliases/example`. To build
it manually just run `docker build` as usual and provide the variable containing the actual image id
via `--build-arg`:

```bash
docker build \
    --pull \
    --build-arg "IMAGE_CMK_BASE=$(./resolve.sh IMAGE_CMK_BASE)" \
    -t debian_example example
```

Whereever you `run` (or somehow reference) an image you would have referenced directly you now run
`resolve.sh` to get the image behind the alias. E.g. in scripts/Makefiles instead of writing

```bash
docker run --rm -i hadolint/hadolint < Dockerfile
```

you can now run s.th. like

```bash
docker run --rm -i $$(<PATH_TO>/resolve.sh IMAGE_HADOLINT) < Dockerfile
```

You can also use the Dockerfiles contained in the alias directories directly if possible. E.g. in
Jenkins/Groovy scripts you write

```
docker.build("<NAME>", "--pull <PATH-TO-ALIAS>").inside(<ARGS>) {
    <CODE>
}
```

Which is equivalent to

```
def IMAGE_ID = sh("<PATH_TO>/resolve.sh IMAGE_HADOLINT");
docker.image(IMAGE_ID).inside(<ARGS>) {
    <CODE>
}
```
