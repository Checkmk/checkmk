# Checkmk - Your complete IT monitoring solution

Checkmk is available in several editions. The Checkmk Raw Edition is free and
100% open-source. The Checkmk Enterprise Edition includes several additional
features and professional support from the authors, billed annually. A demo
version is freely available for testing the Enterprise Edition in a
non-production environment.

Checkmk can be installed on Linux servers via DEB and RPM packages found on
our [downloads page](https://checkmk.com/download.php). The Enterprise
Edition is also available as a virtual or physical appliance. The following
short installation guides show how you can easily set up Checkmk and begin
monitoring.

Please visit our [website](https://checkmk.com/) for more
details.

## Getting started

Please have a look at the [official
handbook](https://checkmk.com/cms_introduction.html) on how to get
started with Checkmk.

## Building on your own packages

It is highly recommended to use the prebuilt Checkmk packages we
[provide](https://checkmk.com/download.php). But if you really want to
build your own packages, you either need to download the source packages from
our website or check out the [Git
repository](https://github.com/tribe29/checkmk).

To prepare your system for building, you need to execute this command:

    make -C omd setup

This will install the missing build dependencies, at least if you are working on
a supported Linux distribution. Then you can either create RPM or DEB packages,
depending on your distro.

To build an RPM:

    make rpm

To create a DEB package:

    DEBFULLNAME="Mr. Buildmaster" DEBEMAIL="mail@buildmaster.com" make deb

Don't forget to insert your name and mail address. As a result your should find
packages of the form `check-mk-[edition]-[version].[deb|rpm]` in your current
directory.
