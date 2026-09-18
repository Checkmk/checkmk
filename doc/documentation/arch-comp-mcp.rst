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
    [Apache] as apache
    [mod_proxy] as mod_proxy
    () "Unix socket" as socket
    [mcp-server] as mcp_server
    () HTTP as rest_http
    [Rest API] as rest_api

    client ..> https: use
    https - apache
    apache - mod_proxy
    mod_proxy ..> socket: use
    socket - mcp_server
    mcp_server ..> rest_http: use
    rest_http - rest_api

`cmk-mcp` is built on the official Python `mcp` SDK, major version 2.
It runs as a stateless streamable-HTTP MCP server (``stateless_http=True`` in ``server.py``'s ``build_server``).
Apache proxies the public ``/<site>/check_mk/mcp`` URL onto the server's Unix socket, so clients talk to that URL directly.
That proxying is plain ``mod_proxy``/``mod_proxy_http``, not the GUI's own ``mod_wsgi`` worker pool.
It forwards each request byte-for-byte over the socket, so MCP traffic never occupies a GUI application worker.
The Unix socket is the actual access boundary, not TLS.

Interfaces
----------

The server exposes exactly the two HTTP routes described under `Authentication`_ below, and talks only to this site's own REST API.
It has no other way in or out.

Which tool modules Bazel builds into the package is a build-time decision, driven by the ``srcs`` glob -- there's no runtime edition check inside the server itself.
If a tool ever needs restricting to specific editions, that becomes a change to a Bazel target, not to ``cmk.mcp``.
See the package README for the tool-registration mechanics.

Runtime view
============

Authentication
--------------

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
* **A single-segment authorization server URL.**
  ``{base}/oauth-{site}`` rather than ``{base}/{site}/oauth``, because MCP clients don't reliably do `RFC 8414 <https://www.rfc-editor.org/rfc/rfc8414>`_ path insertion for multi-segment issuer paths.
* **Introspection caching.**
  An "active" answer is cached for 15 minutes under the token's hash.
  A rejection is never cached, and a REST call answering 401 drops the cached entry immediately.
  RFC 7662 defines the introspection call itself, not this caching policy.
* **Authorization stays with the token's own user.**
  The token is forwarded as-is to every REST call a tool makes.
  The REST API resolves it to a specific Checkmk user and enforces that user's own permissions.
  No tool ever runs as a shared internal identity.

Deployment view
================

``skel/etc/init.d/mcp-server`` starts ``cmk.mcp.main:serve`` under uvicorn as the ``--factory`` entry point, bound to a Unix socket under ``tmp/run/mcp.sock``.
Logging is configured entirely via uvicorn's ``--log-config`` pointing at ``etc/mcp-server/log_config.json``.
The service is opt-in per site (``CONFIG_MCP_SERVER``, exposed as a GUI setting in ``cmk/gui/mcp``).
The init script exits immediately if it is off.

Risks and technical debts
==========================

1. The mcp-server log file grows unbounded -- nothing wires up a logrotate entry for it yet.

See Also
========

* ``non-free/packages/cmk-mcp/README.md``: tool registration, REST client layering, and error/telemetry handling inside the server.
* :doc:`arch-comp-oauth`: the authorization server MCP clients are directed to.
* :doc:`arch-comp-agent-receiver`: another site-side service proxied by Apache over a Unix socket.
