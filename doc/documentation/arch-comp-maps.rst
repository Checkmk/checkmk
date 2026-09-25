====================
Checkmk Maps (maps)
====================

Introduction and goals
======================

Checkmk Maps renders live monitoring state on user-authored maps (static
maps, world maps, radar, flow/topology, folder trees, presentations). Its
Python vertical is one package, ``packages/cmk-maps``; the SPA ships inside
the regular ``cmk-frontend-vue`` bundle. The parts are:

* the **Maps SPA**: a Vue application shipped as the ``cmk-maps`` web
  component inside ``cmk-frontend-vue``, mounted inline by the GUI page
  ``maps.py``,
* the **GUI integration** (``cmk.maps.gui``): map storage, permissions,
  configuration, monitoring commands and the data providers behind the REST
  endpoints — everything that needs Checkmk application semantics,
* the **REST API** (``cmk.maps.rest_api``): the versioned endpoints the SPA
  talks to — a public ``map`` CRUD family plus an internal family carrying
  every read-only lookup,
* the **Maps daemon** (``cmk.maps.backend``): a FastAPI site daemon that
  streams live object state and serves monitoring data,
* the **shared domain layer** (``cmk.maps.shared``): the pure GUI↔daemon
  code both sides import — ticket protocol, config-variable names, row
  extractors, state/severity maps, geo resolver, filter allow-list, perf-data
  parser.

Requirements overview
---------------------

* Live state for hundreds of objects per map with sub-check-interval
  latency (server-sent events, shared per map across viewers).
* Checkmk's security model must hold: RBAC, per-user contact-group
  visibility, publish permissions for maps.
* Maps are Checkmk pagetypes: per-user storage, builtin maps, publishing
  and Activate-Changes replication like graph collections or dashboards.
* Maps written by the pre-in-tree, file-based daemon must survive an update
  (see `Deployment view`_).

Architecture
============

Composition root
----------------

Maps plugs itself into the GUI as a ``GuiFeaturePlugin``
(``cmk.maps.registration``) that ``cmk.gui.main_modules`` discovers by name
and hands the registries it asks for, rather than being called from each
edition's ``registration.py``. So ``cmk.gui`` needs no import of the feature,
and each edition gets Maps by depending on the wheel alone.

``cmk.maps.registration`` is also the only module that sees both halves of the
feature — the GUI integration and the REST endpoints — which is why it sits
next to them rather than inside either: neither half may import the other.

Module layers
-------------

The package's five top-level modules are separate components in
``module_layers.toml``, so the layering is enforced rather than conventional
(abridged — the file is authoritative):

=========================  =====================================================
Component                  May import
=========================  =====================================================
``cmk.maps.shared``        ``cmk.ccc``, ``cmk.utils`` — deliberately minimal, so
                           that both a GUI request and a daemon process can hold
                           it
``cmk.maps.backend``       ``cmk.ccc``, the Livestatus client, ``cmk.trace``,
                           ``cmk.crash``, ``cmk.utils``, ``cmk.maps.shared`` —
                           **no** ``cmk.gui``
``cmk.maps.gui``           ``cmk.gui`` internals, the Livestatus client,
                           ``cmk.bi``, the graphing engine, the plug-in APIs,
                           ``cmk.maps.shared``
``cmk.maps.rest_api``      ``cmk.gui`` (``openapi`` framework), ``cmk.maps.gui``,
                           ``cmk.maps.shared``
``cmk.maps.registration``  ``cmk.gui_plugins.internal``, ``cmk.maps.gui``,
                           ``cmk.maps.rest_api``
=========================  =====================================================

That ``cmk.maps.gui`` imports ``cmk.gui`` internals is not an exception granted
to Maps: there is no clean ``cmk.gui`` public API, and ``cmk.network_flow.gui``
sits the same way.

Division of responsibility
--------------------------

