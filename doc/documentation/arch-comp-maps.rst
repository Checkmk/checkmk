====================
Checkmk Maps (maps)
====================

Introduction and goals
======================

Checkmk Maps shows live monitoring state on maps that users draw themselves:
static maps with a background image, world maps, radar views, flow/topology
graphs, folder trees and full-screen presentations. A map is a set of
*objects* (among others hosts, services, host and service groups, dynamic
groups, BI aggregations, links to other maps, lines, text boxes, images and
embedded graphs), each drawn with the state Checkmk currently knows for it.

Maps is split into five parts. The Python code lives in one package,
``packages/cmk-maps``; the browser application ships inside the regular
``cmk-frontend-vue`` bundle.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Part
     - What it does
   * - **Maps SPA**
     - The Vue application the user sees. It is shipped as the ``cmk-maps``
       web component inside ``cmk-frontend-vue`` (source:
       ``packages/cmk-frontend-vue/src/maps``) and mounted by the GUI page
       ``maps.py``.
   * - **GUI integration** (``cmk.maps.gui``)
     - Everything that needs Checkmk's application logic: storing maps,
       permissions, the settings page, monitoring commands, BI, metric
       display, image uploads, and minting the tickets the daemon accepts.
   * - **REST API** (``cmk.maps.rest_api``)
     - The HTTP endpoints the SPA uses to talk to the GUI integration: a public
       ``map`` family (create, read, update, delete maps) and an internal family
       for everything else.
   * - **Maps daemon** (``cmk.maps.backend``)
     - A FastAPI process inside the site. It fetches live states from
       Livestatus and streams them to the browsers that show a map. It has no
       write access to monitoring and imports no GUI code.
   * - **Shared layer** (``cmk.maps.shared``)
     - Plain Python both the GUI and the daemon import: the ticket protocol,
       config-variable names, URL/colour/asset validators, the map vocabulary,
       row extractors, state and severity tables, the geo resolver, the
       Livestatus filter allow-list and the perf-data parser.

Who should read what
--------------------

* For an overview, read this introduction, `Overview`_ and `Opening a map`_.
* Developers find the internal structure under `Architecture`_ and the
  interfaces with every endpoint under `Interfaces`_.
* Security reviews and penetration tests start with `Security concept`_. It
  lists the actors, trust boundaries, tokens, permissions, stored data, limits
  and the anonymous surface.

Glossary
--------

Map
  A Checkmk *pagetype* instance of type ``map``, stored per user like graph
  collections or dashboards. It has an owner, a name, a title, a visibility
  (private, published to all, to contact groups or to sites) and a
  specification (objects, view type, templates, …).
Built-in map
  One of five maps shipped in code (``all_hosts``, ``service_problems``,
  ``infrastructure``, ``monitoring_folders``, ``noc_wall``). Owner is the
  empty built-in user.
Session
  The normal Checkmk GUI login (session cookie). The SPA uses it for all calls
  to the GUI and the REST API.
Maps ticket
  A short-lived token the GUI signs for the logged-in user. The daemon accepts
  nothing else. It carries the user name and a set of capabilities.
Stream token
  A second, reduced ticket used only for the live state stream (SSE), because
  the browser's ``EventSource`` cannot send headers.
AuthUser
  The Livestatus header that makes Livestatus return only the hosts and
  services the named user is a contact for. It is the security boundary for
  monitoring data.
Connection
  A Livestatus endpoint the daemon queries: by default the local site (which
  also reaches all remote sites in a distributed setup), optionally further
  Livestatus endpoints configured in the Maps settings.
SSE
  Server-sent events: one long-lived HTTP response per browser tab over which
  the daemon pushes state changes.

Requirements overview
---------------------

* Live state for hundreds of objects per map, faster than a check interval.
  All viewers of a map share one poll loop; states arrive over SSE.
* Checkmk's security model must hold: role permissions, per-user
  contact-group visibility of hosts and services, and the publish permissions
  of pagetypes.
* Maps behave like other Checkmk pagetypes: per-user storage, built-in maps,
  publishing, and replication with Activate Changes.

Architecture
============

Overview
--------

The browser talks to three applications behind the site Apache: the GUI page
``maps.py``, the Checkmk REST API, and the Maps daemon; it also fetches static
images from the site and map tiles directly from the configured tile servers.
The GUI decides *who may see which map*; the daemon only delivers *live
states*, and Livestatus filters them per user (users with ``general.see_all``
see everything). The GUI and the daemon never call each other. They share only
the site-internal secret, with which the GUI signs tickets and map configs and
the daemon verifies them, and the files under ``etc/check_mk/maps.d/``, which
the GUI writes and the daemon reads.

.. uml::

    actor "User" as user
    [Browser\n(cmk-maps web component)] as spa
    [Site Apache] as apache
    [GUI pages\nmaps.py, maps_settings.py] as pages
    [REST API\n(cmk.maps.rest_api)] as rest
    [GUI integration\n(cmk.maps.gui)] as gui
    [Maps daemon\n(cmk.maps.backend)] as daemon
    () "unix socket\ntmp/run/maps.sock" as sock
    [Livestatus] as livestatus
    [cmk.bi] as bi
    folder "var/check_mk/web/<user>/\nuser_maps.mk" as mapstore
    folder "var/maps/images\nvar/maps/backgrounds" as files
    folder "etc/check_mk/maps.d/" as mapsd
    file "etc/site_internal.secret" as secret

    user --> spa
    spa ..> apache
    apache ..> pages : check_mk/maps.py\n(session)
    apache ..> rest : check_mk/api/{internal,unstable}/…\n(session)
    apache ..> sock : check_mk/maps/api/…\n(Maps ticket)
    apache ..> files : check_mk/maps/{images,backgrounds}\n(static, no login)
    pages ..> gui
    rest ..> gui : data providers
    sock - daemon
    gui ..> mapstore : read/write maps
    gui ..> files : uploads
    gui ..> mapsd : settings, folder\npermissions, site specs
    gui ..> secret : sign tickets\nand map configs
    gui ..> livestatus : commands, lookups\n(sites.live())
    gui ..> bi : BIManager
    daemon ..> secret : verify
    daemon ..> mapsd : read
    daemon ..> livestatus : AuthUser per query\n(none for see_all users)

Composition root
----------------

