.. _graphs:

=====================
Metric & Graph system
=====================

Introduction and goals
======================

Checkmk provides specific knowledge around its check-plugin system.
Check-plugins are aware of the health of the service they monitor and thus the
recorded metrics (performance data) include richer meta-data within the system.
As such beyond being a values time series, the metric system in the User
Interface assigns to each metric a Name, unit and color. Units are further
characterized in our system by its name, symbol and description, on top of it
they are equipped with methods to render themselves in a human readable
way (using magnitude prefixes).

Due to the independent development of check-plugins, it often arises that they
deliver metrics which represent a common concept, e.g. "RAM used", yet they are
not equally named across all check-plugins. In order to reunify this
non-standardized names the metric translations subsystem exists. Its duty relies
on renaming and re-scaling metric names and values from individual check-plugins
outputs into their canonical name, and scale. From there on the Metric System
can use defined metric names & unit for an homogeneous display. This was enough
for simple display, once Checkmk introduced bulk queries and statistical
analysis of metrics, metrics names within check-plugin had to be unified and
thus an extra metric-merge utility enhanced the translation system. It allows to
rename the old metric-name on the check-plugin yet still allow the GUI to
retrieve from RRD the data of the old metric and merge both time series. This
allows a path to standardize metric-names going forward and clean RRDs columns.

The final step is to display time series. Metrics belonging to a service are
contextually grouped into graphs, which provides a better utility to the user
compared to assigning each metric to an individual graph. A graph plug-in
declares the metrics it draws, and is matched dynamically against the metrics a
service actually reports.

Architecture
============

Metrics, graphs, Perf-O-Meters and metric translations are declared as plug-ins
against the ``cmk.graphing`` API (``packages/cmk-plugin-apis``). They are
discovered per site and evaluated by ``cmk.graphing_engine``
(``packages/cmk-graphing-engine``), which matches a graph plug-in against the
available metric names, fetches the time series from RRD and evaluates the
declared quantities into curves. The engine produces data only; ``cmk/gui``
renders it - as a Vue component in the browser, or as PNG for notification mails
and PDF reports.

Risks and technical debts
=========================

The meta data and output values of checks are controlled by their authors and
can, hence, contain malicious payloads that are ultimately rendered on the
client side within the monitoring and administration web interface. The metrics
are calculated by check plugins and then written by the check plugin API. The
data has to be sanitized there (e.g. numbers only), prior to being rendered on
the client side.
