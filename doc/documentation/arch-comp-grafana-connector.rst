=================
Grafana Connector
=================

Introduction and goals
======================

Checkmk has an integrated graphing system with comprehensive features for
visualizing and storing of metrics. However, it might still be helpful to use
Grafana as an external graphing system — for example, if you are already using
Grafana and have other data sources connected to it and want to have a single,
unified dashboard.

Requirements:

* Make Checkmk time series data available in Grafana
* Allow users to select builtin, so called template graphs of Checkmk,
  which already provides nice titles, colors and scaling of values for human
  beings.
* Enable users to access single metrics in their canonical form.
* Allow users to create complex graphs based on a dynamic selection of
  services and their metrics.
* Make metrics of a whole distributed environment available through a single
  data source configuration in Grafana.

Interfaces
----------

The connector interfaces with Checkmk using the REST API. In distributed
environments it connects to the REST API of the central site to be able to
access the metrics of all configured sites.

Project infrastructure
======================

The connector is a pure `GitHub project <https://github.com/tribe29/grafana-checkmk-datasource>`_.
Issues and pull requests are managed on GitHub and also related CI jobs are
built as GitHub actions.

See also
--------
- `User manual: Integrating Checkmk in Grafana <https://docs.checkmk.com/master/en/grafana.html>`_
- `Github repository <https://github.com/tribe29/grafana-checkmk-datasource>`_

