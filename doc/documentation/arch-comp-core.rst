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
