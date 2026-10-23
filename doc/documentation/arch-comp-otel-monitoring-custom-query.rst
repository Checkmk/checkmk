==================================================
Custom-service monitoring of OpenTelemetry metrics
==================================================

Introduction and goals
======================

The custom-service monitoring is one of the two main channels for monitoring OpenTelemetry (OTel) metrics ingested into the :doc:`data backend <arch-comp-data-backend>`.
The goal is to offer application monitoring with Checkmk.
The custom-service monitoring supports this goal by enabling users to first explore the ingested OTel metrics and then create alerts for selected time series.
A time series is set of (time stamp, value) pairs uniquely identified by a metric name and a set of attributes.

Architecture
============

.. uml:: arch-comp-otel-monitoring-custom-query.puml

Runtime view
============

* The entry point is the custom graph editor.
  If the backend is enabled, it offers a configuration section for adding OTel metrics stored in the data backend to the custom graph.

* Once added, a graphed OTel metric can be turned into a custom service.
  This opens a slide-in, prefilled from the graphed metric, that creates a "Custom Service" rule.
  The same rules can be created, edited and deleted on the "Custom Services" Setup page and through the REST API.
  Each rule holds exactly one query.

* After activating, the telemetry metrics fetcher of every host the rule applies to runs the rule's query against the data backend.
  It writes the results into the host's ``telemetry_custom_service`` section: one line per rule, in rule order, including a line for a rule that matched nothing.
  The queries are deliberately not scoped to the host: the rule alone says which time series it wants.

* The ``telemetry_custom_service`` check plugin creates one service per resolved service name template, typically one per matching time series.
  A service name that more than one time series resolves to is reported as UNKNOWN.

Risks and technical debts
=========================

The telemetry metrics fetcher only runs for hosts with a metrics association.
The :doc:`DCD-based monitoring <arch-comp-otel-monitoring-dcd>` sets one on every host it creates.
A "Custom Service" rule applying to a manually created host without a metrics association produces no services.
