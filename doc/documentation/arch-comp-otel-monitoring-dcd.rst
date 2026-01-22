=============================================
DCD-based monitoring of OpenTelemetry metrics
=============================================

Introduction and goals
======================

The DCD-based monitoring is one the two main channels for monitoring OpenTelemetry (OTel) metrics ingested into the :doc:`metric backend <arch-comp-metric-backend>`.
The goal is to offer application monitoring with Checkmk.
The DCD-based monitoring supports this goal by enabling users to automatically create hosts and services based on OTel metrics stored in the metric backend.

Architecture
============

* A dedicated DCD connector queries the backend.
  The OTel-specific configuration parameters are the resource attribute to use for host names (e.g., "service.name") and optional attribute filters (key-value pairs).
  For each distinct value of the specified resource attribute, a host is created.

* The created hosts have a dedicated host attribute set that associates the host with data in the metric backend.
  This enables us to fetch OTel metrics related to the host.

* A special agent is used to create monitoring data for the created hosts.
  The special agent queries the metric backend for OTel metrics related to the host (based on the dedicated host attribute).
  For each retrieved metric, a service is created.

.. uml:: arch-comp-otel-monitoring-dcd.puml

Risks and technical debts
=========================
Each special agent execution requires spawning a new Python process.
This limits the performance of the DCD-based monitoring, in particular when many hosts are created.
In the future, we will likely implement something along the lines of a dedicated process pool or a dedicated fetcher.