Maps plugs into the GUI as a ``GuiFeaturePlugin`` (``feature_plugin_maps`` in
``cmk.maps.registration``). ``cmk.gui.main_modules`` lists the module name
``cmk.maps.registration`` for each edition in ``_FEATURE_PLUGIN_MODULES`` and
hands it the registries it asks for. The editions' ``registration.py`` do not
call into Maps.

The OpenAPI spec generator is the one place in ``cmk.gui`` that imports Maps
directly: the edition modules under ``cmk/gui/openapi/spec/editions/`` register
the Maps permissions, ``MapPage`` and both endpoint families, so that the
generated spec contains them.

``cmk.maps.registration`` is also the only module of the package that
registers both halves of the feature, the GUI integration and the REST
endpoints. That is why it sits next to them rather than inside either: the REST
endpoints use the GUI integration, but ``cmk.maps.gui`` may not import
``cmk.maps.rest_api``.

Module layers
-------------

The five top-level modules of the package are separate components in
``module_layers.toml``, so the layering is enforced by a check rather than by
convention (abridged, the file is authoritative):

=========================  =====================================================
Component                  May import
=========================  =====================================================
``cmk.maps.shared``        ``cmk.ccc``, ``cmk.utils``. Kept minimal so that both
                           a GUI request and the daemon process can load it
                           (the code currently uses the standard library only)
``cmk.maps.backend``       ``cmk.ccc``, the Livestatus client, ``cmk.trace``,
                           ``cmk.crash``, ``cmk.utils``, ``cmk.maps.shared``
                           (and still ``cmk.bi``, which it no longer imports).
                           **No** ``cmk.gui``
``cmk.maps.gui``           ``cmk.gui`` internals, the Livestatus client,
                           ``cmk.bi``, the graphing engine, the plug-in APIs,
                           ``cmk.maps.shared``
``cmk.maps.rest_api``      ``cmk.gui`` (``openapi`` framework), ``cmk.maps.gui``,
                           ``cmk.maps.shared``
``cmk.maps.registration``  ``cmk.gui_plugins.internal``, ``cmk.maps.gui``,
                           ``cmk.maps.rest_api``
=========================  =====================================================

That ``cmk.maps.gui`` imports ``cmk.gui`` internals is not an exception granted
to Maps: there is no clean public ``cmk.gui`` API, and ``cmk.network_flow.gui``
is set up the same way.

Division of responsibility
--------------------------

The rule is simple: the **daemon owns data access and fan-out**, the **GUI owns
application semantics**. Anything that needs Checkmk's registries, the user's
permissions or the configuration lives in ``cmk.maps.gui`` and is reached over
the GUI session, as ordinary Checkmk REST endpoints.

* **Map CRUD** is the public ``map`` family (``APIVersion.UNSTABLE``, doc group
  *Monitoring*), so maps can be provisioned and version-controlled like any
  other Checkmk object. It applies the pagetype permission model (own, foreign,
  built-in) and ETag concurrency control.
* **Everything else the SPA asks Checkmk for** is the internal family
  (``APIVersion.INTERNAL``, doc group *Checkmk Internal*). It is not public API
  because its shapes follow what the SPA renders.
* **Metric display** (Perf-O-Meter, units, titles, graph groups) is computed
  with ``cmk.gui.graphing``, the same pipeline the monitoring views use. The SPA
  sends the raw ``perf_data`` and ``check_command`` it already has from the
  state stream.
* **BI aggregations** are resolved in the GUI with Checkmk's own
  ``cmk.gui.bi.bi_manager.BIManager``. The daemon does not touch BI; it skips
  ``aggregation`` objects in the state stream.
* **Monitoring commands** run with the user's session, never with a Maps
  ticket. The daemon has no write path into monitoring.

Consequently the daemon needs no ``cmk.gui`` imports and holds no user
database, no map store and no permission logic of its own. Everything it needs
to know about the user is baked into the ticket.

Interfaces
==========

This section lists every entry point. All paths are relative to
``/<site>/check_mk/``.

GUI pages
---------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Page
     - Required permission
     - Purpose
   * - ``maps.py``
     - ``maps.use``
     - Mounts the SPA. Hands it only the settings page URL and the
       breadcrumb; no map data. ``?kiosk`` and ``?preview`` hide the navigation (the
       latter is used by the live preview in the settings dialog); both still
       require login. Each load seeds the built-in icons into
       ``var/maps/images``.
   * - ``maps_settings.py``
     - Setup enabled, provider site, ``wato.use`` and ``maps.configure`` to
       view; ``wato.edit`` in addition to save
     - The Maps settings, rendered with Checkmk's global settings editor.

REST API
--------

The SPA calls ``api/internal/…`` through the shared ``lib/rest-api-client``.
The internal version is the highest one and inherits all endpoints of the lower
versions, so one base URL reaches both families. Authentication is the normal
GUI session cookie (``SameSite=Lax``). The REST API accepts automation-user
credentials as well, so these endpoints are not session-only. Every Maps handler
first requires ``maps.use``. The SPA's types come from the GUI's generated
OpenAPI types, not from hand-written copies.

**Public map family** (``api/unstable`` and above):

