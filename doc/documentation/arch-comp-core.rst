==================
Nagios & Microcore
==================

Introduction and goals
======================

WIP

Architecture
============

Components and interfaces
-------------------------

Configuration
~~~~~~~~~~~~~

.. uml::

   object Core {
     world : World2
     old_worlds : [World1]
   }
   object World1 {
     hosts : [Object11, Object12]
   }
   object World2 {
     hosts : [Object21, Object22, Object23]
   }
   object Object11 {
     state : State1
   }
   object Object12 {
     state : State2
   }
   object Object21 {
     state : State1
   }
   object Object22 {
     state : State2
   }
   object Object23 {
     state : State23
   }
   object State1 {
     shared = 1
   }
   object State2 {
     shared = 1
   }
   object State23 {
     shared = 0
   }
   Core *-- World1
   Core *-- World2
   World1 *-- Object11
   World1 *-- Object12
   World2 *-- Object21
   World2 *-- Object22
   World2 *-- Object23
   Object11 *-- State1
   Object12 *-- State2
   Object21 *-- State1
   Object22 *-- State2
   Object23 *-- State23

Livestatus
~~~~~~~~~~

.. uml::

   package "On disk" as disk {
     database Config
     database State
   }

   disk   <-- [Core] : use
   [Core] -- Livestatus
   [Core] -- Log
   [Core] -  [Check engine]

See also
~~~~~~~~
- :doc:`arch-comp-livestatus`

Risks and technical debts
=========================

Risks
-----

Programming errors in the core stale the monitoring completely

Technical debts
---------------

We have to keep enterprise and raw editions partly in sync
because the rely on different core implementations:  the
enterprise editions use a closed-source CMC microcore and
the raw edition uses the third-party `Nagios`_ core.

The Nagios core further dictates some of our protocols such
as the format with which the :ref:`check results<check-engine>`
are passed to the core.

.. _Nagios: https://www.nagios.org/
