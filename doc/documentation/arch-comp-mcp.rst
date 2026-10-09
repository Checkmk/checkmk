===================
MCP server (`mcp`)
===================

Introduction and goals
=======================

The MCP server exposes a Checkmk site to `MCP <https://modelcontextprotocol.io/>`_ clients (e.g. AI assistants), letting them query monitoring state -- hosts, services, events, downtimes, comments, config changes, metrics -- without a custom REST integration.

Requirements overview
----------------------
* Every tool call must run with the calling user's own Checkmk permissions -- never a shared internal identity.
* Tool errors and telemetry must never leak monitoring data or secrets.
* Adding a new tool must not require touching server plumbing.

Architecture
============

White-box overall system
-------------------------

.. uml::

    [MCP client] as client
    () HTTPS as https
    node "Site Apache" {
        [mod_proxy] as mod_proxy
        [REST API] as rest_api
        [oauth_introspect.py] as introspect
    }
    () "Unix socket (0700)" as socket
    [mcp-server] as mcp_server
    () "HTTP (loopback)" as loopback
    () "OTLP" as otlp
    [Local trace collector] as local_collector
    [mcp-analytics.checkmk.com] as analytics
    database "var/check_mk/crashes/mcp" as crashes

    client ..> https: use
    https - mod_proxy
    mod_proxy ..> socket: "/<site>/check_mk/mcp\n/.well-known/oauth-protected-resource/..."
    socket - mcp_server
    mcp_server ..> loopback: use
    loopback - rest_api
    loopback - introspect
    mcp_server ..> otlp: "TRACE_SEND"
    otlp - local_collector
    mcp_server ..> analytics: "MCP_TRACE_FORWARD (opt-in)"
    mcp_server ..> crashes: write

`cmk-mcp` is built on the official Python `mcp` SDK, major version 2.
It runs as a stateless streamable-HTTP MCP server with JSON responses (``stateless_http=True``, ``json_response=True`` in ``server.py``'s ``build_server``).
Apache proxies the public ``/<site>/check_mk/mcp`` URL onto the server's Unix socket, so clients talk to that URL directly.
That proxying is plain ``mod_proxy``/``mod_proxy_http``; the request body is not handled by the GUI's ``mod_wsgi`` application.
It still occupies a site Apache child process for the whole tool call (``ProxyPass ... timeout=120``), and every REST call the tool makes occupies another one, since the REST API is reached through the same site Apache over loopback HTTP.
See `Risks and technical debts`_.

Interfaces
----------

Inbound, both via the site Apache and the Unix socket:

* ``/<site>/check_mk/mcp``: the MCP endpoint, bearer-token protected (see `Authentication`_).
* ``/.well-known/oauth-protected-resource/<site>/check_mk/mcp``: the public RFC 9728 PRM document.

Outbound:

* **REST API** (``http://localhost:<apache port>/<site>/check_mk/api``): every tool's data access, with the caller's token forwarded.
* **Token introspection page** (``oauth_introspect.py`` on the same loopback base URL): one call per token not yet in the cache.
  The page itself is unauthenticated; it takes the token to check in the request body.
* **Local OTLP collector**, when the site's ``TRACE_SEND`` is on (see `Telemetry`_).
* **mcp-analytics.checkmk.com**, only when ``MCP_TRACE_FORWARD`` is on (see `Telemetry`_).
* **Crash reports** on disk, for unexpected tool exceptions (see `Error handling and failure modes`_).

The server has no other way in or out.

Which tool modules Bazel builds into the package is a build-time decision, driven by the ``srcs`` glob -- there's no runtime edition check inside the server itself.
If a tool ever needs restricting to specific editions, that becomes a change to a Bazel target, not to ``cmk.mcp``.
The tool catalogue is what an MCP client's ``tools/list`` returns; there is no separately maintained contract document.
See the package README for the tool-registration mechanics.

Runtime view
============

Authentication
--------------

.. uml::

    participant "MCP client" as client
    participant "mcp-server" as mcp
    participant "OAuth pages\n(cmk.gui.oauth)" as oauth
    participant "oauth_introspect.py" as introspect
    participant "REST API" as rest

    client -> mcp: POST /mcp (no token)
    mcp --> client: 401, WWW-Authenticate: resource_metadata=<PRM URL>
    client -> mcp: GET PRM document
    mcp --> client: authorization_servers=[{base}/oauth-{site}]
    client -> oauth: OAuth flow
    oauth --> client: access token
    client -> mcp: POST /mcp, Authorization: Bearer <token>
    alt token not cached
        mcp -> introspect: introspect token
        introspect --> mcp: active / inactive
    end
    mcp -> rest: REST call(s), Authorization: Bearer <token>
    rest --> mcp: data, as permitted for the token's user
    mcp --> client: tool result

The ``/mcp`` route requires a bearer token per `RFC 6750 <https://www.rfc-editor.org/rfc/rfc6750>`_.
A missing or unusable token gets a 401.
Its ``WWW-Authenticate`` challenge points at this site's `RFC 9728 <https://www.rfc-editor.org/rfc/rfc9728>`_ Protected Resource Metadata (PRM) document, which names the authorization server (the main repo's ``cmk.gui.oauth`` pages) an MCP client uses to obtain a token.
Tokens are checked against the site's `RFC 7662 <https://www.rfc-editor.org/rfc/rfc7662>`_ introspection endpoint.

Implementation specifics beyond what those RFCs mandate:

* **Locating this site's own PRM document.**
  The PRM route lives at a well-known, site-root-relative path, so Apache proxies it separately from ``/<site>/check_mk/mcp``.
  The site name is spliced into that path, so each site on a shared host gets its own document.
* **Building the PRM document's URLs per request.**
  The server only ever sees a request on a Unix socket, so it has no idea of its own public URL.
  ``_discovery.py`` reconstructs it per request from the reverse proxy's own headers: host from ``X-Forwarded-Host`` (client-most value, falling back to ``Host``), scheme from ``X-Forwarded-Proto`` (falling back to the request's own, plain ``http``).
  As with the GUI's secure-GUI requirement, a TLS-terminating proxy in front of Apache must set that header itself, or the PRM document's URLs silently fall back to ``http``.
  A host that fails validation gets a 400 on the PRM route and a 401 without ``resource_metadata`` on ``/mcp``.
