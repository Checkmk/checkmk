=====
Views
=====

Introduction and goals
======================

*Views* show the live monitoring state: tables of hosts, services, events,
downtimes and more, with filters, sorting and commands. They are part of the
*Monitoring* area of the :doc:`GUI <arch-comp-gui>`.

Two generations exist side by side:

* **Classic views**: configurable *visuals* that are rendered server-side as
  HTML. Code: ``cmk.gui.views`` and the packages it builds on.
* **Monitoring pages** (Views 3.0): dedicated pages rendered by Vue
  applications, which get their data from internal REST endpoints. Code:
  ``cmk.gui.monitor`` and ``packages/cmk-frontend-vue/src/monitoring``.

Goals of the monitoring pages are a responsive UI, a typed contract between
backend and frontend, and domain logic that is independent of the transport
and of the classic view code. The classic views stay available until the
monitoring pages cover their functionality.

Both generations read from Livestatus, use the same permissions and the same
authorization of what a user may see.

Architecture
============

.. uml:: arch-comp-gui-views-components.puml

Classic views
-------------

A classic view is a stored description that combines building blocks which
are looked up by name in registries:

* **Data source**: provides the rows, usually from a Livestatus table.
* **Info and filters**: select and narrow the rows.
* **Painters**: render the cells.
* **Sorters and layouts**: order and arrange the rows.
* **Commands and icons**: actions on rows and status icons.

The entry point ``page_show_view`` loads the view, derives the filter context
from the request, fetches the rows through the data source, sorts and filters
them and lets the renderer produce HTML, or exports them (CSV, JSON).
Built-in views are defined in code, user-defined views are stored per user.
Registrations happen in ``cmk.gui.views.registration``; plugins can extend all
registries (see :doc:`arch-comp-gui`).

Monitoring pages
----------------

Each page family (hosts, services) is built in the same layers; dependencies
point downwards only:

* **Page**: the GUI page. Checks permissions, renders header and menu and
  mounts the Vue component with a typed configuration object
  (``cmk.shared_typing.monitoring``, generated from JSON schemas).
* **API**: internal REST endpoints, only available in the internal API
  version. They validate the request and map domain objects to API models.
* **Repositories**: ``Protocol`` classes that state what the endpoints need.
  Tests use stubs.
* **Implementation**: the Livestatus implementation of the repositories. It
  requests only the columns that the shown fields need.
* **Domain models**: independent of the API models, so that API changes do
  not leak into the logic.

Some collaborators are injected at wiring time instead of imported, so the
domain stays independent of them: the classic command registry, the Setup
folder titles and the legacy host menus. Wiring is done in
``cmk.gui.common_registration``. The other direction is wired there, too:
the global search gets the links of its monitoring results from the router,
so that ``cmk.gui.search`` does not import ``cmk.gui.monitor``. Action menus
and icons come from the same icon registry that the classic views use, so
both generations stay consistent.

The Vue applications share one base for all tables
(``MonitoringService``): it owns rows, search, filter, sorting, column
selection and the refresh timer. A page only supplies how to fetch its rows.
The page state (columns, sort, filter, opened row) lives in the URL, which
makes pages shareable. Actions use the existing command infrastructure through
the REST API.

The CSV and JSON export is shared as well, so a new page family uses it
instead of writing its own: ``cmk.gui.monitor.export`` builds the Export menu
of the page, and in the Vue application ``RowExport`` writes the files from a
per-page column schema, ``useRowExport`` answers the menu entries and
``MonitoringExportFeedback`` shows the result. The page only supplies its
column schema; the rows come from ``MonitoringService``.

Interfaces
----------

* GUI pages, registered as page endpoints (the page name is the URL):

  * Classic: ``view`` (``cmk/gui/views/page_show_view.py``).
  * Monitoring pages: ``monitor_all_hosts``
    (``cmk/gui/monitor/hosts/_pages/_monitor_all_hosts.py``),
    ``monitor_all_services``
    (``cmk/gui/monitor/services/_pages/_monitor_all_services.py``) and
    ``monitor_host_services``
    (``cmk/gui/monitor/services/_pages/_monitor_host_services.py``).

