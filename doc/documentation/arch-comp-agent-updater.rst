==================================
Agent updater (`cmk-update-agent`)
==================================


Introduction and goals
======================

The agent updater

 * regularly checks a configured Checkmk site for new agent packages to download and install
 * monitor the deployment state of the agent package, i.e. its own operational state

It is currently available as compiled python executable.

Architecture
============

White-box overall system
------------------------

The current architecture consists of two calls to the agent updater.
Once as an agent plugin (triggered by the agent (:doc:`arch-comp-agent-linux`) creating the monitoring data and potentially downloading a new package.
A second call, triggered by a `systemd` timer to install the downloaded package. 

.. uml:: arch-comp-agent-updater.puml

Interfaces
----------

The agent updater is usually invoked by the agent as a plugin.
It contacts the Checkmk server with host specific credentials and checks if a new version of the agent is available.
If so it downloads the agent, checks the signature (which is attached to the response) and writes the new agent to disk.
Via a `systemd` timer the `cmk-updater-agent` is called (every minute) in order to install available agents.

Runtime view
============

The agent updater polls the server regularly to check if a new version is available.
If so it downloads the agent and a `systemd` timer regularly checks for new agents to install.

Deployment view
===============
The updater is usually part of the agent package.

Risks and technical debts
=========================
- The whole architecture currently is a result of a succession of small changes to adapt to the circumstances imposed by `systemd`. It could be streamlined massively!
- Securing the connection relies on the user. If the system apache is not configured to enforce HTTPS, transferred data like the `host_secret` can be leaked.
