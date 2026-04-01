=====================================
Metric Backend — Internal Components
=====================================

This document describes the internal software components of the metric backend.
For deployment topology, interfaces, and deployment scenarios, see :doc:`arch-comp-metric-backend`.
For the two monitoring channels built on top, see :doc:`arch-comp-otel-monitoring-dcd` and :doc:`arch-comp-otel-monitoring-custom-query`.

Overview
========

The metric backend is self-contained in ``non-free/packages/cmk-metric-backend/``.
All library code, the query client, schema manager, configuration models, and self-monitoring
components live there. Consumers such as the DCD special agent, the DCD connector, and the
custom query special agent are implemented separately and interact with the metric backend
only through its published interfaces.

The central dependency for all consumers is the **query client**, which encapsulates all
read interactions with ClickHouse. Components that need to read from ClickHouse go through it.

Components
==========

Query Client
------------

*Location:* ``non-free/packages/cmk-metric-backend/cmk/metric_backend/query/``

The query client is the single point of access to ClickHouse for all read operations.
It supports four query types:

* **Instant queries** — temporal aggregation (e.g. rate, delta) over a lookback window ending at a point in time.
  Used by two special agents: the opinionated monitoring agent (RED metrics on DCD-created hosts) and the custom query agent (user-specified queries).
* **Range queries** — aggregated values over a time range at fixed step intervals.
  Called live from the UI when rendering custom graphs.
* **Latest value aggregations** — the last observed raw sample per series within a lookback window, without temporal aggregation.
  Used by the DCD special agent for generic per-host metric discovery.
* **Metadata queries** — series metadata for autocompleters and host discovery.

See :doc:`arch-comp-metric-backend-instant-query` and :doc:`arch-comp-metric-backend-range-query`
for detailed parameter documentation of the respective query types.

A thin ``RetryingClient`` wrapper (``retrying_client.py``) sits below the query client and
handles connection setup and exponential-backoff retries on transient ClickHouse errors.
Both self-hosted and cloud connections are configured here based on the active config.


Configuration
-------------

*Location:* ``non-free/packages/cmk-metric-backend/cmk/metric_backend/config.py``, ``cmk/nonfree/ultimate/metric_backend/gui/_config_domain.py``

The metric backend configuration is stored in ``etc/check_mk/metric_backend.json`` and
read at startup by all components that need to connect to ClickHouse. The config is a
discriminated union of two models:

* ``ConfigMetricBackendSelfHosted`` — ports, mTLS certificate paths, server hostname
* ``ConfigMetricBackendCloud`` — address, HTTP port, TLS flag, credentials

The config file is written by the GUI config domain (``_config_domain.py``) when the
operator enables or reconfigures the metric backend in the Checkmk Setup. On activation,
the config domain also regenerates the ClickHouse XML config and restarts the service.

Schema Manager
--------------

*Location:* ``non-free/packages/cmk-metric-backend/cmk/metric_backend/schema_manager/``

The schema manager is a CLI tool that applies versioned DDL migrations to ClickHouse.
It maintains a revision chain where each revision can be upgraded or downgraded independently.
It supports a ``--dry-run`` mode for inspecting the queries that would be executed
without actually running them.

The schema manager is invoked automatically during activation when the metric backend
is enabled or updated via the Checkmk Setup GUI. We also use an OMD update hook to
ensure the schema is kept up-to-date on a site update. For the cloud deployment it uses
``ON CLUSTER`` DDL and ``ReplicatedMergeTree`` engines to deploy the schema across
the ClickHouse cluster.


Self-Monitoring
---------------

*Location:*

* ``non-free/packages/cmk-metric-backend/cmk/metric_backend/monitor.py``
* ``non-free/packages/cmk-metric-backend/cmk/plugins/metric_backend_omd/``

A monitoring script (``monitor.py``) for the Checkmk agent that runs on the site itself and checks the
health of the ClickHouse instance. It emits a ``<<<metric_backend_omd>>>`` agent section
containing:

* A health ping result (HTTP status or error)
* The custom metrics count (All distinct active time series excluding ClickHouse internal series)

The accompanying section plugin (``cmk/plugins/metric_backend_omd/``) parses this section to
be used by the corresponding check plugin to create an "OMD ``<site>`` metric backend"
service with configurable thresholds. This channel is only active for self-hosted deployments.


Consumers
=========

The metric backend is consumed by several external components that are documented separately:

* The DCD special agent and DCD connector — see :doc:`arch-comp-otel-monitoring-dcd`
* The custom query special agent — see :doc:`arch-comp-otel-monitoring-custom-query`
* The custom graphing feature
