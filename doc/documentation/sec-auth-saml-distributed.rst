==========================
SAML in distributed setups
==========================

.. note:: This page describes how SAML works on remote sites, and the per-site authentication configuration it is built on, both introduced in Checkmk 3.0.0.
   Logging in to a *remote* site via SAML requires a commercial edition (every edition except Community and Cloud, see ``distributed_saml_supported()``).
   The per-site authentication configuration itself exists in all editions and governs LDAP connections in the same way, so this page covers those where they differ from SAML.
   The single-site SAML flow is described in :doc:`sec-auth-saml`.

Introduction
############

Before Checkmk 3.0.0 a site had a single *User synchronization* field (``user_sync``) that governed the periodic LDAP synchronization.
Login itself was not configurable per site: every configured connection could authenticate users on every site, and SAML worked on the central site only, because a SAML connection was pinned to its owning site through the ``owned_by_site`` attribute.

Two things changed with Checkmk 3.0.0 (see `werk #22208 <https://checkmk.com/werk/22208>`_):

* Authentication is configured per site.
  Every site in *Setup > Distributed monitoring* carries an ``authentication_connections`` field naming the LDAP and SAML connections that may log users in on that site.
  These connections are also the ones that create users on the site and perform the initial user setup.

* SAML works on remote sites.
  A SAML connection is still configured only on the central site.
  The central site resolves it per remote site, derives that site's service provider endpoints, ships the required key material with the configuration synchronization, and the remote site then acts as its own service provider.

The remaining job of the old field, the periodic attribute synchronization, moved to a second and independent field, ``user_attribute_sync_connections``.
A site can therefore authenticate against a connection without synchronizing its attributes, and vice versa.

Terminology
***********

*Authentication connection*
   A connection that may log a user in on this site.
   It creates the user record and performs the initial setup.

*Attribute sync connection*
   A connection whose users are kept up to date on this site by the periodic background job (alias, email, roles and contact groups).

A connection can be one, the other, or both.

Configuration model
###################

Both fields are part of ``SiteConfiguration`` (``packages/cmk-livestatus-client/cmk/livestatus_client/_connection.py``) and are stored on the central site in ``etc/check_mk/multisite.d/sites.mk``.
Both are declared ``NotRequired`` only so that partial specifications can be constructed in code.
The site editor, the REST API and ``cmk-update-config`` always write them.

authentication_connections
**************************

The field has three value shapes, matching the three choices offered by the site editor:

.. csv-table:: Table 1: Values of ``authentication_connections``
   :header: Value, Editor choice, Meaning
   :widths: 30, 30, 40

   "``""disabled""``", "Disabled (Use the local users of the central site)", "No LDAP or SAML login on this site."
   "``(""all"", [types])``", "Use all", "Every configured and enabled connection of the selected types, including connections added later. Resolved per site before propagation."
   "``[entries]``", "Use the following", "An explicit, ordered list of connections."

An LDAP entry is a plain ``("ldap", connection_id)`` tuple.
A SAML entry carries a small dictionary, because the service provider endpoints are site specific and are stored next to the reference::

    # etc/check_mk/multisite.d/sites.mk on the central site
    sites = {
        "remote_1": {
            ...
            "multisiteurl": "https://remote1.example/remote_1/check_mk/",
            "authentication_connections": [
                ("ldap", "LDAP_1"),
                ("saml", {
                    "connection_id": "saml_1",
                    "metadata_endpoint": "https://remote1.example/remote_1/check_mk/"
                                         "saml_metadata.py?RelayState=saml_1",
                    "acs_endpoint": "https://remote1.example/remote_1/check_mk/saml_acs.py?acs",
                }),
            ],
            "user_attribute_sync_connections": ["LDAP_1"],
        },
    }

The endpoint URLs are derived, never entered by hand.
``populate_saml_site_endpoint_urls()`` recomputes them from the site's *Server URL for SAML ACS callback* (``multisiteurl``) and the connection ID on every save and on every synchronization, so they cannot drift away from the site URL.
The connection ID is percent encoded into the ``RelayState`` query parameter as a defense in depth measure.

