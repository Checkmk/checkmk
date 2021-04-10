=====
Hosts
=====

Introduction and goals
======================

The hosts are the entities being monitored.  This document presents
the interactions between the hosts and the server.

There are two main categories of hosts the core monitors:
:ref:`Agent-based hosts<arch-comp-hosts-agent>` and
:ref:`SNMP hosts<arch-comp-hosts-snmp>`.  They are monitored
over different protocols.

.. uml::

   package "CheckMK Server" {
      [CMK]
   }

   cloud {
      [Agent-based host] as agent_host
      agent_host -u- TCP
      agent_host -u- Syslog
   }

   cloud {
      [SNMP host] as snmp_host
      snmp_host -u- SNMP
      snmp_host -u- Trap
   }

   ' agent_host
   [CMK] -- TCP
   [CMK] -- Syslog

   ' snmp_host
   [CMK] -- SNMP
   [CMK] -- Trap

Requirements overview
---------------------

The server-host communication is unidirectional.

Architecture
============

White-box overall system and interfaces
---------------------------------------

.. _arch-comp-hosts-agent:

Agent-based hosts
~~~~~~~~~~~~~~~~~

The data on the agent-based hosts are collected by a so-called agent.
The monitoring core requests these data to the hosts, typically over
TCP, and they are treated by the :doc:`check engine<arch-comp-checkengine>`.

.. uml::

   package "CheckMK Server" {
      ' Components
      [Core]
      [Check Engine] as check_engine
      [Event Console] as event_console
      ' Connections
      [Core] -- event_console : Livestatus
      [Core] -- check_engine : Sockets
   }

   package "Agent-based host" as agent_host {
      [Agent & Plugins] as agent
      [Applications]
      [Syslog]
      agent -u- TCP
      agent -u- ICMP
   }

   ' Connections
   check_engine -- TCP
   check_engine -- ICMP
   check_engine -- [Applications]
   event_console -- [Syslog]

   note left of [Applications]
      Exposed via a variety
      of protocols such as
      HTTPS, FTP, POP3, ...
   end note

.. _arch-comp-hosts-snmp:

SNMP hosts
~~~~~~~~~~

.. uml::

   package "CheckMK Server" {
      ' Components
      [Core]
      [Check Engine] as check_engine
      [Event Console] as event_console
      ' Connections
      [Core] -- event_console : Livestatus
      [Core] -- check_engine : Sockets
   }

   package "SNMP-based host" as snmp_host {
      interface SNMP
      interface Traps
   }

   ' Connections:
   check_engine -- SNMP
   event_console -- Traps

Deployment view
===============

The agent needs to be deployed on the host.  The program may be copied by
the user or updated automatically in the enterprise edition.

.. uml::

   component "CheckMK Server" {
      ' Components
      component Bakery
      artifact "Agent program" as agent
      ' Connections
      Bakery --> agent
   }

   cloud "Agent-based host" as host {
   }

   agent -0)-> host: TCP

Risks and technical debts
=========================

* Every connection to and from the host must be encrypted, if possible.
* An invalid payload in the agent protocol may produce critical errors
  in the server.
* Errors in the agent protocol may result in false positive or false
  negatives in the monitoring.
