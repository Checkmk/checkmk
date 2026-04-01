=====================================
Metric Backend — Instant Query
=====================================

An instant query returns an aggregated value for each matching time series at a
single point in time. It is similar to the Prometheus ``/query`` endpoint.

Instant queries are used for Checkmk service monitoring: the opinionated monitoring
agent (RED metrics on DCD-created hosts) and the custom query agent both use instant
queries to evaluate whether a metric is in a good or bad state at check time.

Parameters
==========

``metric_name`` *(optional)*
    Filters by metric name. If omitted, all metric names are considered.

``attribute_filters``
    Filters series by their attributes. Three attribute scopes are supported:

    * ``resource_attributes`` — attributes on the resource (e.g. ``service.name``)
    * ``scope_attributes`` — attributes on the instrumentation scope
    * ``data_point_attributes`` — attributes on individual data points

    Each filter specifies a ``key`` and an optional ``value``. If ``value`` is omitted,
    the filter matches any series that has the attribute defined, regardless of its value.

``instant_time``
    The point in time to evaluate the query at, as a Unix timestamp.

``aggregation_lookback_seconds``
    The length of the lookback window. The query considers all data points in the
    interval ``[instant_time - aggregation_lookback_seconds, instant_time]``.

Aggregation by Metric Type
==========================

The aggregation applied within the lookback window depends on the metric type:

* **Gauge** — returns the last observed value within the window.
* **Sum** — returns the rate of change (delta divided by elapsed time) within the window.
* **Histogram** — returns configurable quantiles computed from the histogram buckets
  within the window.

Summary and exponential histogram types are not supported for instant queries.

Result
======

The query yields one ``InstantAggregate`` per matching series. Each result contains
the series metadata (metric name, attributes) and the aggregated value.