On the central site ``multisiteurl`` is empty, since it is the URL the central site uses to reach a remote site.
In that case the connection's own ``checkmk_assertion_consumer_service_endpoint`` is used, which is the URL the SAML implementation uses there at runtime anyway.

user_attribute_sync_connections
*******************************

The value is ``"all"``, ``"disabled"``, or a list of LDAP connection IDs.
SAML connections never appear here.
SAML has no background synchronization; it updates a profile only during a login.

``user_sync_config()`` maps the value onto the legacy shape that the LDAP connector and the synchronization job still consume.
``effective_user_attribute_sync_connections()`` reads the propagated global on a remote site and the site's own entry on the central site.

.. note:: ``LDAPUserConnector.is_enabled()`` is true when the site uses the connection for either purpose: login (``is_authentication_connection()``) or the periodic attribute synchronization (``is_sync_connection()``).
   Password login (``check_credentials``) and user creation during the background synchronization are gated by ``is_authentication_connection()``, the background job itself by ``is_sync_connection()``.
   A connection listed for authentication but excluded from the attribute synchronization therefore logs users in (and synchronizes that one user during the login) but is left alone by the periodic job.
   A connection excluded from authentication never logs anybody in on that site, even if it takes part in the periodic job (CMK-40326).

Propagation to remote sites
###########################

A remote site never reads ``sites.mk``, because that file is not part of the configuration synchronization.
Everything a remote site knows about its own authentication arrives as resolved, site specific globals.

.. uml:: sec-auth-saml-distributed-propagation.puml

``get_site_globals()`` (``cmk.gui.watolib.config_sync``) writes both fields into the site's ``sitespecific.mk`` during snapshot creation.
They are listed in ``UNREGISTERED_SETTINGS``: they belong to the GUI configuration domain, are handed over by the central site and are deliberately not exposed as editable global settings on the remote site.

Only resolved values cross the site boundary.
The ``("all", [types])`` shorthand and the customer scoping are evaluated on the central site, where ``sites.mk`` and the customer to site mapping are available.
The remote site receives a concrete list, with the metadata and ACS URLs already populated.

At runtime ``effective_authentication_connections()`` branches on ``is_distributed_setup_remote_site()``.
A remote site returns ``active_config.authentication_connections`` (the propagated global), the central site resolves its own ``sites.mk`` entry.
Everything downstream goes through this single function: the login page buttons, the SAML endpoints, the LDAP login and user creation gates and the user preservation list.
Both site roles therefore behave identically without special cases.

Users created on a remote site
******************************

Users created on a remote site by a login are local to that site and would be removed by the next configuration synchronization.
``_active_connectors_for_user_preservation()`` (``cmk.gui.watolib.activate_changes``) builds the set of connector IDs whose users have to survive: the union of the site's attribute synchronization list and every connection in its authentication list.
Users owned by those connectors are reintegrated into ``contacts.mk``, ``users.mk`` and ``auth.serials`` after the synchronization archive has been unpacked.

Removing a connection from a site's authentication list therefore also stops preserving the users it created there.

SAML on a remote site
#####################

The remote site is a full service provider.
It serves its own metadata, initiates its own authentication requests and consumes assertions at its own assertion consumer service.
What it does not have is any SAML configuration of its own.

.. uml:: sec-auth-saml-distributed-flow.puml

The general flow and the contents of the ``SAMLRequest`` and ``SAMLResponse`` are described in :doc:`sec-auth-saml`.
The identity provider talks to the remote site directly; nothing is proxied through the central site.

Endpoints
*********

Three ``noauth:`` pages implement the service provider on every site (``cmk.gui.nonfree.pro.saml2_auth._pages``):

.. csv-table:: Table 2: Service provider endpoints
   :header: Page, Purpose
   :widths: 30, 70

   "``saml_metadata.py``", "Serves the service provider metadata for one connection."
   "``saml_sso.py``", "Builds the ``AuthnRequest`` and returns the auto-submitted form."
   "``saml_acs.py``", "Consumes the ``SAMLResponse`` and creates the session."

All three carry the connection ID in the ``RelayState`` parameter, in the form ``<connection_id>,<target_url>``.

Per-site interface configuration
********************************

