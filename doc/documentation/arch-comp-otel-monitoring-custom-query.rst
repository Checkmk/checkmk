================================================
Custom-query monitoring of OpenTelemetry metrics
================================================

Introduction and goals
======================

The custom-query monitoring is one the two main channels for monitoring OpenTelemetry (OTel) metrics ingested into the :doc:`metric backend <arch-comp-metric-backend>`.
The goal is to offer application monitoring with Checkmk.
The custom-query monitoring supports this goal by enabling users to first explore the ingested OTel metrics and then create alerts for selected time series.
A time series is set of (time stamp, value) pairs uniquely identified by a metric name and a set of attributes.

Architecture
============

.. uml:: arch-comp-otel-monitoring-custom-query.puml

Runtime view
============

* The entry point is the custom graph editor.
  If the backend is enabled, it offers a configuration section for adding OTel metrics stored in the metric backend to the custom graph.

* Once added, a monitoring button becomes available for the graphed OTel metric.
  This button opens a slide-in interface to configure a special agent rule.

* After saving and activating this rule, the host which it applies to will discover additional services — one for each matching time series.

Risks and technical debts
=========================
Each special agent execution requires spawning a new Python process.
This limits the performance of the custom-query monitoring.
However, we expect this to be less of an issue compared to the :doc:`DCD-based monitoring <arch-comp-otel-monitoring-dcd>`, since custom-query monitoring is expected to to run on a smaller set of hosts.
