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
   arch-comp-gui-vue.rst
   arch-comp-gui-metrics.rst
   arch-comp-painters-v1.rst
   arch-comp-apache.rst
   arch-comp-checkengine.rst
   arch-comp-core.rst
   arch-comp-smartping.rst
   arch-comp-liveproxyd.rst
   arch-comp-mknotifyd.rst
   arch-comp-dcd.rst
   arch-comp-distributed.rst
   arch-comp-livestatus.rst
   arch-comp-livestatus-client.rst
   arch-comp-kube-monitoring.rst
   arch-comp-rrd-backend.rst
   arch-comp-rrdcached.rst
   arch-comp-nagvis.rst
   arch-comp-crontab.rst
   arch-comp-backup.rst
   arch-comp-agent-receiver.rst
   arch-comp-autoregistration.rst
   arch-comp-metric-backend.rst
   arch-comp-otel-monitoring-dcd.rst
   arch-comp-otel-monitoring-custom-query.rst

   arch-comp-agent-abstract.rst
   arch-comp-agent-linux.rst
   arch-comp-agent-controller.rst
   arch-comp-agent-updater.rst
   arch-comp-agent-bakery.rst
   arch-comp-relay.rst
   arch-comp-grafana-connector.rst

   arch-comp-template.rst