The daemon owns **data access and fan-out**; the GUI owns **application
semantics**. Anything that needs Checkmk's registries or user context lives in
``cmk.maps.gui``, and the SPA reaches it over the GUI session. Wherever the
versioned REST framework can carry that traffic, it does — these are ordinary
Checkmk REST endpoints, not maps-private plumbing:

* **map CRUD** — the public ``map`` family (``APIVersion.UNSTABLE``, doc group
  *Monitoring*, so maps can be provisioned and version-controlled like any other
  Checkmk object): list, show, create, update, delete against the pagetype
  store, with the pagetype permission model (own / foreign / built-in) applied
  by name and ETag concurrency,
* **everything else the SPA asks Checkmk for** — the internal family
  (``APIVersion.INTERNAL``, doc group *Checkmk Internal*, not part of the public
  API because the shapes track what the SPA renders): the ticket handshake (see
  `Interfaces`_), monitoring-object lookups (objects, folders, sites, host-group
  and dynamic-group members, host geo coordinates, available perf metrics), the
  image library with its uploads and per-image usage, a map's background image,
  the authoring defaults, the ``FormSpec`` schemas for the authoring dialogs and
  the translation of their values, the NagVis ``.cfg`` import, and the
  monitoring commands Checkmk's REST API does not offer (rescheduling a check,
  switching notifications and active checks),
* **metric display semantics** —
  ``/domain-types/maps_metric_info/actions/resolve/invoke``: Perf-O-Meter
  rendering, registered units and titles, applicable graph groups — computed
  with ``cmk.gui.graphing``, the same pipeline the monitoring views use. The
  SPA sends the raw ``perf_data``/``check_command`` it already holds from the
  state stream,
* **BI aggregations** — ``/domain-types/maps_aggregation/…`` (discovery,
  ``show-tree``, ``show-states``), resolved GUI-side through Checkmk's own
  ``cmk.gui.bi.bi_manager.BIManager`` (compiler + computer). The daemon does
  not touch BI at all; it skips ``aggregation`` objects in the state stream.

``maps.py`` is the one page Maps registers: it mounts the SPA and hands it the
Checkmk URLs the app links out to. Everything else is a REST endpoint reached
through the generated, typed client — there is no AjaxPage leg.

Two consequences of that are worth naming. Uploads (icons, map backgrounds, a
NagVis ``.cfg``) carry their file base64-encoded in the JSON body, because
nothing in the tree drives the framework's seam for other request media types
yet and every Maps upload is small and capped. And the monitoring commands go
to Checkmk's own REST API (``api/1.0``: ``domain-types/acknowledge``,
``domain-types/downtime`` and ``domain-types/comment``), for one object as for a
whole group. Only the verbs without such an endpoint stay with Maps: they run in
a full Checkmk request through Checkmk's command layer, with real permissions,
the target's visibility checked and explicit site scoping. They belong into the
Monitor endpoint family, whose reschedule does not check that visibility yet.

The daemon consequently needs no ``cmk.gui`` imports at all, and no write path
into monitoring: commands ride the GUI session, never the maps ticket.

White-box overall system
------------------------

.. uml::

    [Browser (cmk-maps web component)] as spa
    [Site Apache] as apache
    [REST API (cmk.maps.rest_api)] as rest
    [GUI (cmk.maps.gui)] as gui
    [Maps daemon (cmk.maps.backend)] as daemon
    () "unix socket tmp/run/maps.sock" as sock
    [Livestatus] as livestatus
    [cmk.bi] as bi

    folder "var/maps (GUI-owned files)" as files

    spa ..> apache
    apache ..> rest : /<site>/check_mk/api/internal/...\n(session auth)
    apache ..> gui : /<site>/check_mk/maps.py\n(session auth)
    apache ..> sock : /<site>/check_mk/maps/api\n(ticket auth)
    apache ..> files : /<site>/check_mk/maps/{images,maps}\n(static Alias)
    rest ..> gui : data providers
    sock - daemon
    daemon ..> livestatus : cmk.livestatus_client,\nAuthUser per query
    gui ..> livestatus : sites.live() (commands)
    gui ..> bi : BIManager\n(aggregation discovery/state)

