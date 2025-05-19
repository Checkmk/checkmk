# Checkmk - Your complete IT monitoring solution

![PR-CI status](https://github.com/Checkmk/checkmk/actions/workflows/pr.yaml/badge.svg)

**Checkmk** is a comprehensive IT monitoring system designed for scalability, flexibility, and low resource consumption. It supports infrastructure and application monitoring across physical, virtual, containerized, and cloud environments.

Checkmk is available in several editions, each suited to different operational needs. Please visit our [website](https://checkmk.com/) for more details, documentation, new releases, discussion forums, and more.

### Checkmk Raw

Checkmk Raw is completely free and open-source (licensed under the GNU GPL v2). It includes the core Checkmk monitoring engine, a web-based UI, agent-based and agentless monitoring, and support for hundreds of official and community-maintained plugins.

This edition is ideal for smaller environments with basic requirements in terms of automation, dashboarding, and support. Download it in various formats [here](https://checkmk.com/download).

### Checkmk Enterprise

A commercial edition that extends Checkmk Raw with advanced features for performance, automation, and usability. These include distributed monitoring, built-in dashboards, automated agent management, support for enterprise integrations (e.g. LDAP, REST APIs), and more. Professional support is included. A demo version can be freely [downloaded](https://checkmk.com/free-trial) for evaluation purposes.

### Checkmk Cloud (self-hosted)

Tailored for modern cloud-native infrastructures, Checkmk Cloud includes all Enterprise features, plus enhanced capabilities for monitoring dynamic, ephemeral environments such as Kubernetes, AWS, Azure, and GCP. It supports application metrics collection via OpenTelemetry, and features push agents and auto-registration of hosts. Download the [free trial](https://checkmk.com/free-trial).

### Checkmk Cloud

For teams that prefer not to deploy Checkmk themselves, [Checkmk Cloud](https://checkmk.com/product/checkmk-cloud-saas) is the SaaS version of Checkmk. It features automatic updates, backups, and easy onboarding, with no infrastructure overhead for the end user. Try it for free [here](https://admin.checkmk.cloud/).

### Checkmk MSP

Designed for managed service providers, Checkmk MSP builds on the Checkmk Cloud (self-hosted) feature set and adds multitenancy support, centralized monitoring across multiple customer environments, isolated access controls, and MSP-specific reporting. A [free trial](https://checkmk.com/msp-trial) is available or you can directly [request a quote](https://checkmk.com/request-quote/msp).


## Installation

Checkmk can be installed on Linux via DEB and RPM packages. We support RedHat (and derived distributions like CentOS, AlmaLinux, Rocky Linux, Oracle Linux and more), Ubuntu, and SUSE Linux Enterprise Server with official packages. Generally LTS/stable versions of these distributions are supported. Direct instructions on the installation of Checkmk can be found on these distribution-specific documentation pages:

- [RedHat](https://docs.checkmk.com/latest/en/install_packages_redhat.html)
- [SUSE Linux Enterprise Server](https://docs.checkmk.com/latest/en/install_packages_sles.html)
- [Debian and Ubuntu](https://docs.checkmk.com/latest/en/install_packages_debian.html)

All Checkmk editions can be also installed as Docker containers. Full instructions [here](https://docs.checkmk.com/latest/en/introduction_docker.html).

Checkmk Enterprise, Cloud (self-hosted) and MSP are also available as virtual or physical appliances. All packages, images, and containers can be found on our [downloads page](https://checkmk.com/download.php).

## Getting started

Please have a look at the [beginners guide](https://docs.checkmk.com/master/en/intro.html) on how to get started with Checkmk.

## Want to contribute?

Nice! Before contributing please check out our [contribution guidelines](CONTRIBUTING.md).

## Building your own packages

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
