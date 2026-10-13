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
* **Painters**: render the cells (see :doc:`arch-comp-painters-v1`).
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
``cmk.gui.common_registration``. Action menus and icons come from the same
icon registry that the classic views use, so both generations stay consistent.

The Vue applications share one base for all tables
(``MonitoringService``): it owns rows, search, filter, sorting, column
selection and the refresh timer. A page only supplies how to fetch its rows.
The page state (columns, sort, filter, opened row) lives in the URL, which
makes pages shareable. Actions use the existing command infrastructure through
the REST API.

Interfaces
----------

* GUI pages, registered as page endpoints (the page name is the URL):

  * Classic: ``view`` (``cmk/gui/views/page_show_view.py``).
  * Monitoring pages: ``monitor_all_hosts``
    (``cmk/gui/monitor/hosts/_pages/_monitor_all_hosts.py``) and
    ``monitor_host_services``
    (``cmk/gui/monitor/services/_pages/_monitor_host_services.py``).

* Internal REST endpoints below ``/monitor/`` (see the *Checkmk Internal*
  documentation of the REST API).
* Livestatus, locally or via :doc:`arch-comp-liveproxyd` for remote sites.

Coexistence
-----------

The classic views offer a link to the new pages and the new pages a link back.

Risks and technical debts
=========================

* Two implementations of the same pages have to be kept consistent until the
  classic views are replaced.
* Classic data sources are loosely typed (rows are dicts) and derive the
  queried columns at runtime, which makes it hard to see what is queried.
* The filter vocabulary of the monitoring pages is defined in the API, the
  Livestatus translation and the frontend. A change has to touch all three.
