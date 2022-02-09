===========================
Checkmk's Build-chain (WIP)
===========================


Introduction and goals
======================
This documentation describes the build process of OMD & Checkmk.
It help users of Checkmk to understand how the software is built code integrity is ensured.

Requirements overview
---------------------
1. Reproducibility

The architecture of the build-chain aims for generating reproducible builds.
Reproducible builds can act as part of a chain of trust.
The source code can be signed, and deterministic compilation can prove that the binary was compiled from trusted source code.

However at the moment we do not comply with 100% reproducible build definition.
Nevertheless it is our goal and we strive to achieve it.

2. Create packages for supported target systems

This involves providing source package that was used for the build.
As well as packages and docker images for all currently supported platforms.

RHEL 7
Debian 9
Debian 11
SLES 12 SP4
SLES 12 SP5
SLES 15
SLES 15 SP1
SLES 15 SP2
SLES 15 SP3
Ubuntu 16.04 (LTS)
Ubuntu 18.04 (LTS)
Ubuntu 20.04 (LTS)
Ubuntu 21.10


3. Builds availability locally and in CI

CI builds are executed daily for all supported platforms.
The builds can be executed locally by the developer provided he uses one of the supported Linux distributions.
External users can build a Raw Edition package locally.

Architecture
============

White-box overall system
------------------------
Add here an UML diagram, which shows the internals of your component,
including external and internal interfaces.

Interfaces
----------
Describe the exposed interfaces of your components. How is your component
communicating with the rest of the system.

Infrastructure
--------------

Hardware infrastructure is managed by Infra team.
In particular Jenkins main and agent nodes are installed using some ansible playbooks.
The same team also manages our package, container and artifacts storage.


Runtime view
=======================
The following sequence diagram describes the steps from Checkmk's source code
to the corresponding distribution packets.

It shows the interaction between internal build, git, artifacts servers and
external sources. All external participants are marked red.

.. uml:: build-sequence.puml

Deployment view
===============
The deployment view describes:

* the technical infrastructure used to execute your system, with infrastructure
  elements like computers, processors as well as other infrastructure elements
  and
* the mapping of (software) building blocks to that infrastructure elements.

Risks and technical debts (optional)
====================================
A list of identified technical risks or technical debts, ordered by priority