* **A single-segment authorization server URL.**
  ``{base}/oauth-{site}`` rather than ``{base}/{site}/oauth``, because MCP clients don't reliably do `RFC 8414 <https://www.rfc-editor.org/rfc/rfc8414>`_ path insertion for multi-segment issuer paths.
* **Scopes.**
  The PRM document advertises ``read`` and ``write``, but the MCP server enforces neither.
  What a token may do is decided solely by its user's Checkmk permissions in the REST API.
* **Introspection caching.**
  An "active" answer is cached per process for 15 minutes under the token's SHA-256 hash.
  A rejection is never cached, and a REST call answering 401 drops the cached entry immediately.
  RFC 7662 defines the introspection call itself, not this caching policy.
* **Fail-closed introspection.**
  If the introspection call itself fails, the request gets the same 401 as an invalid token.
* **Authorization stays with the token's own user.**
  The token is forwarded as-is to every REST call a tool makes.
  The REST API resolves it to a specific Checkmk user and enforces that user's own permissions.
  No tool ever runs as a shared internal identity.

Error handling and failure modes
--------------------------------

* **Tool errors.**
  A caller-safe failure raises a ``ToolError`` subclass (``exceptions.py``).
  The client gets an ``isError`` result reading ``Error executing tool <name>: <caller_message>``, never ``str(exc)``.
* **Unexpected exceptions.**
  The client gets ``Error executing tool <name>: Unexpected error``.
  The server writes a crash report of type ``mcp`` (``crash_reporting.py``) with the tool name and exception class.
  Like any Checkmk crash report it also holds the traceback and the local variables of the failing frame, so it can contain monitoring data; it stays on the site until a user chooses to send it.
* **REST retries and timeouts.**
  Each REST call times out after 30 s (5 s to connect).
  Transport errors and 408, 429, 500, 502, 503 and 504 answers are retried, up to 3 attempts in total, with full-jitter backoff; ``Retry-After`` is honoured up to 10 s.
* **Remote sites.**
  A REST 403 "Setup is disabled" maps to its own error, so Setup-reading tools fail with a clear message on a remote site.
* **Shutdown.**
  uvicorn waits at most 30 s for in-flight requests on ``stop`` (``--timeout-graceful-shutdown 30``).

Telemetry
---------

``_tracing.py`` registers the site's OpenTelemetry tracer provider, so the spans the ``mcp`` SDK and the ASGI middleware create are recorded.
A span-enrichment middleware adds the calling client, the session id and the serialized response size.
The leak rule applies to every attribute: names, sizes, codes and timings only -- never request arguments or result content.

