===========
Linux agent
===========

The following describes the Checkmk agent for Linux.
Other POSIX based agents (AIX, Solaris, OpenWRT, FreeBSD, MaxOS, HPUX, NetBSD) are similar, and will hopefully converge.

Introduction and goals
======================
The agent is responsible for collecting the monitoring data on the monitored host.
It will be executed regularly, usually once every minute.
It is queried for that data by the monitoring site in pull mode or the or the local agent controller in push mode.
There are also use cases where we don't care at all about the transport and leave it to the user to realize it (e.g. monitoring via SSH).

Requirements overview
---------------------
The agent should be compatible to as many systems as possible.
Once installed and configured, the agent should not modify the system in any way during operation ("Look, don't touch").
The agent shall not receive any input from the monitoring site.


Architecture
============

White-box overall system
------------------------

.. uml::

    package "Checkmk agent" as check_mk_agent {
        [Asynchronous tasks] as async
        database "File system" as fs
        [Synchronous tasks] as sync
        database "Configuration files" as config
    }

    () stdout

    async -> fs
    fs -> sync
    sync -> stdout
    config --> sync
    config --> async


Interfaces
----------
The agent writes its data to standard out.
The output is line based and sectioned by section- and piggyback header.
By default the output is UTF-8 encoded (unless the header specifies a different encoding).
The agent shall not read from standard in.


Runtime view
============
Data can be either generated synchronously, or asynchronously.
The synchronous and asynchronous operations may or may not be run in the same process.
The standard Systemd setup for instance consists of one permanently running
asynchronous job, and one synchronous job which is socket activated.

In either case, cached data is stored in cache files, and output by the
synchronous job as long as the files are valid.


Risks and technical debts
=========================
This component is by default run as root the monitored system.
