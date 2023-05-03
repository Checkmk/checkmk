# Checkmk - Your complete IT monitoring solution

![PR-CI status](https://github.com/Checkmk/checkmk/actions/workflows/pr.yaml/badge.svg)

Checkmk is available in several editions.
The Checkmk Raw Edition is free and 100% open-source.
The Checkmk Enterprise Edition includes several additional features and professional support from the authors, billed annually.
A demo version is freely available for testing the Enterprise Edition.

Checkmk can be installed on Linux servers via DEB and RPM packages found on our [downloads page](https://checkmk.com/download.php).
The Enterprise Edition is also available as a virtual or physical appliance.
The following short installation guides show how you can easily set up Checkmk and begin monitoring.

Please visit our [website](https://checkmk.com/) for more details.

## Getting started

Please have a look at the [beginners guide](https://docs.checkmk.com/master/en/intro.html) on how to get started with Checkmk.

## Want to contribute?

Nice! Before contributing please check out our [contribution guidelines](CONTRIBUTING.md).

## Building on your own packages

It is highly recommended to use the prebuilt Checkmk packages we [provide](https://checkmk.com/download.php).
But if you really want to build your own packages, you either need to download the source packages from our website or check out the [Git repository](https://github.com/Checkmk/checkmk).

We're building the Checkmk packages within specific docker images for the different distros.
Please find the Dockerfiles under buildscripts/infrastructure/build-nodes/ in order to get an idea what's needed to build it locally.
However, keep in mind that those Dockerfiles are heavily relying on our infrastructure and won't build from scratch on your machine.

If you have the dependencies in place, you can either create RPM or DEB packages, depending on your Linux distribution.

To build an RPM:

    make rpm

To create a DEB package:

    DEBFULLNAME="Mr. Buildmaster" DEBEMAIL="mail@buildmaster.com" make deb

Don't forget to insert your name and mail address.
As a result you should find packages of the form `check-mk-[edition]-[version].[deb|rpm]` in your current directory.
