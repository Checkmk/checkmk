.. _check-engine:

============
Check engine
============

Introduction and goals
======================

This package contains the business logic for the checkers.

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

The typical sequence of events is

.. uml::

   actor User
   participant Fetcher
   participant Parser
   participant Summarizer

   User -> Fetcher : fetch()
   Fetcher --> Fetcher : I/O
   Fetcher -> Parser : parse(RawData)
   Parser --> Parser : parse data
   Parser --> Parser : cache data
   Parser -> Summarizer : summarize(HostSections)
   Summarizer --> User : ServiceCheckResult

.. seealso::

   :py:mod:`cmk.fetchers` for the fetchers.

   ``cmk.base.sources``: The entry point into the core helpers from base.
