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

Checkmk ships with serveral parts that are compiled on Windows build systems,
these are a) the Windows agent, the windows agent updater and some compiled
windows agent plugins. When these files are not existing previous to the
packaging of Checkmk, the build will fail.

For the moment there is an internal helper script
`zeug_cmk/bin/fake-windows-artifacts` that simply creates empty files at the
required locations to prevent the packaging issues.

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

## Incremental package building

TODO: See omd/Makefile and omd/debian/rules. Should be configurable by
environment variables in the future.

## Makefile organization

Each package has a dedicated Makefile below omd/packages/[name]/[name].make.
These files are all included in the omd/Makefile. The inclusion makes it
possible to define dependencies between the targets of the different packages.

All targets and variables in the packages need to be prefixed with the package
name variables to avoid name clashes.