* The router (``cmk/gui/monitor/router``), the monitoring side of the global
  search. It decides where a search lands in the monitoring pages, whether
  the user presses Enter or clicks a result, in two parts:

  * The page ``monitor_search``, for pressing Enter: it renders nothing
    itself, but parses a query of the global search with
    ``cmk.gui.search.spec`` and redirects to the monitoring page that can show
    it, with the query turned into the page's filters. A query without prefix
    is tried in the order of the classic quicksearch as a filter on host name,
    alias, address and folder title; the first that finds hosts is opened, or
    the search box of "All hosts" when none does. An invalid query goes to the
    search box as typed.
    One that no page can filter on yet goes to the legacy search of the
    classic views (``search_open.py``) and is logged by its prefixes and the
    reason, not by its values; this keeps ``search_open.py`` needed as a
    fallback until the pages can filter on every prefix. Before it redirects
    a host search (with or without prefix), it asks Livestatus through
    ``HostTable.first_hosts`` of ``cmk.gui.monitor.hosts.table`` how many
    hosts "All hosts" would list for it; for a single host, it opens
    "Services of host" for that host with the host panel open instead.
  * The result links (``monitor_result_url``), for clicking a result in the
    list of the global search: a host opens "Services of host" with the host
    panel open, a service opens "Services of host" of its host with the
    service panel open. ``cmk.gui.search`` offers this as an injection
    point (``MonitoringResultUrl`` with the targets of
    ``cmk.gui.search.livestatus_links``) and keeps the link to the classic view
    for a result no monitoring page can show yet, such as host and service
    groups. The sidebar snapin "Quick search" keeps linking to the classic
    views.

* Internal REST endpoints below ``/monitor/`` (see the *Checkmk Internal*
  documentation of the REST API).