Interfaces
----------

* **SPA → REST API**: ``/<site>/check_mk/api/internal/…`` through the shared
  ``lib/rest-api-client`` — session cookie + CSRF like every other GUI page. The
  internal version is the highest one and inherits every lower version's
  endpoints, so this one root reaches both families. Domain types ``map``
  (public) and ``maps_aggregation``, ``maps_command``, ``maps_folder``,
  ``maps_form``, ``maps_host_geo``, ``maps_image``, ``maps_member``,
  ``maps_metric_info``, ``maps_perf_metrics``,
  ``maps_settings``, ``maps_site``, ``maps_ticket`` (internal). The SPA's types
  for them come from the GUI's generated OpenAPI types, not from hand-written
  mirrors.
* **SPA → GUI page**: ``/<site>/check_mk/maps.py`` — the page that mounts the
  SPA, and the only GUI page Maps registers.
* **SPA → static files**: ``/<site>/check_mk/maps/images`` and
  ``/<site>/check_mk/maps/maps/backgrounds`` are plain Apache ``Alias`` es onto
  GUI-owned files under ``var/maps/`` (``cmk.maps.gui._images``) — the daemon
  does not serve files. Backgrounds carry an unguessable token in the filename,
  so the URL is a capability.
* **SPA → daemon**: ``/<site>/check_mk/maps/api/v1/…`` behind the site Apache
  (``ProxyPass`` to the Unix socket, SSE unbuffered), through the shared
  ``lib/daemon-client``. The routes are ``maps/register``,
  ``maps/{name}/states``, ``maps/{name}/auto-objects``,
  ``maps/{name}/folder-host-services``, ``maps/{name}/folder-search``, the
  connection routes (``topology``, ``metric-history``, ``object-details``) and
  the SSE stream ``sse/maps/{name}``. Authentication is a GUI-minted HMAC
  ticket (``etc/site_internal.secret``); the user's capabilities and contact
  groups are baked in when the ticket is minted, the daemon never re-derives
  RBAC. Map configs are GUI-signed with the map's ``(owner, name)`` bound into
  the signature; the daemon verifies it against the owner from the ticket
  before trusting a config, so a viewer can neither tamper with a config nor
  relay one signed for a foreign owner into a shared loop.
* **Two token channels (audience-bound)**: REST calls carry the full-capability
  ticket in the ``X-Maps-Ticket`` *header*. The SSE stream instead carries a
  separate token in the ``?token=`` *query string*, because ``EventSource``
  cannot set headers. A query string lands in access logs — the site Apache's
  own ``combined``/``stats`` logs included, and from there in ``omd backup`` — so
  this stream token is minted with only the read/scope caps (no
  commands / publish / edit / configure), is bound to a single map, and lives
  under its own audience (``maps-stream`` rather than ``maps-ticket``). The
  daemon rejects it on every REST endpoint and rejects the header ticket on the
  SSE endpoint (audience mismatch), so a captured URL token can neither drive
  the API nor escalate privilege — it grants no more than the read access the
  user already had to that one map. Both live 5 minutes; the SPA re-mints them
  on one timer well inside that.
* **daemon → Livestatus**: ``cmk.livestatus_client``. Single-site setups use
  the local socket; distributed setups fan out via the prepared specs the GUI
  writes to ``etc/check_mk/maps.d/sitespecs.mk``. Every query carries
  ``AuthUser:`` from the ticket — Livestatus itself enforces contact-group
  visibility; this is the security boundary.
* **GUI → BI**: BI aggregations are resolved in the GUI request context via
  ``cmk.gui.bi.bi_manager.BIManager`` (the same compiler/computer the ``aggr``
  views use) and handed to the SPA over the ``maps_aggregation`` endpoints. The
  daemon has no BI path.
