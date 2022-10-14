====================
Push agent
====================


Introduction and goals
======================
The agent monitors the host its running on and possibly other services with plugins.

We support a variety of operating systems.
Including Windows, Debian, RHEL.

On modern systems the *new* agent system with the `cmk-agent-ctl` is used.
On older systems only the `check-mk-agent` bash script with `systemd`/`xinetd` is used. (See :doc:`arch-comp-agent-linux`)

Architecture
============

White-box overall system
------------------------

The *new* Agent consists of several parts:

1. The new `cmk-agent-ctl`
2. The `check-mk-agent`
3. Agent plugins

.. uml::

    package "Agent" {
        () TLS as agent_tls
        component "[[../arch-comp-agent-linux.html check-mk-agent]]" as check_mk_agent
        [cmk-agent-ctl] as cmk_agent_ctl
        cmk_agent_ctl - agent_tls

        [check-mk-agent-async] as check_mk_agent_async
        () FS as filesystem
        check_mk_agent - filesystem
        check_mk_agent_async - filesystem

        () "Unix Socket" as unix_socket
        check_mk_agent - unix_socket
        cmk_agent_ctl ..> unix_socket: reads

        [cmk-update-agent] as cmk_update_agent
        check_mk_agent ..> cmk_update_agent: executes
    }

    () HTTPS as https
    component "[[../arch-comp-agent-receiver.html agent-receiver]]" as agent_receiver
    https - agent_receiver
    cmk_agent_ctl ..> https: register, push

    [fetcher] as fetcher
    fetcher ..> agent_tls: pull

    () HTTP as http_gui
    component "[[ ../arch-comp-gui.html GUI]]" as gui
    http_gui -- gui
    cmk_update_agent ..> http_gui

Interfaces
----------

`cmk-agent-ctl`
---------------
The agent controller manages and uses a list of data sets to establish trusted connections to one or more monitoring sites.

Usually the `cmk-agent-ctl` uses this information to create TLS connections using server and client certificates.

If no Checkmk server is known at all and the controller is explicitly configured to do so, it dumps the agent output unencrypted on the open TCP connection.
This is also the initial configuration, to get started easily.

To distinguish between TLS and non TLS connections the first byte is read (first byte marker).
The controller will advertise its readiness to establish a TLS connections by sending b"16".

When talking to the agent-receiver HTTPS is used.

`cmk-updater-agent`
-------------------
The agent updater is usually invoked by the agent as a plugin.
It contacts the Checkmk server with host specific credentials and checks if a new version of the agent is available.
If so it downloads the agent, checks the signature (which is attached to the response) and writes the new agent to disk.
Via a `systemd` timer the `cmk-updater-agent` is called (every minute) in order to install available agents.

Runtime view
============
On older setups `systemd` or `xinetd` executes the `check-mk-agent` command if somebody connects to the defined port.

With the new setup the `check-mk-agent` is executed as soon as the `cmk-agent-ctl` connects to a Unix socket.

Deployment view
===============
The agent is usually installed as a package.

If the agent updater is used the agent updater polls the server regularly to check if a new version is available.
If so it downloads the agent and a `systemd` timer regularly checks for new agents to install.

Risks and technical debts
=========================
- See :doc:`arch-comp-agent-linux` for `check-mk-agent` specific risks and debts
- `cmk-update-agent`: If the site is not using HTTPS the `host_secret` can get lost.
