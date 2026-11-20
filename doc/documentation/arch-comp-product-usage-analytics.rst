=======================================================
Product usage analytics (`product_usage_analytics`)
=======================================================

Introduction and goals
=======================

Checkmk can optionally collect a small set of anonymized usage data -- counts of hosts, services and folders, which check plug-ins are in use, the site's edition and version, and whether the site's Grafana connector is used -- and send it to a Checkmk-hosted analytics endpoint.
This usage data lets Checkmk see which features and integrations are actually used, to prioritize development.
The receiving endpoint lives in a separate repository (``checkmk-saas/checkmk-analytics``), outside this checkout, and is reachable from here only as a plain HTTPS endpoint; this document treats it as a black box.

Requirements overview
----------------------
* Collection and transmission are opt-in and ship disabled (``not_decided``); nothing is collected on a schedule or sent anywhere until an admin explicitly enables it.
* An admin must be able to inspect the exact data that would be sent before deciding, without enabling anything.
* Collected data must never carry secrets or identifying details such as hostnames, file paths, service instance names, or check-command arguments; only aggregate counts and check-command identifiers are allowed.
  The full list of allowed and forbidden data, and who approves new data points, is in the internal guideline "How to add data points to Product Usage Analytics" (Confluence).
* The identifier that correlates a site's uploads must be independent of that site's own Checkmk license/site ID.
* Every site collects and transmits independently, but in a distributed setup the central site makes the consent decision once and replicates it to remote sites.

Architecture
============

White-box overall system
-------------------------

.. uml::

    [cron] as cron
    [cmk-product-usage] as cli
    [Collectors] as collectors
    [Config & consent] as config
    [Transmission] as transmission
    () Livestatus as livestatus
    () "product_usage_analytics.mk" as config_file
    () "var/check_mk/product_usage/*.json" as storage
    [GUI pages] as gui
    () HTTPS as https
    [analytics.checkmk.com] as cloud

    cron ..> cli: invoke every 30 min
    cli ..> collectors: use
    cli ..> config: use
    cli ..> transmission: use
    collectors ..> livestatus: use
    collectors ..> storage: use
    config ..> config_file: use
    transmission ..> storage: use
    transmission ..> https: use
    https - cloud
    gui ..> config_file: use
    gui ..> storage: use

The ``cmk-product-usage`` command-line tool (``cmk.product_usage.cli``) is the single entry point that drives collection, local storage and transmission.
A per-site cron job invokes it every 30 minutes, but a collection actually happens only about once every 30 days (7 days on a Cloud trial site) -- see `Collection and transmission`_.

**Collectors.**
Eight collectors read from Livestatus, the filesystem, and this site's own REST API: check usage (``collectors/checks.py``), site info (``collectors/site_info.py``), a previously recorded Grafana-usage snapshot (``collectors/grafana.py``), which agent updater the hosts run (``collectors/agent_updater.py``), and, on a Cloud trial site only, the audit log entries per actor class (``collectors/audit_log.py``), the user counts (``collectors/users.py``), the number of hosts with default services only (``collectors/host_services.py``), and the stored login sessions (``collectors/sessions.py``).

**Config and consent.**
The config module reads the site's consent decision and HTTP-proxy setting from ``product_usage_analytics.mk``, a Checkmk global-settings file that a GUI page also reads and writes.

**Transmission.**
Transmission POSTs each locally stored JSON payload to the external endpoint over plain HTTPS and, on success, deletes the local file.

**GUI pages.**
The GUI pages -- a consent popup, the global-settings form, and an admin-only download page -- share the same config file and local storage as the CLI, so an admin can inspect or change consent without ever invoking the CLI.

The receiving endpoint is outside this repository; only its interface (a single HTTPS POST) is relevant here.

Interfaces
----------