.. list-table::
   :header-rows: 1
   :widths: 10 35 55

   * - Method
     - Path
     - Checks and behaviour
   * - GET
     - ``domain-types/map/collections/all``
     - Lists the maps the user may see (``map.<name>`` checked per map).
   * - GET
     - ``objects/map/{name}``
     - Returns one map, including its **signed config** (``config_b64``,
       ``sig``) that the SPA hands to the daemon.
   * - POST
     - ``domain-types/map/collections/all``
     - Needs ``general.edit_map``. Name must match ``[a-zA-Z0-9_-]{1,100}``;
       409 if the caller already owns a map of that name (a built-in or
       another user's map of that name is shadowed, not refused). The requested visibility is clamped to what
       the user's publish permissions allow.
   * - PUT
     - ``objects/map/{name}``
     - Own map: needs ``general.edit_map``. Built-in map: needs
       ``general.edit_map`` and is saved as an own copy that shadows it.
       Foreign map: needs ``general.edit_foreign_map``. With ETag locking on
       (global setting, default) ``If-Match`` is required.
   * - DELETE
     - ``objects/map/{name}``
     - Own map: ``general.edit_map``; foreign map:
       ``general.delete_foreign_map``; built-ins never. Also deletes the map's
       background files.

**Internal family** (``api/internal`` only):

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Method
     - Path
     - Checks and behaviour
   * - GET
     - ``domain-types/maps_ticket/collections/all[?name=]``
     - Mints the Maps ticket. With ``name`` of a map the user may open, it also
       mints the stream token for that map. See `Authentication`_.
   * - POST
     - ``domain-types/maps_command/actions/run/invoke``
     - Monitoring commands Checkmk's REST API has no endpoint for. See
       `Monitoring commands`_.
   * - POST
     - ``objects/map/{name}/actions/upload-background/invoke``
     - Needs edit rights on the map. See `Handling untrusted input`_.
   * - POST
     - ``objects/map/{name}/actions/delete-background/invoke``
     - Needs edit rights on the map. Request has no body.
   * - POST
     - ``domain-types/map/actions/parse-cfg/invoke``
     - NagVis ``.cfg`` import, needs ``general.edit_map``. Returns an unsaved
       draft; nothing is stored until the user saves the map.
   * - GET
     - ``domain-types/maps_image/collections/all``
     - Lists the image library.
   * - POST
     - ``domain-types/maps_image/collections/all``
     - Uploads a library image, needs ``maps.configure``.
   * - GET
     - ``objects/maps_image/{name}/actions/usage/invoke``
     - Which maps use an image, needs ``maps.configure``.
   * - DELETE
     - ``objects/maps_image/{name}[?force=]``
     - Deletes a library image, needs ``maps.configure``. Built-in images
       cannot be deleted; an image in use needs ``force``.
   * - GET
     - ``domain-types/maps_settings/collections/all``
     - Authoring defaults and allowed tile sources.
   * - POST
     - ``objects/maps_form/{spec}/actions/{schema,parse}/invoke``
     - ``FormSpec`` schemas for the authoring dialogs and translation of their
       values (``map_metadata``, ``map_bulk_metadata``, ``flow_view``).
   * - POST
     - ``domain-types/maps_metric_info/actions/resolve/invoke``
     - Metric display semantics for perf data the SPA sends.
   * - GET / POST
     - ``domain-types/maps_aggregation/…`` (list, ``show-tree``,
       ``show-states``)
     - BI aggregations. See `BI aggregations`_.
   * - GET
     - ``objects/maps_host_geo/{host_name}``
     - Geo coordinates of a host.
   * - GET
     - ``domain-types/maps_perf_metrics/collections/all``
     - Available perf metrics of an object.
   * - GET
     - ``domain-types/maps_member/collections/{group,dyngroup}``
     - Members of a host/service group, or of a dynamic group defined by
       Livestatus filter lines.
   * - GET
     - ``domain-types/maps_folder/collections/all``
     - Setup folders the user may see.
   * - GET
     - ``domain-types/maps_site/collections/all``
     - Sites the user is authorized for.

All lookups that return monitoring data (geo, perf metrics, group members) run
through ``sites.live()`` under the user's Livestatus scope.

Maps daemon
-----------

The site Apache forwards ``check_mk/maps/api`` to the daemon's Unix socket
(``ProxyPass … flushpackets=on retry=0 timeout=3600``). The SPA uses the shared
``lib/fastapi-client``. Except for ``health``, every route needs a Maps ticket,
sent in the ``X-Maps-Ticket`` header (``Authorization: MapsTicket <ticket>`` is
accepted as well). The SSE route accepts only the stream token, in the
``?token=`` query parameter.

.. list-table::
   :header-rows: 1
   :widths: 8 37 55

   * - Method
     - Path (below ``maps/api``)
     - Checks and behaviour
   * - GET
     - ``health``
     - **No authentication.** Returns ``{"status":"ok"}``.
   * - POST
     - ``v1/maps/register``
     - Hands the daemon a map config to stream. See
       `Map configs in the daemon`_.
   * - GET
     - ``v1/maps/{name}/states``
     - Full state of all objects of a registered map.
   * - GET
     - ``v1/maps/{name}/auto-objects``
     - Hosts with geo coordinates for world maps that place hosts
       automatically.
   * - GET
     - ``v1/maps/{name}/folder-host-services``
     - Services of one host (folder-tree maps).
   * - GET
     - ``v1/maps/{name}/folder-search``
     - Service search in a folder-tree map.
   * - GET
     - ``v1/sse/maps/{name}?token=``
     - The live state stream (SSE).
   * - GET
     - ``v1/connections``
     - The configured connections. Needs ``may_edit`` or ``configure``;
       technical fields only with ``configure``, secrets never.
   * - GET
     - ``v1/connections/{id}/topology``
     - Parent/child topology for flow maps.
   * - GET
     - ``v1/connections/{id}/metric-history``
     - Metric time series for the object detail panel.
   * - GET
     - ``v1/connections/{id}/object-details``
     - Long output, groups, labels, comments and downtimes of one object.

Map names in paths must match ``[a-zA-Z0-9_-]{1,100}``. For a ticket bound to a
map (see `Authentication`_), the ``states``, ``folder-*`` and SSE routes must
name that map. The
daemon serves no OpenAPI schema, no ``/docs`` and no ``/redoc``.

Static files
------------

``check_mk/maps/images`` and ``check_mk/maps/backgrounds`` are plain Apache
``Alias`` es onto the GUI-owned directories ``var/maps/images`` and
``var/maps/backgrounds``. The daemon serves no files. See
`Unauthenticated surface`_ for who can fetch them.

* **Images** are the shared image library: the vendored Tabler icons plus icons
  uploaded by users with ``maps.configure``.
* **Backgrounds** belong to one map each. The file name is
  ``<sha256(owner)[:16]>__<map>.<random token><suffix>``. The token
  (``secrets.token_urlsafe(16)``) makes the URL unguessable, so the URL itself
  is the permission to fetch it.

Monitoring commands
-------------------

Commands always run with the user's GUI session and Checkmk's own permission
checks. The Maps ticket cannot trigger them.

* **Acknowledge, remove acknowledgement, schedule downtime, add comment** use
  Checkmk's regular REST endpoints (``domain-types/acknowledge``,
  ``domain-types/downtime``, ``domain-types/comment``). Single-object calls go
  to the page's own site, as does removing an acknowledgement. Group commands
  (host and service groups), the downtime list and downtime deletion go to
  ``api/1.0`` at the ``checkmk_url`` of the object's connection; only
  same-origin URLs work in practice, because the page's CSP allows
  ``connect-src`` only for ``'self'`` (and the Checkmk crash report server).
