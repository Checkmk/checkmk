==================================
Agent controller (`cmk-agent-ctl`)
==================================


Introduction and goals
======================

The agent controller is responsible for the transport of the monitoring data to the site.
This includes

 * establishing a trusted (encrypted) connection as client *or* server
 * compressing the data
 * optionally the scheduling

It was originally written to allow the monitored host to initiate the connection to the site in cases where the site can not poll the data from the host.

However, it supports both modes:
 * In the *pull mode* the monitoring sites pulls the data, the agent controller acts as server (TLS or plain TCP)
 * In the *push mode* the controller sends data to the site, the agent controller acts as a HTTPS client to the :doc:`arch-comp-agent-receiver`.

Requirements overview
---------------------

The controller should be compatible with as many operating systems as possible.
Since it is a component that talks TCP, it could be a potential attack vector. For this reason, it is run as a dedicated user with little privileges.

Architecture
============

White-box overall system
------------------------

.. uml:: arch-comp-agent-controller.puml

Interfaces
----------

The agent controller manages and uses a list of data sets to establish trusted connections to one or more monitoring sites.

Usually the `cmk-agent-ctl` uses this information to create TLS connections using server and client certificates.

If no Checkmk server is known at all and the controller is explicitly configured to do so, it dumps the agent output unencrypted on the open TCP connection.
This is also the initial configuration, to get started easily.

To distinguish between TLS and non TLS connections the first byte is read by the fetcher (first byte marker).
The controller will advertise its readiness to establish a TLS connections by sending b"16".

When talking to the agent-receiver HTTPS is used.

Runtime view
============
On older setups `systemd` or `xinetd` executes the `check-mk-agent` command if somebody connects to the defined port.

With the new setup the `check-mk-agent` is executed by `systemd` as soon as the `cmk-agent-ctl` connects to a Unix socket.

Deployment view
===============
The agent is usually installed as a package.

If the agent updater is used the agent updater polls the server regularly to check if a new version is available.
If so it downloads the agent and a `systemd` timer regularly checks for new agents to install.

Risks and technical debts
=========================
(yet to be implemented)