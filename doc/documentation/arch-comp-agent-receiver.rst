=================================
Agent receiver (`agent-receiver`)
=================================

Introduction and goals
======================
* receives the data pushed by the agent controller
* general endpoint for agent controller communication

Requirements overview
---------------------
* It must be able to handle TLS client certificates


Architecture
============

White-box overall system
------------------------

.. uml::

    [cmk-agent-ctl] as cmk_agent_ctl
    () HTTPS as https
    [Gunicorn] as gunicorn
    () wsgi
    [agent-receiver] as agent_receiver
    () HTTP as rest_http
    [Rest API] as rest_api
    () Filesystem as filesystem
    [Wato] as wato

    cmk_agent_ctl ..> https: use
    https - gunicorn
    gunicorn ..> wsgi: use
    wsgi - agent_receiver
    agent_receiver ..> rest_http: use
    rest_http - rest_api
    agent_receiver - filesystem
    filesystem - wato

Interfaces
----------

The agent-receiver can be accessed via HTTPS on the AGENT_RECEIVER_PORT
(Typically 8000). It accesses the REST-API (with Credentials forwarded by the
agent) and it writes files to the disk which then are read by other Checkmk
components.

.. uml:: arch-comp-agent-receiver.puml

Risks and technical debts
=========================
1. Weak TLS-Configuration: One cannot properly configure TLS versions and TLS
   ciphers in gunicorn. Putting it behind the Site-Apache does currently not
   work.