* **Reschedule check, enable/disable notifications, enable/disable active
  checks** have no Checkmk REST endpoint. Maps offers them through
  ``maps_command``. The endpoint requires ``general.act`` plus the verb's
  permission (``action.reschedule``, ``action.notifications``,
  ``action.enablechecks``), checks under the user's Livestatus scope that the
  target exists and is visible. That query runs only against the sites the
  user is authorized for, limited to the given site, so an unknown or
  unauthorized site is answered like an invisible target. The toggles require
  a site; a reschedule without one goes to
  the local site. These verbs should move to Checkmk's REST API once it offers
  them.

The ticket also lists the commands the user may run, but only so that the SPA
can hide menu entries. The daemon ignores this list.

BI aggregations
---------------

BI aggregations are resolved in the GUI request with ``BIManager`` (the same
compiler and computer the ``aggr`` views use), always against the local site's
compiled BI configuration. Aggregations are addressed by title. A user without
``general.see_all`` gets only the aggregations that contain at least one host
they can see; leaf states are fetched under the ``bi`` auth domain (no AuthUser
with ``bi.see_all``). Trees are returned up to depth 10.

Daemon to Livestatus and Checkmk
--------------------------------

* **Livestatus** is queried with ``cmk.livestatus_client``. The default
  connection ``cmk_<site>`` uses the local socket ``tmp/run/live``. In a
  distributed setup this connection fans out to all sites, using the site specs
  the GUI writes to ``etc/check_mk/maps.d/sitespecs.mk``. Further connections
  (Unix socket or TCP, optionally TLS) can be configured in the Maps settings.
* **Checkmk REST API**, only for metric history: if a connection has a
  ``checkmk_url``, an automation user and a secret, the daemon fetches metric
  series through ``api/1.0`` of that site with these credentials. It does so
  only after it has checked under the user's AuthUser that the object is
  visible. Without credentials it uses Livestatus ``rrddata`` columns, which are
  scoped by AuthUser anyway.

Configuration
-------------

All Maps settings live in one package-owned config domain, ``ConfigDomainMaps``
(like ``dcd`` or ``liveproxyd``: a standalone package owns its own domain). It
is edited on ``maps_settings.py`` (needs ``maps.configure``) and written to
``etc/check_mk/maps.d/wato/global.mk`` (``sitespecific.mk`` for site-specific
values). It holds:

* the connections (``maps_connections``),
* the daemon's log level and state refresh interval (1–300 s, default 5 s),
* the authoring defaults for new maps and objects, including the default
  tile server for world maps.

The directory is a registered replication path, so remote sites receive the
same settings with Activate Changes. The daemon ignores the keys it does not
use. It re-reads the refresh interval on every poll, but sets up the
connections and the log level only at start (see `Daemon lifecycle`_). The
connection list route re-reads the file on every request, so until a restart
it can differ from the connections actually in use.

The GUI writes two more files for the daemon:

* ``etc/check_mk/maps.d/wato/folder_perms.mk`` on every Activate Changes: path,
  title and permitted contact groups of every Setup folder, used to scope
  folder-tree maps.
* ``etc/check_mk/maps.d/sitespecs.mk`` when sites are saved and on Activate
  Changes: the Livestatus address of every enabled site (encoded socket,
  timeout, persistence, status host, proxy cache flag or TLS settings), without
  login secrets. It is empty for a single site, lies outside ``wato/`` and is
  not replicated.

Type generation
---------------

Neither side of the wire is typed by hand:

