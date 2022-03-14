.. _check-engine:

============
Check engine
============

Introduction and goals
======================

WIP

Architecture
============

WIP

Runtime view
============

The raw data is fetched regularly from the sources and forwarded
to the check engine.  The results are passed to the cores in a
Nagios-compatible format.

.. uml::

   Core  -> Queue
   Queue -> Fetcher
   Fetcher -> Source
   Source --> Fetcher : Agent or SNMP data
   group Success and non-critical errors
   Fetcher --> Core : Forwad
   Core -> "Check engine" : Forward
   "Check engine" --> Core : Result in Nagios format
   end
   group Critical error
   Fetcher --> Core : Log
   end

.. uml::

   interface "Fetcher protocol" as FetcherProtocol
   interface "Check API" as CheckAPI
   cloud Source
   component "Check engine" as CheckEngine
   component Core
   component Fetcher

   Core - FetcherProtocol
   FetcherProtocol - Fetcher
   Fetcher - Source
   Core -- CheckEngine
   CheckEngine - CheckAPI
