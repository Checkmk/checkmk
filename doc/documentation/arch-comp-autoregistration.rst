=============================================================================
Auto-registration of hosts (`cmk.gui.cce.plugins.watolib.agent_registration`)
=============================================================================

Introduction and goals
======================
* Processes a request for registration dropped by the agent receiver
* If successful creates a new host in the monitoring, establishes a trusted connection and discovers the services

Requirements overview
---------------------
* This is a CCE feature
* It must be able to deal with many incoming requests at once
* It must respect the users role & permissions


Architecture
============

White-box overall system
------------------------


.. uml::

    [cmk-agent-ctl] as cmk_agent_ctl
    () HTTPS as https
    [agent-receiver] as agent_receiver
    () Filesystem as filesystem
    [Remote site] as remote
    () "HTTP\nautomation calls" as automations
    [Central site] as central

    cmk_agent_ctl ..> https: send registration request
    https - agent_receiver
    agent_receiver - filesystem: write request for registration
    agent_receiver - remote: query certificate config via RestAPI
    filesystem - remote: read R4R

    remote - automations
    automations - central

Interfaces
----------

.. uml:: arch-comp-autoregistration.puml

Risks and technical debts
=========================
1. Due to various cron jobs involved, the total processing time of a R4R can add up to several minutes.
