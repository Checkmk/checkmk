# Checkmk - Your complete IT monitoring solution

![PR-CI status](https://github.com/Checkmk/checkmk/actions/workflows/pr.yaml/badge.svg)

**Checkmk** is a comprehensive IT monitoring system designed for scalability, flexibility, and low resource consumption. It supports infrastructure and application monitoring across physical, virtual, containerized, and cloud environments.

Checkmk is available in several editions, each suited to different operational needs. Please visit our [website](https://checkmk.com/) for more details, documentation, new releases, discussion forums, and more.

### Checkmk Community

Checkmk Community is completely free and open-source (licensed under the GNU GPL v2). It includes the core Checkmk monitoring engine, a web-based UI, agent-based and agentless monitoring, and support for hundreds of official and community-maintained plugins.

This edition is ideal for smaller environments with basic requirements in terms of automation, dashboarding, and support. Download it in various formats [here](https://checkmk.com/download).

### Checkmk Pro

A commercial edition that extends Checkmk Community with advanced features for performance, automation, and usability. These include distributed monitoring, built-in dashboards, automated agent management, support for enterprise integrations (e.g. LDAP, REST APIs), and more. Professional support is included. A demo version can be freely [downloaded](https://checkmk.com/free-trial) for evaluation purposes.

### Checkmk Ultimate

Tailored for modern cloud-native infrastructures, Checkmk Ultimate includes all Pro features, plus enhanced capabilities for monitoring dynamic, ephemeral environments such as Kubernetes, AWS, Azure, and GCP. It supports application metrics collection via OpenTelemetry, and features push agents and auto-registration of hosts. Download the [free trial](https://checkmk.com/free-trial).

### Checkmk Cloud

For teams that prefer not to deploy Checkmk themselves, [Checkmk Cloud](https://checkmk.com/product/checkmk-cloud-saas) is the SaaS version of Checkmk. It features automatic updates, backups, and easy onboarding, with no infrastructure overhead for the end user. Try it for free [here](https://admin.checkmk.cloud/).

### Checkmk Ultimate with Multi-Tenancy

Designed for managed service providers, Checkmk Ultimate with Multi-Tenancy builds on the Checkmk Ultimate feature set and adds multitenancy support, centralized monitoring across multiple customer environments, isolated access controls, and MSP-specific reporting. A [free trial](https://checkmk.com/msp-trial) is available or you can directly [request a quote](https://checkmk.com/request-quote/msp).

## Installation

Checkmk can be installed on Linux via DEB and RPM packages. We support RedHat (and derived distributions like CentOS, AlmaLinux, Rocky Linux, Oracle Linux and more), Ubuntu, and SUSE Linux Enterprise Server with official packages. Generally LTS/stable versions of these distributions are supported. Direct instructions on the installation of Checkmk can be found on these distribution-specific documentation pages:

- [RedHat](https://docs.checkmk.com/latest/en/install_packages_redhat.html)
- [SUSE Linux Enterprise Server](https://docs.checkmk.com/latest/en/install_packages_sles.html)
- [Debian and Ubuntu](https://docs.checkmk.com/latest/en/install_packages_debian.html)

All Checkmk editions can be also installed as Docker containers. Full instructions [here](https://docs.checkmk.com/latest/en/introduction_docker.html).

Checkmk Pro, Ultimate and Ultimate with Multi-Tenancy are also available as virtual or physical appliances. All packages, images, and containers can be found on our [downloads page](https://checkmk.com/download.php).

## Getting started

Please have a look at the [beginners guide](https://docs.checkmk.com/latest/en/intro_welcome.html) on how to get started with Checkmk.

## Want to contribute?

Nice! Before contributing please check out our [contribution guidelines](CONTRIBUTING.md).

## Building your own packages

It is highly recommended to use the prebuilt Checkmk packages we [provide](https://checkmk.com/download.php).
But if you really want to build your own packages, follow the instructions here.

We're building the Checkmk packages within specific docker images for the different distros as the builds are not (yet) fully hermetic.
Please find the Dockerfiles under buildscripts/infrastructure/build-nodes/ in order to get an idea what's needed to build it locally.
However, keep in mind that those Dockerfiles are heavily relying on our infrastructure and won't build from scratch on your machine.

If you have the dependencies in place, you can build RPM or DEB packages with [Bazel](BAZEL.md).

To create a DEB package:

    bazel build --cmk_edition=community --cmk_version=3.0.0 \
        --//:disable_agent_package_signing=true //omd:deb

To build an RPM:

    bazel build --cmk_edition=community --cmk_version=3.0.0 \
        --//:disable_agent_package_signing=true //omd:rpm

The build settings select what is packaged:

- `--cmk_edition`: use `community` to build the open source version of checkmk
- `--cmk_version`: the version string used in the package name and the installation path `/opt/omd/versions/<version>.<edition>`

The packages bundle the `check-mk-agent` RPM, which is signed with our release key.
Without a signing key, the package targets refuse to build, so that no unsigned agent package is shipped by accident.
`--//:disable_agent_package_signing=true` bundles the unsigned agent RPM instead.

Some artifacts cannot yet be built on linux-only and are provided by our CI from dedicated build nodes.
Add `--//:use_faked_artifacts=true` to replace them with placeholders.
Faked artifacts imply unsigned agent packages, so `--//:disable_agent_package_signing=true` isn't needed then.
Packages built this way are fine for testing but must not be used in production.

As a result you should find packages of the form `check-mk-[edition]-[version]*.[deb|rpm]` in `bazel-bin/omd/`.
