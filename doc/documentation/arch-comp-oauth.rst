====================================
OAuth authorization server (`oauth`)
====================================

Introduction and goals
=======================

Checkmk's site GUI hosts its own OAuth 2.1 authorization server, letting other site components hand a caller a token scoped to that caller's own Checkmk permissions, rather than a shared credential.
Today the only OAuth-consuming feature is the MCP server; see :doc:`arch-comp-mcp` for how a caller reaches this server in the first place.

Requirements overview
----------------------
* An issued token must never grant more than the approving user's own Checkmk permissions.
* The whole surface (metadata, authorization, registration, token, introspection) must 404 while no OAuth-consuming feature is enabled for the site.
* Registering a client must not require any manual admin step, so a new MCP client can be used immediately.

Architecture
============

White-box overall system
-------------------------

.. uml::

    [OAuth client] as client
    () HTTPS as https
    [Apache] as apache
    [oauth pages] as oauth_pages
    () SQLite as sqlite
    () Redis as redis

    client ..> https: use
    https - apache
    apache - oauth_pages
    oauth_pages ..> sqlite: use
    oauth_pages ..> redis: use

The authorization server is a set of unauthenticated GUI pages (``cmk.gui.oauth``), reached through the same Apache that serves the rest of the site.
Registered clients and issued tokens are durable state in a SQLite database (``var/oauth/db.sqlite3``).
Short-lived, single-use authorization codes live in Redis instead, since they only need to survive the few minutes of a redirect round-trip.

Interfaces
----------

Five endpoints, all gated behind the same ``enabled`` predicate (404 while off):

* ``GET /oauth-<site>/.well-known/oauth-authorization-server`` -- `RFC 8414 <https://www.rfc-editor.org/rfc/rfc8414>`_ metadata, unauthenticated.
* ``/authorize`` (``GET``, ``POST``) -- `RFC 6749 <https://www.rfc-editor.org/rfc/rfc6749>`_ section 3.1 authorization endpoint; requires an active Checkmk GUI session.
* ``POST /register`` -- `RFC 7591 <https://www.rfc-editor.org/rfc/rfc7591>`_ dynamic client registration, unauthenticated.
* ``POST /token`` -- `RFC 6749 <https://www.rfc-editor.org/rfc/rfc6749>`_ section 3.2 token endpoint, unauthenticated.
* ``POST /introspect`` -- `RFC 7662 <https://www.rfc-editor.org/rfc/rfc7662>`_ introspection endpoint, unauthenticated and not advertised in the metadata document, since it is reachable only over the loopback trust boundary (this is the endpoint :doc:`arch-comp-mcp` calls).

The "Registered clients" Setup page for reviewing or deleting a client's registration is always available, independent of ``enabled``.

Runtime view
============

Authorization
-------------

A client first registers via `RFC 7591 <https://www.rfc-editor.org/rfc/rfc7591>`_ dynamic registration, then obtains a token through `RFC 6749 <https://www.rfc-editor.org/rfc/rfc6749>`_'s authorization code grant with `RFC 7636 <https://www.rfc-editor.org/rfc/rfc7636>`_ PKCE (S256 only).
The consent screen at ``/authorize`` runs inside the user's own logged-in session.
The code, and later the token, bind the scope the user selected there, not the scope the client requested.

Implementation specifics beyond what those RFCs mandate:

* **A single-segment issuer.**
  The metadata's ``issuer`` is ``oauth-<site>``, not ``<site>/oauth``, for the same reason as the MCP server's PRM document: MCP clients don't reliably do RFC 8414 path insertion for multi-segment issuer paths.
* **Tokens are opaque and hashed at rest.**
  An issued token is a random secret (prefixed ``cmko1.``).
  Only its SHA-256 hash is ever stored, and it carries no encoded claims a caller could inspect.
* **Scope only narrows permissions.**
  ``cmk.gui.auth`` resolves a token to the approving user, capped by the token's own scope (read-only, or read-write) on top of whatever that user's roles already allow.
  A token can only ever narrow, never widen, what its user can do.
* **A code is single-use and short-lived.**
  Redis's ``GETDEL`` removes an authorization code's record on its first redemption attempt, successful or not, so a stolen or replayed code is worthless.
  Unredeemed codes expire after 10 minutes.
* **Coupled to one feature flag today.**
  The whole server answers 404 unless the MCP server is enabled for the site (``enabled=mcp_registration.mcp_server_enabled``, wired per edition in each edition's ``registration.py``).
  No other feature needs it yet.

Deployment view
================

The OAuth pages are only registered for the non-free editions (``pro``, ``cloud``, ``ultimate``, ``ultimatemt``).
Each edition's own ``registration.py`` wires them into the page registry, gated by the MCP enabled flag.
Apache proxies the metadata route's well-known path the same way it does the MCP server's PRM route.

Risks and technical debts
==========================

1. The RFC 8414 metadata document is incomplete: it has no ``jwks_uri``, since tokens are opaque rather than signed.
2. The introspection endpoint deliberately does not implement RFC 7662 section 2.1's MUST-protect requirement.
   It relies entirely on being unreachable except over the loopback boundary.

See Also
========

* :doc:`arch-comp-mcp`: this authorization server's only current consumer.
* ``cmk/gui/oauth/pages/``: page-level docstrings carry the RFC-by-RFC implementation notes this doc summarizes.