Spans go to up to two exporters:

* **Local**, when the site's ``TRACE_SEND`` is on, like any other site process.
* **Forward to Checkmk**, when ``MCP_TRACE_FORWARD`` ("Send MCP usage data to Checkmk") is on.
  This is the server's only off-site data egress.
  It exports to ``https://mcp-analytics.checkmk.com:54829`` with a bearer token hard-coded in ``_tracing.py``.
  The token only gates ingest at the collector: it carries no identity and grants no read access.
  A ``ForwardFilter`` passes only allowlisted span attributes, resource attributes and instrumentation scopes; anything an instrumentor or SDK upgrade adds is dropped by default.
  The allowlists are derived from ``telemetry_manifest.py``, which is the single description of the forwarded data.
  Host name and site id are deliberately not forwarded.

The server stays stateless, but ``SessionIdMiddleware`` (``_session_id.py``) mints an ``Mcp-Session-Id`` for requests that arrive without one.
The client echoes it back, so the forwarded spans can be correlated per session; the server never validates or expires it.

Deployment view
================

The service exists in the Pro, Ultimate, Ultimate MT and Cloud editions; Community doesn't ship ``cmk-mcp``.

``skel/etc/init.d/mcp-server`` (rc link ``85-mcp-server``) starts ``cmk.mcp.main:serve`` under uvicorn as the ``--factory`` entry point, bound to a Unix socket at ``tmp/run/mcp.sock``.
The init script pre-creates that socket with mode 0700, because uvicorn otherwise falls back to 0666 after binding.
So only processes running as the site user, including the site Apache, can connect to it.
The socket guards the server process; remote callers are authenticated by their bearer token.

Logging is configured via uvicorn's ``--log-config`` pointing at ``etc/mcp-server/log_config.json``.
It writes ``var/log/mcp-server.log`` through a ``RotatingFileHandler`` (20 MiB, 5 backups).
Output that bypasses Python logging lands in ``var/log/mcp-server-stderr.log``, which ``etc/logrotate.d/mcp-server`` rotates with ``copytruncate``.

The service is opt-in per site through the ``MCP_SERVER`` OMD hook, off by default.
The GUI exposes it, together with ``MCP_TRACE_FORWARD``, as a global setting in the "AI features" group, registered by ``cmk/mcp/gui/registration.py``.
The init script exits immediately if it is off.

The ``MCP_SERVER`` hook (``omd/packages/omd/omdlib/mcp.py``) writes ``etc/apache/conf.d/mcp.conf`` when turned on and removes it when turned off.
That file sets up both ``ProxyPass`` routes and lets CORS preflight (``OPTIONS``) requests through to the MCP endpoint and the PRM path, ahead of ``security.conf``'s general ``OPTIONS`` block.
The ``MCP_TRACE_FORWARD`` hook only stores the setting; the server reads it at startup.

Updates
-------

The MCP server keeps no persisted state of its own.
Hook names, setting idents, paths and URLs are unchanged since the first release (2.5.0p13).
``mcp.conf`` is regenerated by the hook on ``omd update`` and restored if the update fails.
The tool contract is experimental and may change between releases; clients re-list the tools on connect, so no client-side migration is needed.

Risks and technical debts
==========================

1. **Shared Apache workers.**
   Each in-flight tool call holds one site Apache child, plus one per concurrent REST call.
   Nothing in the server limits concurrency, so a few dozen concurrent tool calls can use up the site Apache's children and stall the GUI and the REST API with it.
2. **Whole-site fetches.**
   ``limit`` is applied after the REST response is fetched, and counts and the monitoring overview are computed in the server from every matching row.
   On large sites this means very large REST responses, parsed on the server's single event loop.
   The REST retries amplify this: a slow query that times out is run up to 3 times.
3. **Relaxed transport checks.**
   DNS-rebinding protection is off and CORS allows any origin.
   This is not exploitable, since authentication is an explicit bearer header rather than a cookie, but it deviates from the MCP transport spec's requirement to validate ``Origin``.
4. **Advertised but unenforced scopes.**
   See `Authentication`_.

See Also
========

* ``non-free/packages/cmk-mcp/README.md``: tool registration, REST client layering, and error/telemetry handling inside the server.
* :doc:`arch-comp-oauth`: the authorization server MCP clients are directed to.
* :doc:`arch-comp-agent-receiver`: another site-side service proxied by Apache over a Unix socket.
