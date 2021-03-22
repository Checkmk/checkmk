==========
Livestatus
==========

Introduction and goals
======================

WIP

Architecture
============

Components and interfaces
-------------------------

Livestatus is a library that behaves like a database and a protocol.

.. uml::

  database Livestatus
  interface Socket

  [Core] - livestatus
  Livestatus - Socket

See also
~~~~~~~~
- :doc:`arch-comp-core`
- Retrieving status data via Livestatus
  `[doc] <https://docs.checkmk.com/latest/en/livestatus.html>`_
