============
Agent bakery
============

Introduction and goals
======================
* Allow easy deployment of agents with customization (mainly plugins)

Architecture
============

Monitored Host
------------------------

See :doc:`arch-comp-agent-updater`

Interfaces
----------
* Setup: For configuring
* Setup: `noauth:deploy_agent` for the agent updater to retrieve agents or info
  about new agents


Risks and technical debts
=========================

Agent package is transferred over HTTP (MITM)
---------------------------------------------
The agent package possibly contains configuration file which might include
sensitive data e.g. local database passwords.
When transmitted over HTTP a MITM attacker could retrieve them.

**Possible mitigation:**

This endpoint should be moved to the agent receiver.
We have the host_secret as authentication for the agent-updater.
TLS for the agent controller, we should unify that and favor TLS.

Unclear if rules have changed when "bake & sign" is pressed
-----------------------------------------------------------
When a new bake is necessary it is not clear what actually has changed.
A rouge admin could add new custom files or plugins and another admin bakes and
signs them unconsciously.

**Possible mitigation:**

* Show a diff of agent configuration
* package content preview
* highlight files that are not CMK builtin, i.e. local structure or MKPs

Compromised plugin (MKP) or attacker on server
----------------------------------------------
An attacker on the Checkmk server could manipulate viewing mitigation and bake
arbitrary files into a agent package.
As soon as the signing took place the malicious files can then be installed by
agents.

**Possible mitigation:**

* log warnings/info if local files are loaded that override builtin functionality.
* sign packages on Package Exchange to validate MKP contents

Downloaded package is manipulated
---------------------------------
The package the agent-updater downloads is briefly stored on disk and then
installed after that.
During that time it could be manipulated.

This is mitigated via the signature.
On Unix the installer checks the signatures again.
On Windows the updater runs as SYSTEM and the path is only writable by SYSTEM.
