=============================
Checkmk software architecture
=============================


Top-level Architecture
======================

.. _topo & interfaces:

Topology and interfaces
-----------------------

.. uml:: topology.puml

.. toctree::
   :maxdepth: 1

   arch-comp-omd.rst
   arch-comp-hosts.rst

Components
==========

.. toctree::
   :maxdepth: 1

   arch-comp-gui.rst
   arch-comp-gui-metrics.rst
   arch-comp-apache.rst
   arch-comp-checkengine.rst
   arch-comp-core.rst
   arch-comp-liveproxyd.rst
   arch-comp-dcd.rst
   arch-comp-livestatus.rst
   arch-comp-livestatus-client.rst
   arch-comp-rrd-backend.rst
   arch-comp-rrdcached.rst
   arch-comp-nagvis.rst
   arch-comp-crontab.rst

   arch-comp-agent-linux.rst
   arch-comp-grafana-connector.rst

   arch-comp-template.rst