* ``cmk-product-usage`` CLI (``cmk.product_usage.cli:main``): ``--collection`` (collect and store locally), ``--upload`` (transmit locally stored files), ``--dry-run`` (collect and print to stdout only, without storing or sending), and ``--cron`` (collect, store, upload and reschedule, but only if a run is actually due).
* Cron: ``etc/cron.d/cmk_collect_transmit_product_usage_analytics`` runs ``cmk-product-usage --cron`` every 30 minutes.
* Global settings variable ``product_usage_analytics`` (Setup -> Global settings -> "Product usage analytics"): ``enabled`` (``enabled``/``disabled``/``not_decided``, ships as ``not_decided``) and ``proxy_setting`` (the same HTTP-proxy form spec used elsewhere in Checkmk: environment, no proxy, an explicit URL, or a named global proxy).
* ``download_product_usage.py``: an admin-only GUI page (permission ``general.download_product_usage_analytics``, default role ``admin``) that runs the same collectors on demand and returns the payload as a downloadable JSON file, regardless of the site's consent setting.
* The consent popup for eligible admins (see `Opt-in and consent`_); it only links back to global settings and cannot itself change the setting.
* The REST API's ``get_graph`` metric action, called by the Grafana connector's Checkmk datasource plugin for every graph query (see :doc:`arch-comp-grafana-connector`), incidentally records a Grafana-usage snapshot that the next collection picks up.
* External HTTPS endpoint (outside this repo): ``POST https://analytics.checkmk.com/upload`` receives the payload; the URL can be overridden via the ``CMK_PRODUCT_USAGE_URL`` environment variable, which must still resolve to an ``https`` URL.
  The help menu's "About Checkmk" section also links to ``https://analytics.checkmk.com/manifest``, a human-readable description of what is collected.