* The **daemon's** schema is dumped from ``create_app().openapi()``
  (``//packages/cmk-maps:openapi_spec``) and fed through the same
  ``openapi-typescript`` rule in ``cmk-shared-typing`` that produces the GUI's
  internal API types. Nothing is committed and nothing is served at runtime.
  The response model names of the daemon are therefore part of the SPA's type
  contract.
* The **REST API's** types come from the GUI's existing generated OpenAPI
  types.

Building the app needs no site or process state: ``app.py`` is a pure factory,
and everything that touches a running site (logging, tracing, crash reporting,
the start-up lifespan) lives in ``main.py``.

Security concept
================

This section is meant to be read on its own. It builds on the site-wide promise
in :doc:`sec-boundaries`.

What Maps promises
------------------

* A user sees only the maps Checkmk's pagetype rules let them see, and on any
  map only the monitoring data (states, output, metrics) of hosts and services
  they are a contact for (or of all of them with ``general.see_all``). The map
  configuration itself, including the object names the author placed, is
  visible to everyone the map is published to.
* A Maps ticket or stream token never grants more than its user already has in
  the GUI. A leaked stream token grants read access to one map for at most five
  minutes (plus up to 30 s on a stream that is already open).
* Monitoring data (plug-in output, aliases, labels, …) is data, not markup: a
  monitored host cannot inject active content into a map.
* The daemon cannot change monitoring or configuration. Commands run only with
  the user's GUI session.

Actors and default permissions
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Permission
     - Default roles
     - Grants
   * - ``maps.use``
     - admin, user, guest
     - Open Maps at all; required by ``maps.py``, every Maps REST endpoint and
       for minting tickets.
   * - ``maps.configure``
     - admin
     - Maps settings (view: with ``wato.use``; save: also ``wato.edit``),
       image library uploads and deletions, full connection details.
   * - ``general.edit_map``
     - admin, user
     - Create and edit own maps; register unsigned previews in the daemon.
   * - ``general.see_user_map``
     - admin, user, guest
     - See maps others published.
   * - ``general.publish_map``
     - admin, user
     - Publish to all users.
   * - ``general.publish_to_groups_map``
     - admin, user
     - Publish to own contact groups.
   * - ``general.publish_to_foreign_groups_map``
     - admin
     - Publish to any contact group.
   * - ``general.publish_to_sites_map``
     - admin
     - Publish to users of certain sites.
   * - ``general.force_map``
     - admin
     - Override built-in maps for everyone.
   * - ``general.edit_foreign_map``, ``general.delete_foreign_map``
     - admin
     - Edit or delete other users' maps.
   * - ``map.<name>``
     - admin, user, guest
     - One permission per published or built-in map name, shared by all maps
       of that name regardless of owner.
   * - ``general.act`` + ``action.*``
     - Checkmk defaults
     - Monitoring commands.
   * - ``general.see_all``
     - Checkmk defaults
     - See all hosts and services; the daemon then queries without AuthUser.
   * - ``wato.see_all_folders``
     - Checkmk defaults
     - See all Setup folders in folder-tree maps.

Besides human users there are two technical actors: **monitored hosts**, which
control the text Maps displays (output, alias, labels), and **remote sites** in
a distributed setup, whose Livestatus the daemon queries.

Trust boundaries
----------------

1. **Browser → site Apache.** Everything from the browser is untrusted. The GUI
   checks the session and permissions; the daemon checks the ticket.
2. **GUI → daemon (via the browser).** The GUI and the daemon never talk
   directly. The GUI signs tickets and map configs with
   ``etc/site_internal.secret``; the browser carries them to the daemon, which
   verifies the signature. The browser can therefore replay what it received,
   but cannot alter it.
3. **Daemon → Livestatus.** Livestatus enforces contact-group visibility for
   every query that carries ``AuthUser``. The daemon adds it from the verified
   ticket, never from request parameters.
4. **Monitored host → browser.** Host-controlled text reaches the SPA and is
   escaped before it is placed into any HTML template.
5. **Local socket.** ``tmp/run/maps.sock`` is mode 0660 (site user and group).
   The daemon still requires a ticket on every call except ``health``.

Authentication
--------------

**GUI and REST API** use the normal Checkmk session cookie (``SameSite=Lax``).
There is no separate CSRF token for REST calls. Endpoints with a body require
``Content-Type: application/json``, which a cross-site form cannot send;
bodyless POSTs (``delete-background``) rely on ``SameSite=Lax`` alone.

**The daemon** does no login, session or password handling of its own. It
accepts two token types, both minted by ``GET …/maps_ticket/collections/all``:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * -
     - Maps ticket
     - Stream token
   * - Used for
     - All daemon REST routes
     - Only the SSE route
   * - Sent as
     - ``X-Maps-Ticket`` header (``Authorization: MapsTicket …`` also
       accepted)
     - ``?token=`` query parameter
   * - Audience (``aud``)
     - ``maps-ticket``
     - ``maps-stream``
   * - Capabilities
     - All (see below)
     - Only ``see_all``, ``folder_see_all``, ``contact_groups``
   * - Bound to a map
     - Only if minted with ``?name=`` of a map the user may open
     - Always (only minted in that case)
   * - Lifetime
     - 300 s
     - 300 s

Both are ``base64url(canonical JSON).base64url(HMAC-SHA256)``, keyed with
``etc/site_internal.secret`` and compared in constant time. The payload holds
``aud``, ``v`` (1), ``sub`` (user name), ``exp``, ``caps`` and optionally
``map`` (owner and name). The daemon rejects a wrong audience, a wrong version,
an expired or missing ``exp``, and an empty ``sub``, so the stream token is
refused on every REST route and the ticket on the SSE route.

The SPA keeps both tokens in memory only (no browser storage) and re-mints them
every 240 s, on every map switch and at start. If minting fails with 401/403
(session expired), it redirects to the login page. The daemon re-checks the stream token of an open stream on every
wake-up and ends the stream at most 30 s after the token expired.

There is no nonce and no revocation list: a captured token can be replayed
until it expires, and a permission change or user deletion takes effect when
the current token expires (at most 5 minutes, plus up to 30 s on an open
stream). Rotating the secret invalidates
all tokens at once; the daemon picks up the new secret by file modification
time. If the secret file is missing, the crypto helper creates it.

Authorization
-------------

**Which maps a user may open** is decided in the GUI by Checkmk's pagetype
logic, not by Maps:

* A map is published to a user if the user has ``general.see_user_map`` and the
  map is public to all, or shares a contact group with the user, and the owner
  still holds a publish permission.
* For a map published by someone else, the user must also hold
  ``map.<name>``. Own maps need no such permission.
* Lookup order for a name is: own map, map forced by an admin, built-in map,
  map published by someone else.
* On create and update, the requested visibility is clamped to what the
  editing user may publish.

**Which capabilities a ticket carries** is derived from the user's permissions
when it is minted:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Capability
     - From permission
     - Used by the daemon for
   * - ``see_all``
     - ``general.see_all``
     - Querying without AuthUser
   * - ``folder_see_all``
     - ``wato.see_all_folders``
     - Folder scope of folder-tree maps
   * - ``contact_groups``
     - the user's contact groups
     - Folder scope of folder-tree maps
   * - ``may_edit``
     - ``general.edit_map``
     - Unsigned previews, connection list
   * - ``configure``
     - ``maps.configure``
     - Full connection details
   * - ``commands``
     - ``general.act`` + ``action.*``
     - Nothing (SPA menu only)
   * - ``publish_*``, ``all_contact_groups``, ``all_sites``
     - publish permissions
     - Nothing (SPA dialogs only)

**Which hosts and services a user sees** is decided by Livestatus. Every
daemon query carries ``AuthUser: <ticket sub>``, with two exceptions:

* Users with ``general.see_all`` are queried without AuthUser, as in the rest of
  the GUI.
* A background warm-up loop queries topology and host/service data every 60 s
  without AuthUser to keep connections warm. Its results are discarded, never
  sent to a client.

The ticket's contact groups are not used for Livestatus; they only scope the
Setup folder skeleton of folder-tree maps.

The ``connections/{id}/…`` routes accept any configured connection ID; access
to the data is still governed by AuthUser on that connection. For a connection
to a *foreign* Livestatus, the local user name is sent as AuthUser, so a user of
the same name on the foreign system determines what is visible.

Map configs in the daemon
-------------------------

The daemon stores no maps. Before opening a stream, the SPA registers the map's
config with ``POST v1/maps/register``. The daemon keeps registered configs in
memory (LRU, 1024 entries), keyed by the map's owner and name.

* **Signed config** (the normal case): the GUI signs a domain prefix
  (``maps-map-config:v2:``), the owner and the canonical config JSON (which
  contains the name). The daemon checks the signature against the owner from
  the ticket's ``map`` claim (or the caller, if the ticket is not bound to a
  map), and, for a bound ticket, that the config's name equals the ticket's map
  name. So a viewer can neither
  modify a config nor file one signed for another owner or map under a shared
  key.
* **Unsigned config** (editor preview): accepted only with ``may_edit``, only in
  the caller's own namespace, and only for the map the ticket is bound to (if
  any). It lets the editor preview unsaved changes.