* ``cmk.gui.monitor.hosts.table``: the supported entry point for server-side
  consumers that query hosts, such as the dashboards, the PDF reports and
  the router ``monitor_search``. Other components use only this module, not
  the package internals. It offers ``HostTable`` (with ``list``,
  ``parse_filter`` and ``first_hosts``, the first two hosts a filter
  finds), ``FilterNode``, the filter tree ``first_hosts`` takes,
  ``MonitorFolders``, the column catalogs ``ALL_HOSTS_TABLE`` and
  ``HOST_TABLE``, ``HostEntry``,
  ``HOST_LISTING`` (which validates a request body of the internal REST
  endpoint that lists hosts with the endpoint's own model) and
  ``ALL_HOSTS_PERMISSION``, the permission the page "All hosts" needs. The
  rows are ``HostEntry``, the response model of the internal REST endpoint,
  so a change of that model also changes what these consumers get.
* ``cmk.gui.monitor.services.table``: the same for the services of one host.
  It offers ``HostServicesTable`` (with ``list`` and ``parse_filter``), the
  column catalog ``HOST_SERVICES_TABLE``, ``HostServiceEntry``,
  ``ServiceOptionalField``, the errors ``HostNotFoundError`` (also for a
  site that does not exist) and ``InvalidServiceFilterError``,
  ``SERVICE_LISTING`` (which validates a request body of the internal REST
  endpoint that lists the services of a host with the endpoint's own model)
  and ``HOST_SERVICES_PERMISSION``, the permission the page "Services of
  host" needs. The rows are ``HostServiceEntry``, the response model of
  that endpoint.
* Livestatus, locally or via :doc:`arch-comp-liveproxyd` for remote sites.
* Outside Community, the pages "All hosts" and "Services of host" link to
  an instant PDF report of reporting with the columns they show and the
  request body they send to their internal REST endpoint, with relative age
  filters already resolved. Reporting turns that body into the listing with
  ``HOST_LISTING`` from ``cmk.gui.monitor.hosts.table`` and
  ``SERVICE_LISTING`` from ``cmk.gui.monitor.services.table``.
* ``cmk.gui.monitor.table_widget``: what the tables of the monitoring pages
  share. ``ColumnCatalog`` implements the column catalog ``TableCatalog``
  and ``ListingParser`` turns a request body into a ``TableListing``; the
  hosts and services packages only plug in their columns and models.
* ``cmk.shared_typing.monitoring.action_ident`` (generated from
  ``packages/cmk-shared-typing/source/monitoring/action_ident.json``): the
  contract between backend and frontend for the commands that the
  monitoring pages and the monitoring tables of the dashboards offer on a
  host or a service. It is the only list of their IDs, in the order they
  are offered: the backend offers ``HOST_SUPPORTED_ACTIONS`` and
  ``SERVICE_SUPPORTED_ACTIONS`` straight from the generated enums, and the
  frontend types its actions with them. Every ID needs a command in the
  command registry for its object type and an action in the frontend; a
  unit test fails if the backend has no command for one, and the type check
  of the frontend fails if it has no action for one.

Coexistence
-----------

The classic views offer a link to the new pages and the new pages a link back.
The link from a classic view carries the view's filters, translated into
the filter tree of the page, and names the filters it could not take over,
which the page lists as not applied.

The global search (``packages/cmk-frontend-vue/src/unified-search``) is an
entry point into the monitoring pages, too: pressing Enter with the
monitoring or "all" search selected opens ``monitor_search.py`` with the
query, and the router picks the page. A query no monitoring page can filter
on yet goes on to the legacy search of the classic views (``search_open.py``),
which the sidebar snapin "Quick search" still opens directly. Clicking a
host or service in the result list of the global search opens the monitoring
pages as well. There is no setting to switch back yet.

Risks and technical debts
=========================

* Two implementations of the same pages have to be kept consistent until the
  classic views are replaced.
* The columns of the pages "All hosts" and "Services of host" and their
  titles are defined in the frontend (``all-hosts/columns.ts``,
  ``host-services/columns.ts``) and, for server-side consumers such as the
  PDF reports, in the ``_table_catalog.py`` of ``cmk/gui/monitor/hosts`` and
  ``cmk/gui/monitor/services``. A new or renamed column has to touch both.
  The titles of the time columns differ on purpose: the pages show an age
  ("Check age", "State age"), the PDFs an absolute time ("Last check",
  "Last state change").
* The server-side consumers of ``cmk.gui.monitor.hosts.table`` and
  ``cmk.gui.monitor.services.table`` read ``HostEntry`` and
  ``HostServiceEntry``, API models, instead of domain models, including the
  ``ApiOmitted`` placeholder of the REST framework. Reshaping a response of
  the internal endpoints has to keep them working, too.
* Classic data sources are loosely typed (rows are dicts) and derive the
  queried columns at runtime, which makes it hard to see what is queried.
* The filter vocabulary of the monitoring pages is defined in the API, the
  Livestatus translation and the frontend. A change has to touch all three.
  The instant report of All hosts reuses the API's model for it.
* The filters of the classic views and the dashboards are translated into
  the vocabulary a fourth time (``cmk.gui.monitor.legacy_context`` and the
  ``context_filters.py`` of ``cmk/gui/monitor/hosts`` and
  ``cmk/gui/monitor/services``). The links from the classic views use it
  more strictly: they keep only conditions the columns of the page can
  show, and report the other filters as not applied. Which conditions,
  field and operator, the columns show comes from the schema
  ``monitoring/page_filter_condition.json`` of ``cmk-shared-typing``. A
  frontend test fails if the columns drift from it, going by a list of
  what each kind of column filter shows that the tests of the filter
  components back. Two rules stay unchecked copies of those components:
  one condition or a range per field (``build_column_filter_check``),
  and ``one_of`` with a single value only in a free-text filter, which
  the links rely on for contacts. A new kind of column filter has to
  touch them, too.
* The services filter tree embeds the hosts filter tree, which lives in
  ``cmk.gui.monitor.shared``, to filter services by their host, so a change to
  the host filters also reaches the services listing. A new host condition is
  only accepted there once ``validate_host_columns_only`` lets it in.
* ``cmk.gui.monitor.command``, and through it the monitoring tables of the
  dashboards, depends on the page types of ``cmk.shared_typing.monitoring``:
  which commands the backend offers is declared in the schema
  ``action_ident.json``, not in ``cmk.gui.monitor``. Adding a command to the
  pages starts with editing that schema. This is on purpose, because the
  list is a contract that neither side can change on its own, but it is the
  one place where the commands do not stay independent of the page
  transport.
