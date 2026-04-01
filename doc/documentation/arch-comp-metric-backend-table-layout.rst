=====================================
Metric Backend — ClickHouse Table Layout
=====================================

This document describes the ClickHouse table schema used by the metric backend,
the motivation behind key design decisions, and the materialized views that maintain
derived data. For deployment and component overview, see :doc:`arch-comp-metric-backend`
and :doc:`arch-comp-metric-backend-internals`.

Samples Tables
==============

All time series data is stored in a family of tables prefixed ``metrics_samples_*``,
one per OTel metric type:

* ``metrics_samples_gauge``
* ``metrics_samples_sum``
* ``metrics_samples_histogram``
* ``metrics_samples_exponential_histogram``
* ``metrics_samples_summary``

Each table uses ``MergeTree`` (on-premise) or ``ReplicatedMergeTree`` (cloud) and is
ordered by ``(MetricName, SeriesId, StartTimeUnix, TimeUnix)``.

``SeriesId`` is a UUID derived deterministically from the series identity::

    reinterpretAsUUID(sipHash128(MetricName, ResourceAttributes, ScopeAttributes, Attributes, 'gauge'))

The ordering key is chosen so that queries can first filter cheaply by ``MetricName``,
then prune down to the relevant series via ``SeriesId``. Read queries are deeply nested
(window functions, grid alignment, gap filling, aggregation, and a final attribute JOIN),
but at the innermost raw-samples level the query restricts rows using a
``SeriesId IN (SELECT DISTINCT SeriesId ... LIMIT <num_series_max>)`` subquery. That
subquery applies the same time-range and attribute filters as the outer query and caps
the result at typically 100 series. Because the table is ordered by ``SeriesId``,
ClickHouse can locate each series' data contiguously on disk, making this pruning highly
effective before the more expensive operations run over the reduced row set.
``TimeUnix`` at the end of the key further narrows the scan to the requested time window.
Additional skip indexes on the attribute columns support attribute-based filtering without
a full table scan.

All samples tables are partitioned by ``toDate(TimeUnix)`` and carry a configurable TTL
(default 14 days on-premise).

Attribute-to-Series Table
=========================

``metrics_attribute_to_series`` stores one row per unique series, containing all
metadata columns (metric name, type, attributes) and a ``LastSeen`` timestamp.
It uses ``ReplacingMergeTree(LastSeen)`` ordered by ``(MetricName, MetricType, SeriesId)``.

The purpose of this table is to enable fast metadata lookups — autocompleters, host
discovery in the DCD connector, and series count queries — without scanning the much
larger samples tables. Eventual consistency is achieved through the ``ReplacingMergeTree``
engine: when a series is seen again, the new row (with a higher ``LastSeen``) replaces
the old one during background merges.

Unlike the samples tables, ``metrics_attribute_to_series`` is **not partitioned**. The
reason is fundamental to how ``ReplacingMergeTree`` deduplication works: ClickHouse only
merges parts within the same partition, never across partition boundaries. If the table
were partitioned by day, a series that emits data continuously over a 14-day TTL window
would produce one surviving row per day partition — 14 rows instead of one — because the
deduplication merges can never consolidate rows that live in different partitions.
Partitioning would therefore inflate the table size by up to 14× and defeat the purpose
of the engine. Without partitioning, all rows for a given series end up in the same pool
of parts, so ``ReplacingMergeTree`` can collapse them down to a single row as intended.

The table carries the same TTL as the samples tables, based on ``LastSeen``.

Queries on this table almost always filter by ``LastSeen`` to restrict results to series
seen within a recent lookback period. To keep this fast, the table carries a ``minmax``
skip index on ``LastSeen`` (``INDEX idx_last_seen LastSeen TYPE minmax GRANULARITY 1``).
ClickHouse stores the min and max ``LastSeen`` per granule and can skip any granule whose
maximum falls below the filter threshold.

The table also carries bloom filter skip indexes on the keys and values of all three
attribute map columns (``ResourceAttributes``, ``ScopeAttributes``, ``Attributes``),
mirroring the indexes on the samples tables, to accelerate attribute-based filtering.

Materialized Views
==================

Attribute-to-Series Views
--------------------------

One trigger-based materialized view exists per samples table, all writing into
``metrics_attribute_to_series``:

* ``metrics_attribute_to_series_gauge_mv``
* ``metrics_attribute_to_series_sum_mv``
* ``metrics_attribute_to_series_histogram_mv``
* ``metrics_attribute_to_series_exponential_histogram_mv``
* ``metrics_attribute_to_series_summary_mv``

Each view fires on INSERT into its source table, selects the metadata columns, and sets
``LastSeen = TimeUnix``. The ``ReplacingMergeTree`` engine on the target table ensures
only the most recently observed row per series is retained after merges.

ClickHouse Internal Metrics
-----------------------------

Three scheduled materialized views feed ClickHouse's own internal metrics into the
regular metric tables, making ClickHouse itself observable through the same pipeline.
All three views refresh every 30 seconds.

* ``ch_events_mv`` — reads from ``system.events``, writes cumulative sum metrics
  into ``metrics_samples_sum`` with ``ServiceName = 'checkmk_clickhouse_events'``
  and metric names prefixed ``ClickHouseCurrentEvent_``.
* ``ch_metrics_mv`` — reads from ``system.metrics``, writes gauge metrics
  into ``metrics_samples_gauge`` with ``ServiceName = 'checkmk_clickhouse_metrics'``
  and metric names prefixed ``ClickHouseCurrentMetric_``.
* ``ch_asynchronous_metrics_mv`` — reads from ``system.asynchronous_metrics``, writes
  gauge metrics into ``metrics_samples_gauge`` with
  ``ServiceName = 'checkmk_clickhouse_asynchronous_metrics'``
  and metric names prefixed ``ClickHouseAsyncMetric_``.

Licensing
---------

* ``licensing_active_series_count`` — stores periodic counts of distinct active series,
  used for license reporting. Uses ``ReplacingMergeTree`` ordered by time bucket.

* ``licensing_active_series_count_mv`` — a scheduled materialized view that runs
  every 20 minutes. It counts distinct active ``SeriesId`` values from
  ``metrics_attribute_to_series`` within each 20-minute bucket, excluding ClickHouse
  internal series. Results are appended to ``licensing_active_series_count``.