``_site_interface_config()`` takes the connection's ``InterfaceConfig`` and overrides exactly one value: the ACS URL, taken from this site's entry in the effective authentication connections.
Entity ID, certificates and identity provider metadata come straight from the shared connection; there are no other per-site overrides.
If the site has no usable entry, for example because the entry still holds the ``-`` placeholder, the connection's own ACS endpoint is used as a fallback.

Because the entity ID is shared, all sites appear to the identity provider as the same service provider.
Each site's ACS URL has to be registered with the identity provider.
The site edit page shows the derived *Metadata endpoint URL* and *Assertion Consumer Service URL* per SAML entry once the site has been saved.

Request gating
**************

``_initialise_page()`` rejects a request whose connection is disabled, and a request whose connection ID is not contained in ``get_saml_connections_for_current_site()``.
The login page only renders buttons for the connections available on the site, but the endpoints do not trust the connection ID in the request.
A hand crafted URL naming a connection that is not listed for this site is refused.

Certificates
############

A SAML connection signs requests, and optionally decrypts responses, with either the built-in Checkmk certificate or a custom one.
Both live below ``etc/ssl/saml2`` (``cmk.gui.nonfree.pro.saml2_auth._paths``):

.. csv-table:: Table 3: Certificate locations
   :header: Path, Content
   :widths: 55, 45

   "``etc/ssl/saml2/builtin/signature/{private,public}.pem``", "Built-in pair, shared by all connections that select it."
   "``etc/ssl/saml2/builtin/encryption/{private,public}.pem``", "Built-in encryption pair."
   "``etc/ssl/saml2/custom/<connection_id>/<kind>/{private,public}.pem``", "Custom pair of one connection."

Selective distribution
**********************

The former replication path copied the whole ``etc/ssl/saml2`` tree, that is the custom certificates of *all* SAML connections, to *every* remote site.
It has been replaced by a ``SnapshotFileCreator`` registered under the same ident, ``saml2_certs`` (``cmk.gui.nonfree.pro.saml2_auth._snapshot``).
It assembles the snapshot per site, so that only the key material referenced by the SAML connections resolved for that site is copied.

Reusing the ident is load bearing.
The snapshot collectors treat a replication path whose ident matches a registered ``SnapshotFileCreator`` as assembled per site and skip the one to one copy.
The ``ReplicationPath`` registration is still required, because the synchronization delta only considers files below a registered replication path; without it the assembled certificates would never be transferred to, or pruned from, a remote site.

Rotation
********

The built-in signature certificate is renewed by a cron job when it expires in less than 14 days.
Two rules keep this safe in a distributed setup:

* ``replace_builtin_signature_cert()`` returns immediately on a remote site.
  A remote site holds a copy of the central site's certificate.
  Rotating that copy locally would produce a certificate the identity provider does not know, and the next activation would overwrite it anyway.

* When the central site rotates the certificate, it adds a pending change for every remote site whose SAML connections sign with the built-in certificate (``remote_sites_using_builtin_signature_certificate()``).
  Without that pending change nothing would prompt an activation, and the remote sites would keep signing with the superseded certificate until it expires.

This is also why the choice is labeled *Use Checkmk certificate (central site only)* in the connection editor.
The certificate is generated on the central site and reaches the remote sites through the configuration synchronization.
A remote site that has never received an activation has no key material and cannot complete a SAML login.

User ownership
##############

Every user record carries a ``connector`` field naming the connection that owns it.
Now that SAML and LDAP can both authenticate on the same site, a single person may arrive through either path, so the ownership rules matter (CMK-33805, CMK-33824):

* *User creation is reserved for authentication connections.*
  During the periodic background synchronization an LDAP connector that is not listed in the site's ``authentication_connections`` updates existing users, and removes the users it owns when they leave the directory, but does not create new users (``is_authentication_connection()``).
  A login attempt may always create a user.

* *The owning connector authenticates first.*
  ``check_credentials`` consults the connector that owns an existing record before the others, regardless of the declaration order, and stops at the first connector that returns a user ID.
  Two enabled connectors never both create the same user.

* *LDAP may take a SAML owned user over.*
  When an LDAP synchronization finds a user owned by a SAML connector under the bare user ID, it flips ``connector`` to itself, records an explicit change log entry, and resets the attributes managed by the previous connection, so that stale SAML values do not linger.
  Existing users are never renamed, so the takeover matches the bare user ID only.