* **Configuration**: all Maps globals live in one package-owned config domain
  ``ConfigDomainMaps`` (like ``dcd``/``liveproxyd`` — a standalone package owns a
  single domain, not a split off ``ConfigDomainGUI``). WATO writes them to
  ``etc/check_mk/maps.d/wato/``. It holds both the daemon-facing settings
  (connections, log level, refresh interval) and the GUI-only authoring defaults
  (map/object defaults); the daemon reads the file per request — no reload signal
  needed — and simply ignores the keys it does not consume. The domain's config
  dir is a registered replication path, so remote sites' daemons read the same
  settings. Distributed-setup Livestatus site specs are written separately by
  ``cmk.maps.gui._sites`` to ``etc/check_mk/maps.d/sitespecs.mk``.

Type generation
---------------

Neither side of the wire is typed by hand:

* the **daemon's** schema is dumped from ``create_app().openapi()``
  (``//packages/cmk-maps:openapi_spec``) and fed through the same
  ``openapi-typescript`` rule in ``cmk-shared-typing`` that produces the GUI's
  internal API types. Nothing is committed and nothing is served at runtime —
  the daemon's ``openapi_url`` stays ``None``, because the site Apache exempts
  the whole ``/maps`` prefix from Basic auth and only ``/api/v1/*`` is
  ticket-guarded, so a served schema would be anonymous.
* the **REST API's** types come from the GUI's existing generated OpenAPI
  types.

Building the app is therefore free of site and process state: ``app.py`` is a
pure factory, and everything that touches a running site (logging, tracing,
crash reporting, the startup lifespan) lives in ``main.py``.

Runtime view
============

* ``omd config`` hook ``MAPS`` (on/off); ``etc/init.d/maps`` starts
  **gunicorn** with a **uvicorn worker** on the Unix socket. Exactly one
  worker by design: SSE subscribers, map broadcast loops and Livestatus
  caches are process-local. Blocking work runs via ``asyncio.to_thread``.
* The SPA registers a map's signed config with the daemon
  (``POST maps/register``) before opening its stream; the daemon stores no map.
* One shared broadcast loop per map (keyed by the map's owner + name from
  the signed ticket) serves every viewer of that map.
* Logs: ``var/log/maps/{access,error}.log`` (gunicorn, rotating). The daemon's
  own access log omits query strings, but the site Apache in front of it does
  not — its ``combined`` format logs the full request line, so the SSE
  ``?token=`` is recorded in ``var/log/apache/access_log``. That is why the URL
  token is audience-bound and minimal-scope (see the two token channels above):
  a logged token grants no API access and no more read access than its bearer
  already had. ``SIGHUP`` reloads gracefully, ``SIGUSR1`` reopens logs.
* Unhandled request exceptions are stored as Checkmk **crash reports**
  (``var/check_mk/crashes/maps/``). Tracing is wired into Checkmk's
  OpenTelemetry setup (``cmk.trace``, FastAPI instrumentation), service name
  ``cmk-maps``.

Deployment view
===============

The package ships as one wheel (``//packages/cmk-maps:wheel``, bundling
``backend``, ``gui``, ``rest_api`` and the shared layer) plus an OMD skel tar
(init script, gunicorn config, Apache drop-in, logrotate), wired into all five
editions — community, pro, ultimate, ultimatemt and cloud (see ``omd/BUILD``).
Unlike NagVis, which is excluded from cloud, Maps ships there too. The SPA ships
inside the ``cmk-frontend-vue`` bundle; there is no separate frontend artifact.

``cmk-dev-deploy`` knows the wheel restarts the ``maps`` service, so a developer
deploy of the package does not leave a stale daemon behind.

On update, ``cmk.update_config.plugins.actions.maps`` imports the legacy
file-based maps (``var/maps/maps/<name>.json``, one global namespace, no owner)
into the pagetype store as maps owned by the site admin and published to all,
preserving their previous everyone-can-see visibility. It is best-effort and
idempotent, like the NagVis ``.cfg`` import: every source file is validated
against the REST model and then renamed away from ``*.json``, so a re-run only
sees what still needs attention, and anything unreadable, invalidly named or
colliding with an existing or built-in map is kept as ``*.failed`` /
``*.skipped`` with a warning rather than silently dropped or written over.

Touchpoints in the core
=======================

Beyond the package itself, Maps adds a small number of extension points to
``cmk.gui`` — each one generic rather than maps-specific:

* ``MonitorMenuTopicRegistry`` (``cmk.gui.sidebar``): feature modules
  contribute topics to the Monitor main menu instead of the core menu builders
  importing them, mirroring ``FolderMenuEntryRegistry`` /
  ``HostActionMenuRegistry``.
* ``GuiFeaturePlugin`` / ``RegistrationContext``
  (``cmk.gui_plugins.internal``): extended with the registries Maps needs.
* ``DomainType`` / ``CmkEndpointName`` literals
  (``cmk.gui.openapi.restful_objects.type_defs``): the new domain types and
  link relations.
* ``cmk.gui.graphing``: ``translated_names_and_scales`` exported for the
  metric-info endpoint.

Risks and technical debts
=========================

* The GUI normalises the Livestatus site specs and writes them to
  ``etc/check_mk/maps.d/sitespecs.mk`` (``cmk.maps.gui._sites``); the daemon
  (``integrations/checkmk_sites.py``) only reads them back, so there is no
  duplicated normalisation in the daemon. The proxy/OMD-specific socket encoding
  — the part most prone to drift — reuses the public
  ``cmk.gui.sites.encode_socket_for_livestatus`` helper (the same one the NagVis
  backend writer uses). A small residual mirror remains: ``_for_livestatus``
  still sets the proxy-cache / TCP-tls hint locally rather than widening the
  ``cmk.gui.sites`` API for this single caller.
* The single-worker model caps vertical scalability; scaling out needs the
  process-local state (SSE subscribers, caches) to move behind a shared
  broker first.
* The SSE stream carries no ``Last-Event-ID`` / ``retry:`` replay: a reconnect is
  a cold start, and the client reconverges from a full resend rather than
  replaying missed events. This is deliberate — the server keeps no per-client
  event history — and covers both cases that end a stream: a client that drops
  and reconnects, and a client that falls so far behind that its bounded per-
  subscriber queue overflows (the daemon then ends that one stream so the browser
  reconnects). On (re)join the server sends only that client a full state built
  from the shared tick's fetch — established viewers keep receiving deltas — so a
  reconnect never re-fulls the whole group, and a slow client is never left
  permanently stale by silently dropped deltas.
* Tickets and the URL stream token carry an expiry but no per-use nonce, so a
  captured token is replayable until it expires (≤ 5 min). The window is bounded
  by the short TTL and narrowed by the mitigations already in place: responses
  set ``Referrer-Policy: no-referrer``, and the URL stream token is read-only and
  bound to a single map. It is *not* narrowed by log hygiene — the site Apache
  logs the query string (see `Runtime view`_), so anyone who can read
  ``var/log/apache/`` or a site backup can replay a stream token within its TTL.
  A ``jti`` + server-seen cache, or moving the stream off ``EventSource`` so the
  token can travel in a header, would close the residual window if a threat model
  requires it.
* Uploads (icons, map backgrounds, a NagVis ``.cfg``) carry their file
  base64-encoded in a JSON body. The versioned framework has a seam for other
  request media types, but nothing in the tree drives it yet; every Maps upload
  is small and capped, so the ~33% encoding overhead buys the typed JSON model.
  Worth revisiting once the framework grows a multipart path.
* ``cmk.bi`` is still on the daemon's ``module_layers.toml`` allow-list although
  the daemon no longer imports it; BI moved GUI-side.
