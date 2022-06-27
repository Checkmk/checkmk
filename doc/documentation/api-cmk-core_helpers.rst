================
Core helpers API
================

.. automodule:: cmk.core_helpers

Agent helpers
=============

Base classes and finite-state machine for the parser
----------------------------------------------------

.. automodule:: cmk.core_helpers.agent

.. autoclass:: cmk.core_helpers.agent.AgentParser

.. autoclass:: cmk.core_helpers.agent.ParserState

IPMI helper
-----------

.. automodule:: cmk.core_helpers.ipmi

.. autoclass:: cmk.core_helpers.ipmi.IPMIFetcher

.. autoclass:: cmk.core_helpers.ipmi.IPMISummarizer

.. seealso::

  The parser is :class:`cmk.core_helpers.agent.AgentParser`.

Piggyback helper
----------------

.. automodule:: cmk.core_helpers.piggyback

.. autoclass:: cmk.core_helpers.piggyback.PiggybackFetcher

.. autoclass:: cmk.core_helpers.piggyback.PiggybackSummarizer

Program helpers
---------------

.. automodule:: cmk.core_helpers.program

.. autoclass:: cmk.core_helpers.program.ProgramFetcher

.. seealso::

  - The parser is :class:`cmk.core_helpers.agent.AgentParser`.
  - The summarizer is :class:`cmk.core_helpers.agent.AgentSummarizer`.

TCP helpers
-----------

.. automodule:: cmk.core_helpers.tcp

.. autoclass:: cmk.core_helpers.tcp.TCPFetcher

.. seealso::

  - The parser is :class:`cmk.core_helpers.agent.AgentParser`.
  - The summarizer is :class:`cmk.core_helpers.agent.AgentSummarizer`.

SNMP helpers
============

SNMP helper
-----------

.. automodule:: cmk.core_helpers.snmp

.. autoclass:: cmk.core_helpers.snmp.SNMPFetcher

.. autoclass:: cmk.core_helpers.snmp.SNMPParser

.. autoclass:: cmk.core_helpers.snmp.SNMPSummarizer

SNMP backends
-------------

.. automodule:: cmk.core_helpers.snmp_backend

.. autoclass:: cmk.core_helpers.snmp_backend.classic.ClassicSNMPBackend

.. autoclass:: cmk.core_helpers.snmp_backend.stored_walk.StoredWalkSNMPBackend