* *LDAP wins afterwards.*
  Once a user is owned by LDAP, a subsequent SAML login authenticates the person, but does not modify the profile and does not reclaim the ownership.
  Any other connector mismatch still raises an error; only the SAML to LDAP direction is tolerated.

* *An orphaned owning connection locks the user out.*
  A user whose owning connection has been deleted cannot log in, and no new record is created for them.

* *The login lock always wins.*
  An administrator can disable the login of any user in Setup or via the REST API, whoever owns the record (CMK-40515).
  Both login paths honour the lock: the password login in ``check_credentials``, the SAML login in ``ensure_user_may_login`` on the ACS page.
  A sync never lifts a lock an administrator set: the AD "authentication expiration" plug-in only unlocks a user it locked itself (marker ``ldap_locked_in_ad``), and quarantine reactivation only unlocks a user that was not locked before the quarantine (``locked_before_quarantine`` in ``QuarantineInfo``).

SAML profile updates are written only when something actually changed (``_is_changed_profile()``), because saving invalidates the user cache and is expensive.
Both creation and update emit a ``UserManagementEvent`` security event and add a pending change scoped to all activation sites.

Multi-tenancy
#############

This section applies to the Ultimate edition with multi-tenancy.
In all other editions the customer API is a stub that treats every scope as global, and the checks below are no-ops.

A SAML connection is scoped to exactly one customer, chosen directly below the connection ID and defaulting to the provider.
There is no *Global* scope for SAML connections.
Users created by a SAML login belong to that customer, the same way LDAP connections already behaved.

The scoping is enforced at four places:

.. csv-table:: Table 4: Enforcement of the customer scope
   :header: Place, Function, Effect
   :widths: 22, 34, 44

   "Propagation", "``_connection_available_on_site()``", "A customer scoped connection is only resolved into the authentication list of the sites of that customer."
   "Runtime, any site", "``_may_authenticate_on_current_site()``", "Works without ``sites.mk`` and therefore also on a remote site. The central site is no exception: it holds every connection as the configuration master, but for login it belongs to the provider customer like any other site."
   "Editing a connection", "``sites_with_dangling_login_reference()``", "Changing the customer of a connection is refused while sites of another customer still reference it explicitly."
   "Editing a site", "``login_connections_of_other_customer()``", "The mirror image: changing the customer of a site is refused while it references connections scoped to a different customer."

Both dangling reference checks only inspect explicit lists.
The ``("all", [types])`` shorthand resolves dynamically and simply skips connections that are not available on a site, so it can never leave a dead reference behind.
``"disabled"`` references nothing.

Finally the assertion consumer mirrors the password login path: after a successful assertion ``is_customer_user_allowed_to_login()`` still has to pass.
A user of another customer is rejected even though the identity provider authenticated them successfully.

Security considerations
#######################

Assertions are bound to a single site
*************************************

Sites in a distributed setup share a SAML connection and therefore share the key material and the service provider entity ID.
Without further measures a signed assertion issued for the ACS of one site stays valid when it is replayed at the ACS of another site: the assertion signature remains valid, the ``InResponseTo`` ID can be harvested from the target's single sign-on endpoint, and the ``Response`` wrapper (``Destination``, wrapper signature) is not integrity protected.
A malicious remote site could use this to hijack a session on the central site (CMK-35948).

``Interface.validate_recipient()`` closes this hole.
Every ``SubjectConfirmationData`` of an assertion carries a ``Recipient`` attribute, the ACS URL the identity provider issued the assertion for, and this attribute is part of the signed assertion.
Checkmk requires it to be equal to the ACS endpoint of the site processing the response, and rejects a missing or mismatching ``Recipient``, regardless of what an attacker does to the unsigned wrapper.

The implementation performs this check explicitly, in addition to the ``InResponseTo`` and issuer checks.
The SAML library only validates the recipient when it is handed the outstanding queries (``conv_info``), which Checkmk cannot supply, because the request and the response are handled in two separate sessions, in ``saml_sso.py`` and ``saml_acs.py``.

Password changes are blocked on remote sites
********************************************

