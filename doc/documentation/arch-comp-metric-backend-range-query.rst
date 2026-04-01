=====================================
Metric Backend — Range Query
=====================================

A range query evaluates an instant query repeatedly across a fixed time grid, returning
an aggregated value at each grid point. It is similar to the Prometheus
``/query_range`` endpoint.

Range queries are used for rendering custom graphs: the UI calls a range query to obtain
the time series data needed to plot a line graph.

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

``start_time``
    Start of the time range as a Unix timestamp.

``end_time``
    End of the time range as a Unix timestamp.

``step_seconds``
    Distance in seconds between consecutive grid points. The grid is defined as
    ``[start_time, start_time + step, start_time + 2*step, ..., end_time]``.

``aggregation_lookback_seconds``
    The length of the lookback window applied at each grid point. For a grid point ``t``,
    the query considers data points in the interval
    ``[t - aggregation_lookback_seconds, t]``.

Aggregation by Metric Type
==========================

The aggregation applied at each grid point depends on the metric type:

* **Gauge** — returns the last observed value within the lookback window.
* **Sum** — returns the rate of change within the lookback window.
* **Histogram** — returns a single configurable quantile computed from the histogram
  buckets within the lookback window.

Summary and exponential histogram types are not supported for range queries.

Result
======

The query yields one ``CustomMetricRangeAggregate`` per matching series. Each result
contains the series metadata and an array of (timestamp, value) pairs, one per grid
point. Grid points for which no or too little data was observed within the lookback
window are filled with ``null``. This might be the case if no data is observed at all,
or if the metric is a sum or histogram and the lookback window contains only a single
data point (since rate of change or the change in quantiles cannot be computed from
a single point).
