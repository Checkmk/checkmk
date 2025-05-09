# OMD - Packaging Checkmk

OMD consists of various components. These are called packages. You can
understand OMD packages as a form of distribution that bundles different
software components into a functional bundle that then implements our monitoring
environment. Checkmk is just as much a part as NagVis or the patch command.

## Creating packages

The packages can be built on all Linux distributions that we are supporting.
For each of the supported Linux distributions the following is needed:

- A file below `distros/*.mk` specifying the distro specific settings
- A distro detection logic in the `distro` script

If you use one of these distributions, you need to prepare your system for
building the Checkmk packages. A good start is to run `make setup` in the
Checkmk git base directory.

After this is done, you may use, depending on your distribution, one of the
following targets to build a package for the current git:

- `make rpm`: Create a RPM package for RedHat/SLES. Each build starts
  building th
- `make deb`: Create a DEB package for Debian/Ubuntu
- `make cma`: Create a CMA package for the appliance

## Dealing with Windows artifacts

Checkmk ships with several parts that are compiled on Windows build systems,
these are

- a) the Windows agent
- b) the optional python interpreter for plugins.

When these files are not existing previous to the packaging of Checkmk,
the build will fail.

For the moment there is an internal helper script
`scripts/fake-artifacts` that creates empty stub files at the required
locations to prevent the packaging issues. Obviously the Windows agent and
related features in your built package will not be usable when building with
these faked artifacts.

TODO: Shouldn't we put them into dedicated packages which can then easily be
excluded when there is no need to pack them (e.g. for tests)?

## Using bazel remote cache

In case you want to use the (internal) bazel remote cache, add a `remote.bazelrc`
to the repository root (see `.bazelrc` for more information)

## How to build locally?

Clone from the Checkmk Git, then execute the following commands:

```bash
# Run everything in our pre-built docker images.
# This may take a while as it's pulling the image from the registry
scripts/run-in-docker.sh bash

# Fake the windows artifacts - they need to be built on a windows node
scripts/fake-artifacts

# And now build a debian package
make deb
```

It will use the OMD package build cache to create a `.deb` file in the `omd`
directory.

## How to build a single OMD package?

The OMD packages are built in the following phases in general:

  1. unpacking
  2. building
  3. intermediate install
    - optionally processing build cache
  4. installing to final directory

### `{PKG}_UNPACK` - Unpack the source archive

The source archive is unpacked into the `{PKG}_BUILD_DIR`. A default target is
implemented for most of the packages. Only source archives which need special
handling (e.g. because the archive name is not equal to the OMD package name)
have a custom `{PKG}_UNPACK` target.

### `{PKG}_BUILD` - Build the package

For most packages this contains the normal `./configure && make` logic. The
build is executed in `{PKG}_BUILD_DIR` (which is
`omd/build/package_build/{PKG}-{VERS}`).

### `{PKG}_INTERMEDIATE_INSTALL` - Intermediate install

Installs the files previously built to a `{PKG}` individual target directory
`{PKG}_INSTALL_DIR` (which is `omd/build/intermediate_install/{PKG}-{VERS}`).

### `{PKG}_CACHE_PKG_PROCESS` - Optional processing of the build cache

Some packages support a cached build. The files from `{PKG}_INSTALL_DIR` will be
archived and uploaded to our nexus and then used again by other build processes.
In case the nexus is available, and it has a build cache archive, this is
downloaded and unpacked to `{PKG}_INTERMEDIATE_INSTALL` instead of performing
the previous steps.

See also *Using package cache* on how to use it.

### `{PKG}_INSTALL` - Install package files to final target directory

Install all the files of `{PKG}` from the intermediate install directory to the
final target directory which is then used as base for the Checkmk RPM or DEB
packages.

All the phases mentioned above are represented by stamp files which are stored
in `omd/build/stamps`.

### Incrementally work on a specific package

#### Simple packages

Simplest and fastest package build is `nrpe`, just execute the following
commands inside the build container

```sh
cd omd

bazel build @nrpe//:nrpe
# or
make nrpe-build

# there are no stamps available for this package at $PWD/build/stamps

# install the package
make nrpe-install
# target location is check_mk/omd/build/dest/omd/versions/<VERSION>
```

#### Complex packages

A complex package with almost all possible dependencies to other packages like
`perl`, `python3-modules`, `python` and `openSSL` is `net-snmp`. You can do it
like follows to build it.

```sh
# If you're starting from a clean repo, make sure that all needed dependencies are built.
# e.g. when you want to build the package "net-snmp":
cd omd

make PACKAGES="net-snmp" install

# Now the stamps should be in-place - verify it with:
ls build/stamps/net-snmp*

# If you want to change now something,
# - do your changes
# - remove the stamp file and trigger the rebuild:
rm $PWD/build/stamps/net-snmp*build
make $PWD/build/stamps/net-snmp*build
```

## Incremental package building

TODO: See `omd/Makefile` and `omd/debian/rules`. Should be configurable by
environment variables in the future.

## Measuring build times

To improve build times it is first important to understand which parts of the
build take how much time.

During packaging there are entries written to stdout of the build job. They look
like this:

```sh
+++ [1638200385] Build step '/home/lm/git/checkmk/omd/build/stamps/openssl-1.1.1l-install': done
```

You could grep them from the log to get an idea which package takes how long to
be built. These lines are also written to `omd/omd_build_times.log`.

The log contains absolute time stamps. You may use the helper script
`omd/show_build_times` to get the duration of each step calculated.

An other option would be to use `remake` like this:

```sh
cd omd
MAKE="remake --profile" make deb
```

It will call `remake` in profiling mode, instead of bare `make`, for package
building which creates `callgrind.out.*` files that then can be opened with
`kcachegrind callgrind.out.*`.

## Makefile organization

Each package has a dedicated Makefile below omd/packages/[name]/[name].make.
These files are all included in the omd/Makefile. The inclusion makes it
possible to define dependencies between the targets of the different packages.

All targets and variables in the packages need to be prefixed with the package
name variables to avoid name clashes.

## Add/remove new package to distribution

Summary: you must modify `omd/Makefile`, `omd/packages/packages.make` and
create `[name].make` which build/deploy your binary or library.

Step by step:

1. Modify `PACKAGES` variable in `omd/Makefile` adding a line with `[name]` of
a package to be added.
2. Create a corresponding directory with name of the package in the
`omd/packages` subdir, i.e. `omd/packages/[name]`.
3. Create in the directory from p.2 the file having name of the package and
extension make, i.e. `omd/packages/[name]/[name].make`
4. Add `omd/packages/[name]/[name].make` to the rule include in the file
`omd/packages/package.make`

In the simple cases you should use `livestatus.make` or `unixcat.make` as a template.

To remove package just remove the line in `omd/Makefile`, the line in
`omd/packages/package.make` and directory in the `omd/packages`.