Credentials are owned by the central site (CMK-33900).
On a remote site *Change password* is hidden from the user menu and the related dropdown, the change password page raises ``MKAuthException`` on rendering and on submission, and the REST API answers with ``403`` when a user edit sets ``auth_option.auth_type`` to ``password``, ``automation`` or ``remove``.

Further boundaries
******************

These properties are covered by the system tests in ``tests/system/multisite/identity``:

* An authentication cookie minted on one site is rejected on another site.
* Logging out on one site leaves the sessions on other sites valid.
* The login page offers exactly the connections the site configuration allows, and the endpoints check again.

Migration from user_sync
########################

``user_sync`` has been removed from the site specification, and the REST API schema for site connections changed in place.
Existing logins keep working, but automation that writes site connections has to be adapted, see `werk #18500 <https://checkmk.com/werk/18500>`_.

``cmk-update-config`` runs two update actions:

* ``migrate_user_sync_to_auth_connections`` (sort index 35) removes the obsolete ``user_sync`` key and fills in the two new fields.
* ``remove_saml_owned_by_site`` (sort index 40) strips the dead ``owned_by_site`` attribute from SAML connections, so that the records on disk match the new schema.

Both expire with Checkmk 3.1.0.
Only fields that are not set yet are filled in, so a site that was migrated by hand keeps its configuration.

.. csv-table:: Table 5: Mapping of the legacy ``user_sync`` value
   :header: Legacy ``user_sync``, ``authentication_connections``, ``user_attribute_sync_connections``
   :widths: 30, 35, 35

   "``""all""``", "``(""all"", [types])``", "``""all""``"
   "``""master""``", "``(""all"", [types])``", "central ``""all""``, remote ``""disabled""``"
   "non-empty ``(""list"", [...])``", "the same IDs as LDAP entries", "the same IDs"
   "``None`` or empty list", "``(""all"", [types])``", "``""disabled""``"
   "key not present", "``(""all"", [types])``", "central ``""all""``, remote ``""disabled""``"

``[types]`` is ``["ldap", "saml"]`` on the central site and ``["ldap"]`` on remote sites.

The authentication side stays permissive on purpose, so that every login that worked before the update still works afterwards, including the users those logins create on the site, which only survive configuration pushes while their connection is listed.

Remote sites are migrated to LDAP connections only, never to SAML, even where the central site ends up with both.
SAML could not authenticate on a remote site before this version, so enrolling every SAML connection automatically would widen the authentication surface of those sites during an update.
To let users log in to a remote site via SAML, the connection has to be added to that site's *Authentication connections* after the update, followed by an activation.

REST API
########

The site management endpoints were changed in place instead of introducing unstable successors.
``authentication_connections`` is a required key without a default below ``configuration_connection``.

.. csv-table:: Table 6: Affected endpoints
   :header: Endpoint, Change
   :widths: 60, 40

   "``GET /domain-types/site_connection/collections/all``", "Gains the key in its output."
   "``GET /objects/site_connection/{site_id}``", "Gains the key in its output."
   "``POST /domain-types/site_connection/collections/all``", "Requires the key in its input."
   "``PUT /objects/site_connection/{site_id}``", "Requires the key in its input."
   "``.../actions/{delete,login,logout}/invoke``", "Unchanged."

The three value shapes of the field::

    {"authentication_connections": {"type": "disabled"}}

    {"authentication_connections": {"type": "all",
                                    "connection_types": ["ldap", "saml"]}}

    {"authentication_connections": {"type": "list",
                                    "connections": [
                                        {"type": "ldap", "connection_id": "LDAP_1"},
                                        {"type": "saml", "connection_id": "saml_1"}]}}

The existing ``user_sync`` key keeps its name and shape in the API, but is mapped to ``user_attribute_sync_connections`` internally.
The SAML endpoint URLs are not part of a request: ``base_to_internal()`` runs ``populate_saml_site_endpoint_urls()`` before saving, so that a site created through the API ends up with the same configuration as one created in the site editor.

Enabling SAML on a remote site
##############################

#. Create or edit the SAML connection on the **central** site.
   In a multi-tenancy setup, scope it to the customer that owns the target sites.