* Manifest generator (``cmk/product_usage/manifest.py``, Bazel target ``//cmk/product_usage:manifest``): writes ``manifest.json``, a JSON schema of the complete transmitted document (metadata envelope plus data), built from the Pydantic models in ``schema.py``.
  The ``description`` and ``examples`` of every field are the source text for the public manifest page.
  The public page is not yet generated from this file (see `Risks and technical debts`_).

Runtime view
============

Collection and transmission
-----------------------------

**Scheduling.**
On each cron invocation, ``should_run_collection_on_schedule`` only lets collection proceed once a stored ``next_run`` timestamp has passed.
That schedule is staggered per site: the first run after enabling analytics picks a random point within the next 23.5 hours (``create_next_random_ts``), so freshly opted-in sites do not all transmit at the same moment; since cron runs every 30 minutes, that run starts within 24 hours.
Every following run is fixed at 30 days after the previous one, or 7 days on a Cloud site in trial (``create_next_ts``).
The CLI checks whether a site is a Cloud trial (``is_cloud_trial``) once per run that collects or plans the next run, and uses that one answer for both the payload and the interval: it reads the license state only on Cloud sites, through the commercial Cloud licensing handler, and falls back to the product usage payload and the 30-day interval if that read fails.

**What a due run collects:**

* Site info -- Livestatus host/service counts, a folder count from walking the config directory, edition and version.
* Per-check usage -- Livestatus's services table, keyed by check command with anything after a ``!`` stripped so check-parameter secrets are never collected.
* Disabled-service counts -- parsed out of the discovery long-plugin-output's "Service ignored: " lines.
* The last recorded Grafana-usage snapshot, if any.
* Which agent updater the hosts run -- the state of the "Agent updater" item of "Analyze configuration" and its five host counts, over the hosts whose baked agent enables agent updates.
  Only an edition with the Agent Bakery can count this, and only on a central site, and this module ships under the GPL and may not import the bakery.
  The collector therefore asks the bakery's internal REST endpoint (``domain-types/agent/actions/updater_usage/invoke``) over this site's own REST API, authenticating with the site-internal secret as ``cmk/base/diagnostics.py`` does.
  The numbers are counted while that request is answered, so nothing is cached or left on disk; it sends no host names.
  Any other answer than the counts -- no Agent Bakery, a remote site, a release without the endpoint -- leaves the field ``null``.
* On a Cloud trial site only, the audit log entries per actor class -- interactive users, automation users, and the platform (the Cloud platform's users and the site itself) -- as a count and the time of the newest entry.
  The collector reads the current and the rotated audit logs and the GUI's user store; it sends no user IDs.
* On a Cloud trial site only, the number of activated hosts whose only services are ``Check_MK`` and ``Check_MK Discovery``, or that have no services -- hosts that deliver no data yet.
  The collector reads the services of each host from Livestatus's hosts table, so a host counts only after its changes are activated; it sends no host or service names.
* On a Cloud trial site only, the number of users of the Cognito login, split into business and non-business by the domain of their email address, which is their user ID.
  A domain on the collector's free-mail list, or a subdomain of one, is non-business; any other domain is business. No address or domain is sent.
* On a Cloud trial site only, every stored login session with its start and its last activity time.
  The collector reads the GUI's session files (``var/check_mk/web/<user>/session_info.mk``); it sends no user IDs and no session IDs, and sorts the sessions by time so that the order does not tell which ones belong to the same user.

The result is wrapped in a ``SelfDescribingModel`` envelope (``{"metadata": {version, namespace, name}, "data": {...}}``) and stored as ``var/check_mk/product_usage/product_usage_<timestamp>.json``.
A Cloud trial site sends ``CloudTrialPayload`` (``cloud_trial_analytics``) instead of ``ProductUsagePayload`` (``product_usage_analytics``): the same data plus trial signals; of these, only the audit log, the user counts, the number of hosts with default services only, and the sessions are collected so far, the others are still ``null``.
A trial signal whose collector fails is ``null``: the error goes to ``var/log/product_usage_analytics.log`` and the rest of the payload is sent as usual.

**Transmission and retry.**
Transmission uploads every stored file, oldest first, and deletes a file only once its POST gets a successful response, so a failed upload's file survives to be retried.
The Grafana-usage snapshot is cleared only once the newest file transmits successfully, since that file is the one expected to carry it.
Because the whole ``--cron`` flow returns immediately while a run is not yet due, a failed transmission is not retried until the site's next scheduled run (~30 days, or ~7 days on a Cloud trial site), unless an admin re-runs ``cmk-product-usage --upload`` manually.

Extending the collected data
-----------------------------

Which data may be added, and who approves it, is defined in the "How to add data points to Product Usage Analytics" guideline in Confluence.
This section covers the technical side.

**Code changes.**
Add the new field to ``ProductUsageData`` in ``cmk/product_usage/schema.py``, gather it in a collector under ``cmk/product_usage/collectors/`` (a new module, or an existing one if it fits), and wire the result into ``collect_data()`` in ``cmk/product_usage/collection.py``.
A Cloud trial signal goes into ``CloudTrialPayload`` instead and is wired into ``collect_cloud_trial_data()``; catch its collector's errors there, as ``_collect_audit_log()`` does, so that one failing trial signal does not stop the payload.
Keep the same sanitization discipline the existing collectors apply -- no hostnames, paths, service instance names, or check-command arguments, per the `Requirements overview`_.
Every field needs a ``description`` and at least one entry in ``examples``; ``tests/unit/cmk/product_usage/test_manifest.py`` fails otherwise.
The description is the text admins read on the manifest page, so write it for admins, not developers.
Check the result with ``cmk-product-usage --dry-run`` on a test site.

**Optional fields and the model version.**
Add new fields as optional (``<type> | None`` with ``default=None``, like ``grafana``).
An optional field does not require a new model version: ``metadata.version`` stays ``v1``.
Increase the version only for changes that break existing consumers: removing or renaming a field, changing its type or meaning, or adding a required field.
New data points are commonly backported to stable branches, to get data from real environments sooner.
Patch releases of the same Checkmk version can therefore send different sets of fields, and consumers must treat a missing optional field as "not collected by this release".
Extend the existing ``product_usage_analytics`` model; agree with the component owners before introducing a separate model with its own ``metadata.name``.

**Data structure.**
Group the data of a feature in one optional object at the top level, named after the feature (like ``grafana``), not after the team or initiative that adds it: field names are public in the manifest and outlive initiatives and team structures.
A feature therefore adds exactly one top-level field; its collector lives in its own module under ``collectors/``.
Fields added to an existing object later must be optional as well.
Express "feature not used" inside the object (``is_used: false``, counts of 0), so that ``null`` only means "not collected by this release"; ``grafana``, which is ``null`` when Grafana is not connected, predates this rule.
Follow the existing naming: snake_case, ``count_*`` for counts, ``is_*`` for booleans.
The existing site-wide fields (``count_hosts``, ``edition``, ...) and ``checks`` stay at the top level, since moving them would be a breaking change.

**Receiving side.**
The endpoint in ``checkmk-saas/checkmk-analytics`` validates uploads against its own copy of the model.
It stores the fields that model knows and drops unknown fields; the rest of the upload is processed as usual.
A field sent before the endpoint knows it is therefore lost, not the upload.
Extend and deploy the endpoint's model before the first Checkmk release that sends the new field, including stable patch releases, so that no data from that release is lost.

**Manifest page.**
The public manifest page is maintained by hand.
After adding a field, give Marketing the new field's ``description`` and ``examples`` (or the regenerated ``manifest.json``) so the page lists it.

**Werk.**
Admins who already enabled analytics are not asked again: The consent popup only appears while the decision is ``not_decided``.
After an update, their sites send the new field without any notice in the GUI.
Add a werk with the change that adds the field, so these admins learn what their sites now transmit.
The werk names the new field, describes its content in the words of the field's ``description``, and points to ``cmk-product-usage --dry-run`` and the manifest page.
Use class ``feature`` and component ``wato``, like the other product usage analytics werks (e.g. werk 19605).

**Limits.**
A collector runs synchronously inside ``cmk-product-usage --cron`` and inside the admin download page request.
A new collector must finish within a low single-digit number of seconds on a large site.
Prefer Livestatus queries and data that already exists on disk, and do not call external services.
The agent updater collector calls this site's own REST API over ``localhost``, which is not an external service but does make it the only collector that needs Apache to be running; take that route only for a data point that a GPL module cannot compute itself.
The collector sees only the local site; in a distributed setup each site sends its own data.
Keep additions small: single values (counts, booleans, versions) are fine, and a list or map is fine if its length depends on what Checkmk ships (check plug-ins, rulesets, features), never on the site's configuration (hosts, services, rules, users).
For orientation, the payload is about 5--30 KB today, almost all of it the per-plug-in ``checks`` map; a new data point should not noticeably change that.
The upload itself has a 30 second HTTP timeout (``transmission.py``); the client does not enforce a payload size limit.

Opt-in and consent
---------------------

**Default state.**
Analytics ships disabled (``not_decided``); the cron path returns immediately while ``enabled`` is not ``"enabled"``, so nothing is collected, scheduled, or transmitted until an admin makes a decision.

**Who sees the popup, and when.**
On login, ``render_product_usage_analytics_popup`` (called from the sidebar) shows a Vue popup to admins who have not yet decided -- on a standalone site or the central site of a distributed setup, but never on a remote site or to non-admins.
A cookie (``product_usage_analytics_popup_timestamp``, two-year lifetime) is refreshed to "now" every time the popup would next be shown; the popup itself only appears once 30 days have passed since that timestamp, and then keeps reappearing on every login until a decision is made.

**Popup actions.**
The popup's only actions are to dismiss it (which just closes the dialog; the cookie was already refreshed before it was shown) or to follow a link into global settings, where the actual ``enabled``/``disabled`` choice is made.
The popup text and the global-settings hint both point admins at ``cmk-product-usage --dry-run`` or the download page to inspect exactly what would be sent before opting in.

**Activation mechanics.**
The config domain's ``activate()`` and ``create_artifacts()`` are no-ops -- flipping the setting does not restart anything -- but ``always_activate = True`` ensures this domain's config file is still pushed out whenever any activation happens, rather than staying pending until an analytics-specific change also occurs.

Deployment view
================

**Shipped in every edition.**
The collection and transmission code (``cmk.product_usage``) and its ``cmk-product-usage`` console-script entry point ship in every edition's wheel.
Likewise, the GUI wiring -- config variable, permission, download page and popup -- is registered by ``cmk.gui.product_usage_analytics.register()``, which every edition's ``registration.py`` calls via ``common_registration.register()``, so the feature (off by default) is present even in the community edition.

**``ultimatemt``.**
This edition additionally supplies its own hint text for the global-settings form, requiring a tenant admin to obtain per-customer consent before enabling data collection on a multi-tenant site, with a link to the relevant user-guide section.

**``cloud``.**
This edition treats analytics as opt-out rather than opt-in: deploy tooling outside this repository sets the global setting to ``enabled`` when provisioning a cloud site, and the edition calls ``disable_product_usage_analytics_popup()`` to suppress the sidebar popup, since consent is already decided before an admin ever sees it.
Cloud sites in trial run every 7 days instead of every 30 days and send the Cloud trial payload; to tell, the CLI reads the license state through the commercial Cloud licensing handler, which makes ``cmk.licensing`` a dependency of the CLI (see `Collection and transmission`_).
The underlying collection, config and transmission machinery is otherwise unaffected.

**Distributed setups.**
Each site collects and transmits independently.
Only the consent *decision* is centralized: the config file is registered as a ``ReplicationPath``, so the central site's ``enabled``/``disabled``/``proxy_setting`` choice is pushed to remote sites on activation.
Each site still needs its own outbound HTTPS connectivity to the analytics endpoint -- the global-settings help text calls this out explicitly.

**Outbound proxy.**
Transmission goes through this site's configured HTTP proxy (``cmk.utils.http_proxy_config``), resolved from the environment, a named global proxy, or an explicit URL -- the same building block used elsewhere in Checkmk for outbound HTTP.

Risks and technical debts
==========================

1. A failed upload is retried only at the next scheduled run, which for an already-opted-in site can be up to ~30 days later (~7 days on a Cloud trial site), since the whole ``--cron`` flow exits immediately while a run is not yet due; there is no short-interval backoff for a transient network failure.
2. Grafana-usage detection is captured once and latched: ``store_usage_data`` returns immediately if ``grafana_usage.json`` already exists, and the file is cleared only once a transmission that included it succeeds.
   A site that toggles analytics off before ever successfully transmitting keeps a possibly stale snapshot (e.g. an outdated Grafana version) until it is eventually sent or the file is removed by hand.
3. The client and the endpoint each have their own copy of the payload model, and nothing checks that they match.
   If a release sends a field the endpoint does not know, the endpoint drops that field and keeps the rest; that field's data from the release is lost without an error on either side.
4. The public manifest page (``https://analytics.checkmk.com/manifest``) is maintained by hand and does not yet read the generated ``manifest.json``, so it can differ from the data that is actually sent.
5. Collection is not fail-open: ``collect_data()`` calls all collectors in one step, and an exception in any of them aborts the run.
   Nothing is stored or uploaded in that run, including files left over from earlier failed uploads, and the next run is not planned, so every cron run (every 30 minutes) tries again until the error is gone.
   The intended design is fail-open: a failure while gathering one data point must not prevent collecting and sending the others.
   New collectors are built that way from now on; the agent updater collector is the first one whose errors ``collect_data()`` catches, leaving its field ``null``.
6. The audit log collector classifies users by rules of thumb.
   The Cloud platform's user IDs are fixed (``api_user``, ``agent_registration``), so the entries of a different registration user for the preconfigured agent count as automation.
   A deleted user counts as interactive only if its ID is an email address, like a Cognito user's ID; otherwise it counts as automation.
7. The count of hosts with default services only knows these services by their fixed names, ``Check_MK`` and ``Check_MK Discovery``.
   A site that still uses the legacy name ``Check_MK inventory`` counts such hosts as monitored; Cloud trial sites are new and use the new name.
   In a cluster, the clustered services belong to the cluster host, so a node whose services are all clustered counts although it delivers data.
8. The user counts include every Cognito user who has ever signed in: the site keeps users that are removed from the tenant, and a user whose email address changes is counted twice.
   The free-mail list is a copy of cloudmk's list plus the major providers it lacks, and nothing keeps the two in sync; a free-mail domain missing from the list counts as business, so the business count is an upper bound.
9. The sessions are a snapshot of the GUI's session store, not a login history.
   The store is pruned only when a user's session is saved: it then keeps that user's 20 most recent sessions and drops those idle for more than 7 days.
   A busy user's sessions can therefore be gone before the weekly run sends them, while those of a user who has not come back stay in the store, and are sent, beyond 7 days.
   Logged-out sessions are sent too.
   With the global setting "Limit login to single session at a time" enabled, each login removes the user's earlier sessions, so at most one session per user is stored.
   Deleting a user keeps its sessions in the store: they are still sent until the cleanup of abandoned profiles removes the profile, 30 days after its last change.
   A session that is still in the store at the next run is sent again; the payload has no session ID, so the receiver can match the two only by their start time.
   The store also holds sessions that a non-automation user opened with basic auth or web server authentication; a client that does not return the session cookie opens a new one with every request.
   The payload does not tell these from interactive logins.

See Also
========

* :doc:`arch-comp-grafana-connector`: the REST API action this connector calls for every graph is also where Grafana usage is detected for product usage analytics.
