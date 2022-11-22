====================
Agents
====================

An agent is a software package deployed on the monitored host.

Introduction and goals
======================

The agents objective is to make information about the state of the monitored host available to the monitoring site.
The agent monitors the host it is running on and possibly other services with plugins.

We support various operating systems, the most important are Windows and Linux based systems (like Debian and RHEL).
Not all setups and configurations are available for all systems.

On modern systems the *new* agent system with the agent controller `cmk-agent-ctl` is used (see :doc:`arch-comp-agent-controller`).
On older systems only the `check-mk-agent` bash script with `systemd`/`xinetd` is used (see :doc:`arch-comp-agent-linux`).


Requirements overview
---------------------
It should not consume too much resources on the monitored system, and after installation not modify it.
All involved programs and tools should make as few assumptions about the hosts system as possible.


Architecture
============

White-box overall system
------------------------

An agent package can consist of these parts:

1. :doc:`arch-comp-agent-controller`
2. :doc:`arch-comp-agent-linux` / Windows agent
3. Agent plugins
4. :doc:`arch-comp-agent-updater`

This is how things look under Linux:

.. uml:: arch-comp-agent-abstract-linux.puml


Interfaces
----------

The transport of the monitoring data is either handled by the :doc:`arch-comp-agent-controller` (`cmk-agent-ctl`) or, on older systems by `systemd` or even `xinetd`.
Users can also implement their own means of transportation (such as SSH).

The :doc:`arch-comp-agent-updater` is usually invoked by the agent as a plugin and by a `systemd` timer and contacts the monitoring site.