#. Open *Setup > Distributed monitoring*, edit the remote site and add the connection below *Authentication connections*, or select *Use all* with SAML enabled.
#. Make sure the site's *Server URL for SAML ACS callback* is the URL that the browser and the identity provider actually reach.
#. Save the site, then read the derived *Metadata endpoint URL* and *Assertion Consumer Service URL* from the site edit page and register them with the identity provider.
#. Activate the changes.
   The remote site receives the resolved connection list and the required key material.

Diagnose
########

The SAML implementation logs to the ``saml2`` logger and the LDAP connector to ``ldap.Connection(<connection_id>)``, both in ``$OMD_ROOT/var/log/web.log`` of the site that processes the login.
In addition the security event log contains ``AuthenticationInitiated``, ``AuthenticationSuccess``, ``AuthenticationFailure`` and ``UserManagementEvent`` records.

.. csv-table:: Table 7: Common symptoms
   :header: Symptom, Likely cause
   :widths: 40, 60

   "No SAML button on the login page of a remote site", "The connection is not listed for that site, is disabled, belongs to a different customer, or the change has not been activated yet."
   "*This connection is not available on this site*", "The same causes, reached through a bookmarked or hand crafted single sign-on URL instead of the login page."
   "*Assertion Recipient does not match this Service Provider*", "The identity provider issues assertions for a different ACS URL. Usually the callback URL of the site and the registered ACS URL have drifted apart."
   "Login worked and broke after an activation", "The owning connection of the user is no longer listed for the site, so the record was not preserved during the configuration push."
   "Signature failures on a remote site only", "The remote site has not received the key material yet, or the built-in certificate was rotated on the central site and the resulting pending change was not activated."
   "Attributes are not updated on a remote site", "``user_attribute_sync_connections`` is ``""disabled""`` for that site, which is the default for remote sites after the migration."

Where to look in the code
#########################

.. csv-table:: Table 8: Code map
   :header: Path, Content
   :widths: 55, 45

   "``packages/cmk-livestatus-client/cmk/livestatus_client/_connection.py``", "``SiteConfiguration`` and the authentication value types."
   "``cmk/gui/userdb/_connections.py``", "Resolution, per-site availability, customer checks."
   "``cmk/gui/userdb/_user_sync_config.py``", "Effective attribute synchronization value."
   "``cmk/gui/watolib/config_sync.py``", "Endpoint URL derivation, ``get_site_globals()``."
   "``cmk/gui/general_config.py``", "The propagated globals as seen on a remote site."
   "``cmk/gui/watolib/sites.py``", "Form specs of both site fields."
   "``cmk/gui/wato/pages/sites.py``", "Site edit page."
   "``cmk/gui/login.py``, ``cmk/gui/mobile/pages.py``", "SAML buttons on the login pages."
   "``cmk/gui/nonfree/pro/saml2_auth/_pages.py``", "Metadata, single sign-on and ACS endpoints."
   "``cmk/gui/nonfree/pro/saml2_auth/_interface.py``", "SAML library wrapper, recipient validation."
   "``cmk/gui/nonfree/pro/saml2_auth/_snapshot.py``", "Per-site certificate assembly."
   "``cmk/gui/nonfree/pro/saml2_auth/_config.py``", "Certificate creation and rotation."
   "``cmk/gui/nonfree/pro/saml2_auth/_connector.py``", "User creation and update during a SAML login."
   "``cmk/gui/ldap_integration/ldap_connector.py``", "User creation gate, takeover of SAML owned users."
   "``cmk/gui/watolib/activate_changes.py``", "User preservation during configuration pushes."
   "``cmk/update_config/plugins/actions/``", "The two update actions."
   "``tests/system/multisite/identity/``", "End to end tests across a central site and two remote sites."
   "``tests/unit/cmk/gui/userdb/test_identity_unification.py``", "Ownership and connector order rules."

See also
########

- :doc:`sec-auth-saml`
- :doc:`arch-comp-distributed`
- :doc:`sec-boundaries`
- `Werk #22208: Support SAML on remote sites and allow per-site authentication configuration <https://checkmk.com/werk/22208>`_
- `Werk #18500: REST-API site management, authentication_connections <https://checkmk.com/werk/18500>`_
- `User manual: Distributed monitoring <https://docs.checkmk.com/latest/en/distributed_monitoring.html>`_
