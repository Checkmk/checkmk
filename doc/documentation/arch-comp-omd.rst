===
OMD
===

Introduction and goals
======================

WIP

Architecture
============

WIP

Runtime view
============

OMD is responsible for starting the main server processes up to the
monitoring core.  The monitoring core has its own child processes.

.. uml::

   [OMD]
   node "OMD Processes" as omd_p {
      [mknotifyd]
      [mkeventd]
      [rrdcached]
      [liveproxyd]
      [crontab]
      [DCD]
      [Apache]
      [Monitoring Core] as core
   }
   node "Core processes" as core_p {
      [Check Helper] as checker
      [ICMPSender]
      [ICMPReceiver]
      [Fetcher]
      [CMK]
   }
   OMD -> omd_p
   core -> core_p
