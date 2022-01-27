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

- `make rpm`: Create a RPM package for RedHat/CentOS/SLES. Each build starts
  building th
- `make deb`: Create a DEB package for Debian/Ubuntu
- `make cma`: Create a CMA package for the appliance

## Dealing with Windows artifacts

Checkmk ships with several parts that are compiled on Windows build systems,
these are a) the Windows agent and b) the optional python interpreter for
plugins. When these files are not existing previous to the packaging of Checkmk,
the build will fail.

For the moment there is an internal helper script
`scripts/fake-windows-artifacts` that creates empty stub files at the required
locations to prevent the packaging issues. Obviously the Windows agent and
related features in your built package will not be usable when building with
these faked artifacts.

TODO: Shouldn't we put them into dedicated packages which can then easily be
excluded when there is no need to pack them (e.g. for tests)?

## Using package cache

Some of the OMD packages support some kind of build cache which helps to reduce
the overall build times. To make use of this mechanism, you will have to set the
following environment variables before executing the package build targets:

- `NEXUS_BUILD_CACHE_URL=https://[NEXUS_URL]/repository/omd-build-cache`
- `NEXUS_USERNAME=nexus-user`
- `NEXUS_PASSWORD=nexus-password`

Once this is configured correctly the first build will produce build artifacts
and upload them to the nexus server. On the next run, either the locally or
remotely cached build artifacts are used.

The build cache is saved per branch based on the `BRANCH_VERSION` definition in
`defines.make`. It needs to be updated when a new stable branch is forked from
the master branch.

## How to build locally?

Clone from the Checkmk Git, then execute the following commands:

```bash
cd omd
make setup
../scripts/fake-windows-artifacts
NEXUS_BUILD_CACHE_URL=https://artifacts.lan.tribe29.com/repository/omd-build-cache \
NEXUS_USERNAME=nexus-user \
NEXUS_PASSWORD=nexus-pw \
make deb
```

It will use the OMD package build cache to create a `.deb` file in the `omd`
directory.

## How to build one OMD package?

The OMD packages are built in the following phases in general:

- `{PKG}_UNPACK` - Unpack the source archive

The source archive is unpacked into the `{PKG}_BUILD_DIR`. A default target is
implemented for most of the packages. Only source archives which need special
handling (e.g. because the archive name is not equal to the OMD package name)
have a custom `{PKG}_UNPACK` target.

- `{PKG}_BUILD` - Build the package

For most packages this contains the normal `./configure && make` logic. The
build is executed in `{PKG}_BUILD_DIR` (which is
`omd/build/package_build/{PKG}-{VERS}`).

- `{PKG}_INTERMEDIATE_INSTALL` - Intermediate install

Installs the files previously built to a `{PKG}` individual target directory
`{PKG}_INSTALL_DIR` (which is `omd/build/intermediate_install/{PKG}-{VERS}`).

- `{PKG}_CACHE_PKG_PROCESS` - Optional processing of the build cache

Some packages support a cached build. The files from `{PKG}_INSTALL_DIR` will be
archived and uploaded to our nexus and then used again by other build processes.
In case the nexus is available and it has a build cache archive, this is
downloaded and unpacked to `{PKG}_INTERMEDIATE_INSTALL` instead of performing
the previous steps.

See also *Using package cache* on how to use it.

- `{PKG}_INSTALL` - Install packe files to final target directory

Install all the files of `{PKG}` from the intermediate install directory to the
final target directory which is then used as base for the Checkmk RPM or DEB
packages.

All the phases mentioned above are represented by stamp files which are stored
in `omd/build/stamps`.

To execute a build step of your choice, you can do it like follows. In this
example we either build the protobuf OMD package or receive previously built
parts from the build cache.

```
cd omd
make $PWD/build/stamps/protobuf-3.18.1-cache-pkg-process
```

## Incremental package building

TODO: See omd/Makefile and omd/debian/rules. Should be configurable by
environment variables in the future.

## Measuring build times

To improve build times it is first important to understand which parts of the
build take how much time.

During packaging there are entries written to stdout of the build job. They look
like this:

```
+++ [1638200385] Build step '/home/lm/git/checkmk/omd/build/stamps/openssl-1.1.1l-install': done
```

You could grep them from the log to get an idea which package takes how long to
be built. These lines are also written to `omd/omd_build_times.log`.

The log contains absolute time stamps. You may use the helper script
`omd/show_build_times` to get the duration of each step calculated.

An other option would be to use `remake` like this:

```
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