**Shared poll loop.** All viewers of the same map (same owner and name) share
one broadcast loop. On each tick the loop groups its subscribers by AuthUser
(and, for folder-tree maps, by folder scope) and fetches once per group, so
viewers with different visibility never receive each other's data. A new
subscriber gets a full state once; everybody else receives changes only. A
subscriber whose queue (64 messages) overflows is disconnected and reconnects
with a fresh full state.

**Map links.** A map object that links to another map is resolved by name among
the registered configs. The linked states are fetched under the viewer's
AuthUser.

Handling untrusted input
------------------------

Monitoring data and templates
  Maps can show user-authored HTML templates on hover and in context menus,
  with placeholders like ``{{output}}``. Templates are stored as written; the
  server does not sanitize them. The SPA first HTML-escapes every value it
  inserts (``& < > " '``), then runs the result through ``sanitize-html`` with
  an allow-list (basic formatting tags, tables, links, images; attributes
  ``href``, ``class``, ``style``, plus ``src``, ``alt``, ``width``,
  ``height`` on images and ``target``, ``rel`` on links; a fixed set of CSS properties whose values
  may not contain ``url(``, backslashes or comments). Links get
  ``rel="noopener noreferrer nofollow"`` and ``target="_blank"``; images may
  only use relative (same-origin) sources. The template containers use
  ``contain: paint``, ``max-height: 40vh`` and ``overflow: auto`` so that a
  template cannot cover the map. Maps' own code renders HTML with ``v-html`` in
  exactly three places: the two template containers and static icon SVGs
  (shared UI components add their own, for server-provided help texts and
  icons).

URLs
  Object links, hover links, graph URLs, presentation images and tile URLs are
  validated on the server (``cmk.maps.shared.validators``): at most 4096
  characters, no control characters, no leading ``//``, schemes limited to
  http, https, mailto, tel, ssh, telnet, rdp, vnc and ftp. For ssh, telnet, rdp
  and vnc the user and host may not start with ``-`` and may not contain
  whitespace or ``%`` (so no options can be passed to the local handler). The
  link target is coerced to ``_blank`` or ``_self`` on the server.

  Before opening a link, the SPA checks again, but more narrowly: it normalizes
  the URL like the browser does, parses it and checks the scheme and the
  handler authority. Object icons and map backgrounds must be bare file names;
  presentation images may be URLs (http(s), ``data:``, ``blob:`` or a site
  path). Embedded graphs accept only http(s) or relative URLs and are shown as
  an image or, if the author chose so, in an iframe with
  ``sandbox="allow-scripts"`` (no ``allow-same-origin``).

Uploaded files
  Uploads are base64 in a JSON body; the size is checked before decoding.

  * Library images: PNG, JPEG, WebP or SVG, at most 2 MB, needs
    ``maps.configure``. Background images: additionally GIF, at most 10 MB,
    needs edit rights on the map.
  * The file is accepted only if its magic bytes match an allowed type. The
    stored suffix, and so the content type Apache serves, comes from the
    uploaded file name (``.png`` if it has no allowed suffix); it is not tied to
    the detected type. The file name is reduced to ``[A-Za-z0-9_-]``. Built-in names cannot
    be overwritten; other library images of the same name are replaced.
  * SVGs are parsed with ``defusedxml`` (no entities, no external references)
    and rejected, not rewritten, if they contain scripts, ``foreignObject``,
    ``iframe``/``object``/``embed``, animation elements, event-handler
    attributes, external CSS references, ``javascript:``/``vbscript:``/``file:``
    links, non-raster ``data:`` URIs, or external references in ``use``,
    ``image`` or ``feImage``.
  * Apache serves both directories with
    ``Content-Security-Policy: default-src 'none'; sandbox``, so even an SVG
    that slips through cannot run script when opened directly. For ``.png``
    and ``.jpg`` files the site-wide ``security.conf`` removes this header
    again.

NagVis import
  A ``.cfg`` file of at most 5 MB and 2000 objects is parsed into a draft. The
  draft is validated like any other map only when the user saves it.

Livestatus queries
  In the daemon, values from requests and map configs are passed through
  ``lqencode`` and, for searches, ``re.escape``; host names for world-map
  bundles are dropped if they contain a newline or backslash. The GUI builds
  its queries with Checkmk's query expression builder. Dynamic groups accept
  only ``Filter:``, ``And:``, ``Or:`` and ``Negate:`` lines without control
  characters (tab is allowed).

Stored data and secrets
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 32 20 48

   * - Path
     - Written by
     - Content and notes
   * - ``var/check_mk/web/<user>/user_maps.mk``
     - GUI
     - The user's maps, including templates. Replicated with the user
       profiles on the next Activate Changes (saving a map creates no pending
       change).
   * - ``var/maps/images/``
     - GUI
     - Image library. Not replicated.
   * - ``var/maps/backgrounds/``
     - GUI
     - Map backgrounds (capability URLs). Not replicated.
   * - ``etc/check_mk/maps.d/wato/global.mk``, ``sitespecific.mk``
     - Setup
     - Maps settings, including connections. An automation secret entered as
       an *explicit password* is stored here in plain text and replicated; a
       *stored password* is kept as a reference to the password store.
   * - ``etc/check_mk/maps.d/wato/folder_perms.mk``
     - GUI
     - Folder paths, titles and permitted contact groups. Replicated.
   * - ``etc/check_mk/maps.d/sitespecs.mk``
     - GUI
     - Livestatus addresses of all enabled sites, no secrets. Not replicated.
   * - ``etc/site_internal.secret``
     - site
     - The HMAC key for tickets and map configs (0600).
   * - ``var/check_mk/passwords_merged``
     - Checkmk
     - Read by the daemon for connection secrets taken from the password
       store.
   * - ``tmp/run/maps.sock``, ``tmp/run/maps.pid``
     - daemon
     - Socket (0660) and PID file.

The daemon reads the ``.mk`` files by executing them, the usual Checkmk way for
site-owned configuration.

Limits
------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - What
     - Limit
   * - SSE connection attempts
     - 30 per minute and user
   * - Concurrent SSE streams
     - 6 per user, 40 per site (the site Apache has 64 worker processes, and
       each open stream holds one)
   * - Daemon read routes (states, folder routes, topology, metric history,
       object details)
     - 240 per minute and user
   * - Register, auto-objects, connection list, health
     - Not rate-limited
   * - Registered map configs
     - 1024 (LRU)
   * - Objects per map
     - 5000 in the daemon; the REST model has no cap
   * - Metric history window
     - 1 minute to 7 days
   * - Livestatus query timeout
     - 30 s overall per query (socket timeout per connection, default 10 s),
       at most 20 concurrent queries per connection
   * - Uploads
     - 2 MB (library images), 10 MB (backgrounds), 5 MB (NagVis ``.cfg``)

The rate and stream limits are kept in the daemon's memory, per ticket user
(the 40 streams per site), and answered with HTTP 429. Too many objects are
rejected with 422 on register; the upload and import limits are checked by the
GUI (400). The map cache evicts silently.

HTTP security headers
---------------------

* The page ``maps.py`` uses Checkmk's standard page CSP and adds the tile servers to
  ``img-src``: OpenStreetMap and the host of the configured default tile server.
  A per-map tile URL on another host is therefore blocked by the browser. The
  standard CSP still allows inline script, so the template sanitizing above is
  the XSS defense, not the CSP. ``connect-src`` allows only ``'self'`` and the
  Checkmk crash report server. There is no ``frame-src``; frames fall back to
  ``default-src`` (the site's own origin plus ``ssh:`` and ``rdp:``).
* **Daemon responses** carry ``Content-Security-Policy: default-src 'none';
  img-src 'self' data:; style-src 'unsafe-inline'; sandbox``,
  ``Referrer-Policy: no-referrer``, ``X-Content-Type-Options: nosniff``,
  ``X-Frame-Options: SAMEORIGIN``, ``X-XSS-Protection: 1; mode=block``; the
  SSE stream also ``Cache-Control: no-cache``.
* **Static images and backgrounds** carry ``default-src 'none'; sandbox``
  (except ``.png`` and ``.jpg``, see `Handling untrusted input`_).
* The site-wide headers of ``etc/apache/conf.d/security.conf`` are added to all
  of them.

The settings dialog shows a live preview in a same-origin iframe. The two sides
exchange messages with ``postMessage`` and check both the origin and the source
window.

Logs, traces and crash reports
------------------------------

* The daemon writes ``var/log/maps/access.log`` and ``var/log/maps/error.log``.
* **The site Apache logs the full request line**, so the SSE stream token ends
  up in ``var/log/apache/access_log`` and ``var/log/apache/stats``, in
  ``omd backup`` archives, and, depending on its log configuration, in the
  access log of the system Apache in front of the site. That is why the stream token is read-only, bound to one map and
  short-lived.
* Tracing (OpenTelemetry via ``cmk.trace``, service name ``cmk-maps``) excludes
  the SSE route, so the token does not end up in spans. Other routes export
  their URL, including host and service names in query parameters.
* Unhandled exceptions become Checkmk crash reports in
  ``var/check_mk/crashes/maps/``. They contain the local variables of the
  innermost frame; values with sensitive-looking names are redacted.

Unauthenticated surface
-----------------------

With the site's default cookie authentication (``MULTISITE_COOKIE_AUTH=on``),
Apache lets every request under ``/<site>/check_mk`` through without Basic auth
and leaves authentication to the application. For Maps this means:

* ``check_mk/maps/api/health`` answers without a ticket; all other daemon routes
  answer 401 without one (404/405 for unknown paths).
* ``check_mk/maps/images/<file>`` is readable without login (no directory
  listing). Library file names are guessable.
* ``check_mk/maps/backgrounds/<file>`` is readable without login by anyone who
  knows the URL. The URL stays valid until the background is replaced or
  removed or the map is deleted. Browsers cache images for about a month.

Everything else needs a GUI session or a ticket. Switching the daemon off
(``omd config set MAPS off``) stops the daemon only; the Apache configuration,
the static files and the GUI pages stay in place.

Runtime view
============

Opening a map
-------------

.. uml::

    actor User
    participant "Browser (SPA)" as spa
    participant "GUI / REST API" as gui
    participant "Maps daemon" as daemon
    participant Livestatus as ls

    User -> spa : open maps.py
    spa -> gui : GET maps.py (session)
    spa -> gui : GET objects/map/{name}
    gui --> spa : map + signed config
    spa -> gui : GET maps_ticket/collections/all?name={name}
    gui --> spa : ticket + stream token (5 min)
    spa -> daemon : POST v1/maps/register (X-Maps-Ticket, signed config)
    daemon -> daemon : verify ticket and signature,\ncache config under (owner, name)
    spa -> daemon : GET v1/maps/{name}/states (X-Maps-Ticket)
    daemon -> ls : query with the user's AuthUser
    daemon --> spa : full state
    spa -> daemon : GET v1/sse/maps/{name}?token=…
    loop every refresh interval
        daemon -> ls : one query per subscriber group
        daemon --> spa : full state for new subscribers,\nchanges for everyone else
    end
    loop every 240 s
        spa -> gui : re-mint ticket + stream token
        spa -> daemon : reconnect stream
    end

The diagram shows a map opened from the map list. When a map is opened directly
by URL, the SPA mints the map-bound ticket first, at start, and then fetches the
map. A subscriber group is all viewers with the same AuthUser (for folder-tree
maps also the same folder scope); users with ``general.see_all`` are queried
without AuthUser.

A hidden browser tab closes its stream after five seconds and reopens it when
it becomes visible again. If the stream cannot be opened at all, the SPA falls
back to polling ``states`` every 15 s. SSE events carry no ID, so a reconnect
always starts with a fresh full state; the daemon keeps no per-client history.

Editing and saving a map
------------------------

When the user adds or removes objects, the SPA re-registers the edited config
unsigned with the daemon, so that new objects show their live state right away.
Moving objects or changing their properties does not trigger this. The daemon
accepts the unsigned config only for the user's own maps; while editing a
foreign or built-in map, the live preview of new objects fails.

Saving sends ``PUT objects/map/{name}``. The GUI validates the config against the REST
model, clamps the visibility and writes the owner's ``user_maps.mk`` under a
file lock. The daemon streams the saved version once its signed config is
registered again, at the latest when someone opens the map.

Running a command
-----------------

The user picks a command in an object's menu. The SPA sends it with the GUI
session: single-object acknowledgements, downtimes and comments to the REST API
of the page's own site, group commands and downtime listing/removal to the REST
API at the connection's ``checkmk_url``, and the remaining verbs to
``maps_command`` (see `Monitoring commands`_). Checkmk checks the permissions
and the target's visibility and hands the command to the monitoring core. The
SPA then re-fetches the states immediately and again 1.5 s later.

Daemon lifecycle
----------------

* ``omd config`` hook ``MAPS`` (default ``on`` in every edition). With ``off``,
  ``etc/init.d/maps`` exits without starting anything.
* ``etc/init.d/maps`` runs ``bin/cmk-maps-server``, which starts **gunicorn**
  with one **uvicorn worker** on ``tmp/run/maps.sock``
  (``etc/maps/gunicorn.conf.py``). Exactly one worker by design: SSE
  subscribers, broadcast loops, caches and rate limiters live in process
  memory. Blocking Livestatus calls run in threads (``asyncio.to_thread``).
  The daemon starts before Apache (``rc.d/84-maps``).
* At start the daemon applies the log level, activates the configured
  connections (or the built-in local one) and refuses to start if no connection
  could be set up. It does not test connectivity at start, so an unreachable
  Livestatus shows up only in the first queries.
  **Changes to connections or the log level take effect only after**
  ``omd restart maps``; Activate Changes does not restart the daemon.
* ``SIGHUP`` reloads gracefully, ``SIGUSR1`` reopens the log files (used by
  logrotate). Stop sends ``SIGTERM``, waits 35 s and then kills the process
  group.

Deployment view
===============

Packaging
---------

The package ships as one wheel (``//packages/cmk-maps:wheel``, containing
``backend``, ``gui``, ``rest_api``, ``registration``, the shared layer and the
built-in icons) plus an OMD package (``omd/packages/cmk-maps``): the skel files
(init script, gunicorn config, Apache drop-in, logrotate config), the
``rc.d/84-maps`` link, ``bin/cmk-maps-server`` and the ``omd config`` hook in
``lib/omd/hooks/MAPS``. Both are part of all five editions: community, pro,
ultimate, ultimatemt and cloud (see ``omd/BUILD``). Unlike NagVis, which is excluded from
cloud, Maps ships there too. The SPA ships inside the ``cmk-frontend-vue``
bundle; there is no separate frontend artifact.

Site integration
----------------

* **Apache drop-in** ``etc/apache/conf.d/00_maps.conf``: loads ``mod_proxy``
  and ``mod_proxy_http`` if needed, proxies ``check_mk/maps/api`` to the Unix
  socket, and adds the two ``Alias`` es with ``Options -Indexes``,
  ``Require all granted`` and the sandbox CSP. It contains no authentication
  directive of its own.
* **Site Apache** runs the prefork MPM with at most 64 worker processes. Every
  open SSE stream holds one of them, hence the stream limits above. The system
  Apache in front of the site proxies with a 120 s timeout; the daemon sends a
  keep-alive comment every 30 s so that open streams stay under it.
* **Logs** in ``var/log/maps/`` are rotated by OMD's logrotate (seven
  generations).

Developer deploy
----------------

``cmk-dev-deploy`` restarts the ``maps`` service and reloads Apache when it
deploys the wheel, so a developer deploy does not leave a stale daemon behind.
Changes to the skel files (Apache drop-in, init script) are not deployed by the
wheel.

Touchpoints in the core
=======================

Beyond the package itself, Maps adds or uses a few extension points in the
core, each generic rather than Maps-specific:

* ``GuiFeaturePlugin`` / ``RegistrationContext``
  (``cmk.gui_plugins.internal``) and the ``_FEATURE_PLUGIN_MODULES`` list in
  ``cmk.gui.main_modules``.
* The OpenAPI spec edition modules (``cmk/gui/openapi/spec/editions/``), which
  register the Maps permissions, ``MapPage`` and endpoint families.
* ``MonitorMenuTopicRegistry`` (``cmk.gui.sidebar``): feature modules
  contribute topics to the Monitor menu instead of the core menu builders
  importing them, like ``FolderMenuEntryRegistry`` /
  ``HostActionMenuRegistry``. The views snap-in and the reporting snap-in
  consume it.
* ``DomainType`` / ``CmkEndpointName`` literals
  (``cmk.gui.openapi.restful_objects.type_defs``): the new domain types and
  link relations.
* ``cmk.gui.graphing``: ``translated_names_and_scales`` is exported for the
  metric-info endpoint.
* ``cmk.gui.livestatus_utils.commands.force_schedule``: an optional
  ``site_id``, so a reschedule reaches the right site.
* ``cmk.gui.global_settings``: the settings page reuses the global settings
  editor (``central_settings``, ``render_settings_page``).
* GUI hooks: ``sites-saved`` writes ``sitespecs.mk``, ``pre-activate-changes``
  writes ``sitespecs.mk`` and ``folder_perms.mk``.

Risks and technical debts
=========================

* The daemon reads connections and the log level only at start. Changing them
  in the Maps settings needs ``omd restart maps``, and until then the
  connection list (read per request) and the active connections can differ.
* The single-worker model caps vertical scalability. Scaling out needs the
  process-local state (SSE subscribers, caches, rate limiters) to move behind a
  shared broker first. Each open stream also holds one of the 64 site Apache
  workers.
* The SSE stream carries no ``Last-Event-ID`` / ``retry:``. A reconnect is a
  cold start and the client reconverges from a full state. This is deliberate:
  the server keeps no per-client history, and a slow client is disconnected
  rather than silently left stale.
* Uploads are base64 in a JSON body (~33 % overhead). The REST framework has a
  seam for other media types, but nothing in the tree drives it yet. Worth
  revisiting once the framework grows a multipart path.
* The GUI normalizes the Livestatus site specs and writes them to
  ``sitespecs.mk`` (``cmk.maps.gui._sites``); the daemon only reads them back.
  The socket encoding reuses ``cmk.gui.sites.encode_socket_for_livestatus``
  (as the NagVis backend writer does). A small residual mirror remains:
  ``_for_livestatus`` sets the proxy-cache / TLS hint locally rather than
  widening the ``cmk.gui.sites`` API for this single caller.
* ``cmk.bi`` is still on the daemon's ``module_layers.toml`` allow-list,
  although the daemon no longer imports it.
* Map CRUD takes the Setup lock but writes no audit log entry and creates no
  pending change; a saved map reaches remote sites only when some other change
  is activated.

See also
========

* :doc:`sec-boundaries`: the site-wide security promise
* :doc:`arch-comp-nagvis`: the older map component
* :doc:`arch-comp-apache`: the site Apache
* ``packages/cmk-maps/README.md``: package overview and build commands
