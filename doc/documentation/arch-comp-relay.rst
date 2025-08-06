============
Relay Engine
============

Introduction and goals
======================

* Monitor hosts in a segregated network.
* Regularly push monitoring data to a site.
* Fetch monitoring data on demand (e.g. for service discovery in UI).


Requirements overview
---------------------

WIP


Architecture
============

White-box overall system
------------------------

.. uml:: arch-comp-relay.puml

Interfaces
----------
The relay engine does not expose any interfaces.
It only talks to the REST API of the agent receiver
