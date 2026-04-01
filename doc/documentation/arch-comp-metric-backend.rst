==============
Metric backend
==============

Introduction and goals
======================

The metric backend, concretely ClickHouse, is a third-party component.
Its purpose is to store and retrieve time series data (metrics).
The goal is to offer application monitoring with Checkmk.

Note that ClickHouse is not intended to be a general-purpose database for Checkmk.
At the moment, its purpose is solely the support of application monitoring, specifically time series data.
Other signals such as logs or traces will be added in the future.
Hence, only components related to application monitoring should access ClickHouse.

At the moment, we support the ingestion of OpenTelemetry (OTel) metrics via the `ClickHouse exporter <https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/clickhouseexporter>`_ of the OTel collector.
Once ingested, there are two main channels for monitoring:

* :doc:`DCD-based monitoring <arch-comp-otel-monitoring-dcd>`

* :doc:`Custom-query monitoring <arch-comp-otel-monitoring-custom-query>`

Note that Checkmk has another system for storing time series data, :doc:`RRDs <arch-comp-rrd-backend>`.
RRDs are used to store metric data produced by check plugins.
The metric backend works the other way round: We create services based on data stored in the metric backend.
Also, the metric backend offers a much richer feature set, both in terms of storage and querying capabilities.
One prominent example are attributes that uniquely identify a concrete time series.
Finally, the data we store in the metric backend currently has a time-to-live of 14 days, compared to years for RRDs.
In the cloud deployment, this value may be configured differently by the operator.
In the future, we might move the data currently stored in the RRDs to the metric backend as well.
However, this requires further evaluation and there are no concrete plans yet.

Architecture
============

The architecture depends on the deployment scenario (on-premise vs. cloud).
On-premise, once enabled, ClickHouse runs as an :doc:`OMD <arch-comp-omd>` service.
It only accepts connections from localhost (127.0.0.1, and ::1 if IPv6 is available).
Authentication happens via mTLS using the site certificate.
Three dedicated accounts are used: ``checkmk_write_only`` (OTel collector ingestion),
``checkmk_read_only`` (fetcher, DCD connector, self-monitoring, special agents for custom query monitoring, and custom graphing), and
``checkmk_read_write`` (schema manager DDL).

In the cloud deployment, ClickHouse runs externally, as a shared service.
Authentication happens via username and password, using the same three accounts.
In the cloud deployment, encryption is handled transparently by a service mesh.
From Checkmk's perspective the connection to ClickHouse is plain HTTP, but the service mesh creates an encrypted tunnel for the actual traffic.

For querying data, there is no difference between the two deployment scenarios.
We use the same queries in both cases.
Cross-site queries are not supported at the moment.
Each site can only access its own, local ClickHouse instance (on-premise) or the shared ClickHouse instance (cloud).

See the topology diagram for an overview of how the metric backend fits into the :doc:`overall architecture <arch-index>` (on-premise).

Interfaces
----------
For ingestion of OTel metrics, the collector uses ClickHouse's native interface (via TLS).
For querying, we use ClickHouse's HTTP interface (via `ClickHouse Connect <https://clickhouse.com/docs/integrations/python>`_).
On-premise, this is always HTTPS. In the cloud deployment, encryption is provided by the service mesh rather than ClickHouse itself, so the connection to ClickHouse uses HTTP.

Risks and technical debts
=========================
ClickHouse can consume significant system resources, in particular memory.
The memory limit defaults to 50% of total system memory and can be adjusted in the global settings.
