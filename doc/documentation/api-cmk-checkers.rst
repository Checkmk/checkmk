============
Checkers API
============

.. automodule:: cmk.checkers

Agent checkers
==============

Base classes and finite-state machine for the parser
----------------------------------------------------

.. automodule:: cmk.checkers.agent

.. autoclass:: cmk.checkers.agent.AgentParser

.. autoclass:: cmk.checkers.agent.ParserState

IPMI checkers
-------------

.. automodule:: cmk.checkers.ipmi

.. autoclass:: cmk.checkers.ipmi.IPMIFetcher

.. seealso::

  The parser is :class:`cmk.checkers.agent.AgentParser`.

Piggyback checkers
------------------

.. automodule:: cmk.checkers.piggyback

.. autoclass:: cmk.checkers.piggyback.PiggybackFetcher

Program checkers
----------------

.. automodule:: cmk.checkers.program

.. autoclass:: cmk.checkers.program.ProgramFetcher

.. seealso::

  - The parser is :class:`cmk.checkers.agent.AgentParser`.

TCP checkers
------------

.. automodule:: cmk.checkers.tcp

.. autoclass:: cmk.checkers.tcp.TCPFetcher

.. seealso::

  - The parser is :class:`cmk.checkers.agent.AgentParser`.

SNMP checkers
=============

SNMP checkers
-------------

.. automodule:: cmk.checkers.snmp

.. autoclass:: cmk.checkers.snmp.SNMPFetcher

.. autoclass:: cmk.checkers.snmp.SNMPParser

SNMP backends
-------------

.. automodule:: cmk.checkers.snmp_backend

.. autoclass:: cmk.checkers.snmp_backend.classic.ClassicSNMPBackend

.. autoclass:: cmk.checkers.snmp_backend.stored_walk.StoredWalkSNMPBackend
