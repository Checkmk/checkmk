==============
Host relations
==============

Introduction and goals
======================

A management board (BMC, e.g. HPE iLO or Dell iDRAC) is monitored in Checkmk as
a host of its own, next to the OS host running on the same hardware. Without a
link between the two, only the operator knows that "this board belongs to that
OS host". To find out whether a problem is caused by the hardware or by the
software, they have to know the naming convention and open the second host by
hand.

Host relations bring this link into the product. A relation is configured in
Setup, either in the properties of a single host or for many hosts at once with
the relation detection. In the monitoring GUI the relations show up on the page
"All hosts" (``monitor_all_hosts.py``): as a column with the number of related
hosts, and as cards of the related hosts (with their state) in the host
slide-in. The classic views, including the view "All hosts" (``allhosts``), do
not show relations.

Relations are a GUI feature. The public REST API neither reads nor writes them;
its host endpoints only keep what is stored (see `Data model`_).

At the moment "Management board" is the only kind of relation. The model itself
is not specific to management boards, though: adding another kind is mostly one
new entry in a table (see `Adding a relation kind`_).

Relations are metadata. They do not change how a host is checked or alerted on.
They are also unrelated to the ``parents`` attribute, which is about network
reachability. The legacy management board settings of a host
(``management_address``, ``management_protocol`` etc.) are an older, separate
mechanism and are not touched by this component.

The work is tracked in CMK-39466 (model, Setup and monitoring) and CMK-39967
(relation detection).

Terms
-----

* **Kind:** What a relation means, e.g. ``management``. The GUI calls it
  "Type".
* **Direction:** The end of a relation a host sits at. ``parent`` is the
  managing end (for ``management``: the *board*), ``child`` the managed end
  (the *OS host*). ``symmetric`` is for kinds that read the same from both
  sides. ``parent`` and ``child`` have nothing to do with the ``parents``
  attribute.
* **Link:** One entry of the ``relations`` attribute of a host: kind, direction
  and related host.
* **Half:** The link one of the two hosts stores about a relation. A relation
  consists of two halves.
* **Pair:** Two hosts and everything they store about each other.
* **Related host:** The host at the other end of a relation, called counterpart
  in the code.
* **Mirror:** Writing the other half onto the related host whenever a host's
  relations change.
* **Finding:** One source of evidence the relation detection looks at: a word in
  host names, or a label or custom host attribute whose values hosts share.
* **Deciding end:** The end of a kind that a finding identifies, e.g. the board
  for ``management``.
* **Marker:** A word or value that tells which host of a group sits at the
  deciding end.
* **Scan** and **store run:** The two background jobs of the relation
  detection. The scan (``RelationScanBackgroundJob``) finds relations, the
  store run (``RelationDetectionBackgroundJob``, shown as "Store detected
  relations") stores the accepted ones.

"The user may see a host" means different things in the parts of this
component:

* **Setup** (host properties, mirror, validation): the user may read the host,
  which depends on the contact groups of the host and its folder.
* **Relation detection:** the host is in a folder the user may read.
* **Monitoring GUI:** Livestatus returns the host for the user (``AuthUser``).

Requirements overview
---------------------

The main requirements we need to meet are:

* A relation concerns both hosts. Editing one end must always edit the other end
  as well.
* A relation can connect hosts in different folders and on different sites of a
  distributed setup.
* Saving a host must not be blocked by something somebody else broke on the
  other host (e.g. a deleted host or a contradiction stored there). Only what the
  save itself introduces may be refused.
* The stored format describes the structure of a relation (kind and direction),
  not its wording. The wording can then be changed and translated without
  migrating any configuration.
* Older Checkmk versions must be able to read configurations written by newer
  ones and skip relations they do not know, without losing the others. Saving a
  host in the host properties must keep the relations of unknown kinds, as the
  host properties cannot show them (see `Risks and technical debts`_ for what is
  still dropped).
* The page "All hosts" and the host slide-in must only show what the user is
  allowed to see. A related host the user cannot see is neither shown nor
  counted there.
* Setting up relations for a fleet of tens of thousands of hosts must not mean
  editing every host by hand. At the same time nothing may be stored that the
  user did not confirm.
* In a multi-tenant setup (``ultimatemt``) a relation must never cross customers,
  and no site may learn which hosts another customer has.

Quality goals
-------------

1. **Consistency:** Both halves of a relation agree after every write that
   changes the pair. Where they do not (manual edits, locks, an interrupted
   rename), the monitoring GUI still shows the relation on both hosts, and
   ``validate_host_relations`` reports it in Setup.
2. **Robustness:** A broken related host does not prevent saving a host, unless
   the save changes the relation to that host. A failed export does not fail the
   activation (outside of debug mode).
3. **Confidentiality:** The page "All hosts" and the host slide-in only reveal
   related hosts the user may see, and a multi-tenant site only learns about
   hosts of its customer. The raw custom variable does not meet this goal (see
   `Security considerations`_).
4. **Compatibility:** Configurations of other Checkmk versions are read without
   failing, and relations of unknown kinds are kept where possible.
5. **Scalability:** What one host shows stays bounded, however many relations it
   has. Work that grows with the whole installation (scan, export, relation
   count) runs in the background or once per request, never once per relation.

The stakeholders are the operators who configure relations in Setup, the users
who follow them in the monitoring GUI, and the developers who add further kinds.

Architecture
============

White-box overall system
------------------------

.. uml::

    package "Central site: Setup" {
        [Host properties\nand folder view] as dialog
        [Host REST API] as host_api
        [Relation detection page] as detection_page
        [Detection REST API\n(internal)] as detection_api
        [Background jobs\n(scan / store run)] as jobs
        [Host rename] as rename
        [Hosts and folders\n(mirror)] as hosts
        [validate_host_relations\n(validate-host hook)] as validation
        [FolderValidators\n(edition hook)] as validators
        [Activate changes] as activation
        [Relations export] as export
        [Site snapshots\n(ultimatemt only)] as snapshots
        file "hosts.mk\n(relations attribute)" as hosts_mk
        file "conf.d/relations.mk" as relations_mk
    }

    package "Every site (central site included)" {
        file "conf.d/relations.mk\n(_CMK_RELATIONS)" as site_relations_mk
        [Core configuration\nand monitoring core] as core
        () Livestatus as livestatus
    }

    package "Monitoring GUI (site of the user)" {
        [Page "All hosts"\nand host slide-in] as views
        [Monitor hosts REST API\n(internal)] as monitor_api
    }

    package "cmk/gui/utils" {
        [Data format\nand table of kinds] as shared
    }

    dialog ..> hosts: create / edit / delete host
    dialog ..> validation: show problems
    host_api ..> hosts: create / edit / delete host
    rename ..> hosts: rename links
    detection_page ..> detection_api: use
    detection_api ..> hosts: read hosts (suggestions)
    detection_api ..> jobs: start / read result
    jobs ..> hosts: read hosts / store relations
    hosts ..> validators: validate_host_relation
    jobs ..> validators: validate_host_relation
    hosts ..> hosts_mk: save both hosts
    activation ..> export: before building snapshots
    export ..> hosts: read all hosts
    export ..> relations_mk: write if changed
    relations_mk ..> site_relations_mk: config sync (not ultimatemt)
    activation ..> snapshots
    snapshots ..> relations_mk: read
    snapshots ..> site_relations_mk: filtered per customer
    core ..> site_relations_mk: read when generating the config
    core - livestatus
    views ..> monitor_api: use
    monitor_api ..> livestatus: custom_variables
    hosts ..> shared
    export ..> shared
    monitor_api ..> shared

The component consists of two parts:

* **Setup** stores the relations in the ``relations`` host attribute and resolves
  them during the activation of changes.
* **The monitoring GUI** only reads the resolved relations from the
  ``_CMK_RELATIONS`` custom host variable via Livestatus.

The monitoring GUI knows nothing about Setup, and Setup knows nothing about
Livestatus. They only share the data format and the table of kinds, which
therefore live in ``cmk/gui/utils``, a place that belongs to neither of them.

Data model
----------

Each host stores its relations as a list of links in its own ``relations``
attribute in ``hosts.mk``. This is what the board ``srv-01-ilo`` stores:

.. code-block:: python

    {
        "relations": [
            {"kind": "management", "direction": "parent", "host": "srv-01"},
        ],
    }

The ``direction`` is the end of the relation the *storing* host sits at. So the
link above reads like the row in the host properties: "this host is management
board of ``srv-01``".

Both halves of a relation are stored. In the example, ``srv-01`` holds the link
``{"kind": "management", "direction": "child", "host": "srv-01-ilo"}``.

The kind ids and directions end up in the configuration of every installation.
Renaming them would require a migration (see :doc:`arch-migrations`). The
titles shown in the GUI can be changed freely.

A link has exactly these three fields, all non-empty strings, and the
directions are a closed set. A later version that needs a new meaning adds a
kind, which this version keeps (see `Risks and technical debts`_). Data about a
relation beyond these fields belongs in an attribute of its own or comes with a
migration, as this version drops it on every write.

The attribute is intentionally not inherited from folders: a value on a folder
would point all its hosts to the same board. It is not offered in bulk edit
either: one value would point all selected hosts to the same board, rewrite
the folder of that board once per selected host, and leave the selection half
applied if one write is refused. The host cleanup does not offer it either: it
would save the folder of each related host once per selected host, and leave
the selection half applied if one write is refused. The attribute is not shown
in the host search and the host table. The
host endpoints of the REST API do not expose it, but keep it: a full
replacement of the attributes carries the stored value over, and removing it is
refused.

For the monitoring each host with relations gets a ``_CMK_RELATIONS`` custom
host variable during the activation. It contains the same information as JSON,
plus the site that monitors the related host. This is the variable of
``srv-01``:

.. code-block:: json

    [{"kind": "management", "direction": "child", "host": "srv-01-ilo", "site": "remote1"}]

The monitoring GUI only reads Livestatus, which cannot tell on which site the
related host is monitored. With the site in the variable, it can ask that site
for the related host instead of asking all of them.

Code
----

Shared:

* ``cmk/gui/utils/host_relations.py``: The data formats and their parsers. It
  defines the directions, the stored link, the resolved relation and the name of
  the custom variable. It only depends on the standard library and ``cmk.ccc``.
* ``cmk/gui/utils/host_relation_kinds.py``: The table ``RELATION_KINDS`` with all
  kinds of relations, their (translatable) wording and the words that identify a
  kind in host names (``ilo``, ``idrac``, ``bmc``, ...).

Setup:

* ``cmk/gui/watolib/host_relations.py``: The form of the host attribute, the
  rules for conflicting relations, the resolver used by the export, the note
  in the host deletion dialog, and ``with_links_not_shown``, which the host
  properties use to keep the links of kinds they do not show. ``Host`` itself
  stores what it is given.
* ``cmk/gui/watolib/hosts_and_folders.py``: The mirror (``plan_relation_mirror``,
  ``apply_relation_mirror``, ``RelationMirrorBatch`` for several hosts saved in
  one go, ``relation_mirror_folders``, the cleanup after a deletion, and the
  ``Host`` methods ``set_relations_about`` and ``rename_relation``). Creating,
  editing and deleting hosts, the relation detection and renaming write
  relations through these functions. A new writer
  has to resolve related hosts with ``counterpart_resolver`` and save their
  folders through ``relation_mirror_folders``: ``FolderTree.host()`` can return
  a different instance of the folder being saved, and a change made on that
  instance is silently lost.
* ``cmk/gui/watolib/host_rename.py``: Renaming a host rewrites the links on its
  related hosts.
* ``cmk/gui/watolib/builtin_attributes.py``: The host attribute
  ``HostAttributeRelations`` and the ``validate-host`` hook
  ``validate_host_relations``.
* ``cmk/gui/watolib/host_attributes.py``: ``collect_attributes`` lets every
  attribute merge the submitted value with the stored one
  (``ABCHostAttribute.merge_with_stored``). The relations attribute uses this to
  keep the links of kinds the host properties have no row for.
* ``cmk/gui/wato/pages/hosts.py`` and ``cmk/gui/wato/pages/folders.py``: The
  deletion note in the host properties and in the folder view, and cloning a
  host without its relations.
* ``cmk/gui/openapi/api_endpoints/host_config/_utils.py``: The host endpoints of
  the REST API neither expose the attribute nor let a request remove it.
* ``cmk/gui/watolib/host_relations_export.py``: Writes the resolved relations
  for the monitoring core. ``cmk/gui/watolib/activate_changes.py`` calls it in
  ``_pre_activate_changes``.
* ``cmk/gui/watolib/host_relation_detection.py`` and
  ``cmk/gui/watolib/host_relation_scan.py``: The relation detection and its
  background jobs. The module docstrings explain the heuristics.
* ``cmk/gui/openapi/api_endpoints/host_relation_detection/``: The internal REST
  endpoints used by the detection page.
* ``cmk/gui/wato/pages/host_relation_detection.py`` and
  ``packages/cmk-frontend-vue/src/mode-host-relation-detection/``: The Setup page
  "Relation detection".
* ``cmk/gui/watolib/registration.py``: Registers the attribute, the
  ``validate-host`` hook, the replication path and the two background jobs.
  ``cmk/gui/general_config.py`` holds the default log level, and
  ``cmk/config_anonymizer/plugins/hosts.py`` anonymizes the related host names.
* ``cmk/gui/nonfree/ultimatemt/host_and_folder_validators.py``
  (``validate_host_relation``) and
  ``cmk/gui/nonfree/ultimatemt/managed_snapshots.py`` (``relations_of_site``):
  The rules of the multi-tenant edition.

Monitoring GUI:

* ``cmk/gui/monitor/hosts/``: Reads the relations from Livestatus for the page
  "All hosts". The queries and the visibility rule are in ``_impl.py``, the
  limit and the response models in ``_models.py``, the sort column in
  ``_sorting.py``, the REST fields in ``_api/``, and the check whether the
  column is shown at all in ``_pages/``.
* ``packages/cmk-frontend-vue/src/monitoring/all-hosts/``: The relations column
  and the related host cards in the slide-in
  (``components/slide-in/HostRelationsSection.vue``).
* ``cmk/gui/painter/painters.py``: The legacy painter "Host custom
  attributes" hides the variable.

Interfaces
----------

* Host attribute ``relations`` in the host properties, section "Related hosts".
  Each row consists of the type (currently always "Management board"), the
  direction and the related host. Problems with the stored relations
  (``validate_host_relations``) are shown in the host properties and in the
  folder view, like a missing parent.
* Setup page "Relation detection" (``wato.py?mode=host_relation_detection``). It
  is linked in the "Related" section of the folder menu as "Detect related
  hosts" and requires the permissions ``wato.edit``, ``wato.hosts`` and
  ``wato.edit_hosts``.
* Internal REST API "Host relation detection" (not part of the public API). All
  endpoints require the same permissions as the page. This includes the
  read-only endpoints, as in the service discovery.
  ``background_jobs.delete_jobs`` is declared as optional, as reading the state
  of a job asks whether the user may delete it:

  * ``POST /domain-types/host_relation_detection/actions/suggest/invoke``: What
    the hosts reveal (words in host names, labels and attributes shared by few
    hosts).
  * ``POST /domain-types/host_relation_detection/actions/scan/invoke``: Starts a
    scan.
  * ``GET /objects/host_relation_detection/{job_id}``: State of a scan or of a
    store run.
  * ``GET /objects/host_relation_detection/{job_id}/collections/rows``: One page
    of what a scan found (``part=relations``, ``groups`` or ``conflicts``), or
    of the pairs a store run could not write or found related in another way
    (``part=failed``).
  * ``POST /domain-types/host_relation_detection/actions/accept/invoke``: Starts
    a store run.

* Generated file ``etc/check_mk/conf.d/relations.mk``, which sets
  ``explicit_host_conf["_CMK_RELATIONS"]``. It is registered as replication path
  ``host_relations``.
* Livestatus columns ``custom_variables`` and ``custom_variable_names`` of the
  ``hosts`` table. Livestatus strips the leading underscore, so the variable is
  called ``CMK_RELATIONS`` there.
* Internal REST API "Monitor Hosts": the field and sort column
  ``num_relations`` in the host list, and ``relations`` / ``more_relations`` in
  the host overview. The overview lists at most ``MAX_RESOLVED_RELATIONS``
  related hosts the user may see. ``more_relations`` says that the user may see
  more than that.
* Global setting "Logging" > "Host relations" (logger
  ``cmk.web.host_relations``, default "Warning"), see `Operation`_.
* Edition hook ``validate_host_relation`` of ``FolderValidators``. It
  lets an edition refuse a relation between hosts of two sites. Only
  ``ultimatemt`` uses it, to refuse relations between customers.
* Pending changes: a related host written as a side effect gets a change of its
  own with the action ``mirror-relation``. Renaming adds ``rename-relation``,
  the store run ``detect-relations``. These show up in the audit log of the
  host.

Runtime view
============

Editing a host
--------------

When a user saves a host in Setup, ``Host.edit()`` (or ``Folder.create_hosts()``
for a new host) does the following:

1. It checks the new relations for conflicts: a link to the host itself, two
   different directions of one kind to the same host, or the same link twice.
   The last two are only checked for kinds this version knows. Such a conflict
   is only refused if the save introduces it. A conflict that was already
   stored before does not block the save. A value that cannot be read at all is
   refused.
2. It calculates what each affected related host has to store about the saved
   host. This is always the complete state of the pair, not a diff. If two users
   edit the same relation at the same time, the last save wins and both halves
   still agree.
3. Before anything is written, it checks every related host whose pair the save
   changes:

   * If the pair keeps a relation, the related host must exist and be visible to
     the user, and the edition must accept the two sites
     (``validate_host_relation``).
   * A related host that already stores the wanted half is skipped.
   * Otherwise its ``relations`` value must be readable. Writing the half
     into a value that cannot be read would replace it, and with it every
     other relation of that host.
   * Its folder must be writable for the user and not locked.
   * The change of the related host goes through ``Host.apply_edit()``: the
     user needs write permission for the host, the host must not be locked
     (not even by Quick setup), and the edition hook ``validate_edit_host`` is
     asked.
   * If the user may not see the related host, the error message does not name
     its folder or contact groups.

4. It writes the saved host and the related hosts (each folder only once). The
   related hosts get a pending change of their own and are activated together
   with the saved host.

Pairs the save does not change are not touched. This way a broken related host
(locked, not writable, half missing) never blocks saving the host the user is
working on, as long as the save leaves that relation alone. The one exception:
if the save changes the site of the host, the edition hook is asked about all
of its relations (see below).

When several hosts are created at once, the related hosts are looked up among
the hosts that already exist. A relation to a host created in the same call is
refused like one to a missing host, so a board and its OS host cannot be created
together with their relation.

Deleting, renaming, cloning hosts and changing their site
---------------------------------------------------------

* **Deleting** a host or a folder removes the other half of each relation the
  deleted host stores from the related hosts. A half that only the related host
  stores stays behind. This cleanup runs with superuser rights, so a user can
  delete their own host even if the related host is in a folder they may not
  write to. Locked folders and hosts locked by Quick setup are still respected,
  so a half stays behind there as well. Such a half is reported by
  ``validate_host_relations`` and ignored by the export. The delete confirmation
  of a host lists the first ``MAX_LISTED_RELATED_HOSTS`` related hosts.
* **Renaming** a host updates all links to the old name, just like for parents.
  If the user may not write the folder of a related host, the rename stops
  there, as it does for parents: the host is renamed, but that related host
  and everything the rename would have changed after it keep the old name.
  The related host then stores a half that points to a missing host.
* **Cloning** a host does not copy its relations, because the related hosts
  would not know about the clone.
* **Changing the site** of hosts asks the edition hook about each relation of
  every host that changes its site. This applies to moving hosts or folders,
  changing the ``site`` attribute of a host or a folder, and removing it in the
  host cleanup. Related hosts that are moved along are not checked. Hosts with
  an explicit ``site`` attribute do not change their site when their folder
  does, and are not checked either.

Activate changes
----------------

Before the configuration snapshots are created, the activation calls
``export_host_relations`` on the central site:

1. ``resolve_all_relations`` reads the ``relations`` attribute of every host.
   A malformed value is skipped with a warning in the log; a single broken link
   skips all links of that host. Links to unknown kinds or directions, with a
   direction their kind does not have, to the host itself or to hosts that do
   not exist any more are dropped (logged on debug level).
2. For each link the relation is added to the host and the reverse relation to
   the related host. Even if a ``hosts.mk`` only holds one half (e.g. after a
   manual edit), both hosts get the relation in the monitoring.
3. ``relations.mk`` is only written if its content has changed: a file in
   ``conf.d`` that is newer than the last core config makes the CMC do a full
   instead of an incremental config compilation.

The export walks the whole folder tree on every activation and asks each related
host once for its site. If it fails, the error is logged and the activation
continues (in debug mode the error is raised). The sites keep the previously
exported relations.

``relations.mk`` is synced to all sites, except in ``ultimatemt`` (see
`Multi-tenancy (ultimatemt)`_). Each core only sets the variable for the hosts
it monitors.

Monitoring
----------

* The **relations column** on the page "All hosts" is only offered if at least
  one host the user can see carries the ``CMK_RELATIONS`` variable. Once
  offered, it shows 0 for hosts whose related hosts are all hidden from the
  user. To count the relations of each host, the page asks Livestatus once, on
  all sites, which hosts carry the variable at all, with the permissions of the
  user. A relation
  is counted if the related host (by site and name) is in this set or, for
  users who see all hosts, is on a site that currently cannot be reached. Sites
  the user disabled do not count as unreachable.
* The **host slide-in** shows the first ``MAX_RESOLVED_RELATIONS`` related hosts
  the user may see, in the order of the export, with their state and service
  counts. ``more_relations`` says that there are more. It uses the same set of
  hosts and the same rule as the column, so up to that limit the number in the
  column matches the cards. The query that reads the state only names these
  hosts and only goes to their sites. The slide-in first shows a few cards
  and the others when the user expands the list.
* Both leave out related hosts the user may not see, hosts that no site knows
  any more, and hosts on a site the user disabled (that site is not asked). A
  related host only counts as existing if it carries the variable itself. This
  does not check that it carries this particular relation. Related hosts on a
  site that cannot be reached are shown with the note that the site is not
  available, but only to users who see all hosts.
* The monitoring GUI skips relations it cannot place (``kind_accepts``): those
  of an unknown kind, and those with a direction the kind does not have. It
  also skips relations to a name that is not a valid host name, because
  Livestatus cannot be queried for it. The parser ignores broken values, which
  may come from a site running a different Checkmk version.

Relation detection
------------------

The relation detection works like the service discovery: Checkmk proposes
relations, and the user confirms them. The module docstrings of
``host_relation_detection.py`` explain the heuristics; this section gives the
flow. The page is a wizard:

1. **Relation mapping.** The user selects the kind of relation and where to
   look: in the host names, in the host labels and custom host attributes, or
   both. The scan can be restricted to a folder, a site or both; relations with
   at least one host inside are found.

2. **Relation proposal.** The page asks the backend what the hosts reveal. This
   reads all hosts in folders the user may read, synchronously within the
   request (see `Risks and technical debts`_). It proposes words in host names
   (a host name that is another host name plus a word, e.g. ``srv-01-ilo`` or
   ``ilo.srv-01`` for ``srv-01``), and host labels or custom host attributes
   whose values each pick out one machine, like a serial number written by a
   CMDB. The user confirms what to use, and may add their own words, labels or
   attributes.

   Labels are only the explicit labels, the folder labels and the labels that
   come from host attributes; not the ones of host label rules and not the ones
   found by the service discovery. The detection reads the custom host
   attributes set on the host and its folders; the defaults of attributes
   nobody set are not read, as every host would carry them. The endpoints
   refuse built-in attributes (like the IP address): they describe how a host
   is monitored, not which machine it is.

3. **Relation review.** The scan reads the same hosts and stores its result as
   ``result.json`` in the job directory. The page reads it page by page. A scan
   can find three things:

   * *Pairs*: The name, or a shared value together with a marker, tells which
     host sits at the deciding end. A board with all blades of a chassis results
     in several pairs.
   * *Group questions*: Several hosts share a value, but nothing tells which one
     sits at the deciding end. The user selects it. Hosts that a pair already
     places are left out of the question. Kinds with a symmetric direction never
     produce group questions. A group in which the marker points at more than
     one host is dropped.
   * *Conflicts*: Two findings say different things about the same two hosts
     (a different kind or direction). Nothing is proposed until the user
     decides. If one of the two is already stored, the pair is shown as already
     stored instead. Two findings that say the same thing (e.g. the name and a
     serial number) are one pair, attributed to the finding the scan reports
     first.

   A value that too many hosts share is ignored, as it names a category (like a
   location) rather than one machine. For each pair the page shows whether it
   can be stored, is already stored, is stored differently, or cannot be written
   (and why). "Cannot be written" checks the same as the store run: locks, write
   permissions, a ``relations`` value that cannot be read and the edition hook
   ``validate_host_relation``.

4. **Summary.** The page sends the id of the scan, the findings to use and what
   the user changed (excluded rows, answered questions, resolved conflicts), not
   the full list of pairs. The store run stores the relations under the
   configuration lock. It does not call ``Host.edit()``, but writes both halves
   with the same functions (``set_relations_about`` and the mirror functions of
   ``hosts_and_folders``). It only stores pairs the scan proposed for storing,
   and checks each of them again: a relation added manually since the scan is
   not replaced, and a pair whose host was deleted since the scan is reported as
   not writable. It writes each folder once and creates one pending change per
   host. A pair that cannot be written is reported and the run continues with
   the others.

Deployment view
===============

Editions
--------

The host attribute, the export, the monitoring GUI part and the relation
detection (page, background jobs and REST endpoints) are available in all
editions. They are registered together with the other edition-independent Setup
modes and background jobs, not in the registration module of each edition.

Distributed setups
------------------

Relations are resolved on the central site, so they can connect hosts of
different sites. ``relations.mk`` is created on the central site and reaches the
remote sites with the normal config sync. Remote sites never run the export
themselves, not even during local activations triggered by cron jobs. A relation
is shown once the sites of both hosts have activated it (see `Operation`_). When
a host is edited, the sites of its related hosts are part of the change, so they
are activated together with the edited host.

Multi-tenancy (ultimatemt)
--------------------------

``validate_host_relation`` refuses relations between hosts of different
customers. The central site keeps the unfiltered ``relations.mk``, which is not
replicated. Instead, each remote site gets its own ``relations.mk`` built by
``relations_of_site``, which only keeps the hosts of the site and relations to
sites of the same customer. Each relation names the site the related host is
monitored on now, not the one the central file saw (a failed export keeps the
last file). Relations to hosts that no longer exist are dropped.

Operation
=========

* **Logging:** The logger ``cmk.web.host_relations`` logs a failed export as an
  error and a malformed ``relations`` attribute that the export skips as a
  warning. On "Debug" it also logs every relation that was dropped during the
  export, and why, and a summary of each export. A related host that keeps its
  half after a deletion because it is locked is logged as a warning on the
  general ``cmk.web`` logger, not on the relations logger.
* **Locking:** The store run holds the configuration lock for its whole run,
  like a bulk import of hosts. Storing relations for a large fleet blocks other
  Setup changes meanwhile: measured were 11 seconds for 2,500 pairs (about 4 ms
  per pair), with one pending change per host. For tens of thousands of pairs,
  restrict the scan to a folder or a site and store in several runs. The
  suggestions before the scan read 5,000 hosts in 0.2 seconds.
* **Housekeeping:** Scans and store runs are background jobs. Their
  housekeeping removes jobs older than a day and keeps a limited number per job
  type, counted over all users (``housekeeping_max_age_sec``,
  ``housekeeping_max_count``). The newest job of a type and running jobs are
  never removed. A scan that is still being reviewed can therefore disappear
  when other users scan a lot; the page then reports an unknown scan.
* **Core compilation:** Every activation that changes ``relations.mk`` makes the
  core of every site that receives the file compile its whole configuration.
  This includes the first activation after an update that creates the file.
* **Partial activation:** The export always contains all relations stored in
  Setup. If a site is activated before the site of a related host, the related
  host may not carry the variable yet, and the relation stays hidden until the
  other site is activated as well.
* **Troubleshooting:** If a relation is missing in the monitoring GUI, check in
  this order: the ``relations`` attribute of both hosts in Setup (the host
  properties report problems), ``etc/check_mk/conf.d/relations.mk`` on the site
  of the host, the variable in Livestatus (``lq "GET hosts\nColumns: name
  custom_variables\nFilter: custom_variable_names >= CMK_RELATIONS"``), and the
  messages of ``cmk.web.host_relations`` in ``var/log/web.log``.

Testing
=======

* ``tests/unit/cmk/gui/utils/test_host_relations.py`` and
  ``test_host_relation_kinds.py``: The formats and the table of kinds.
* ``tests/unit/cmk/gui/watolib/test_host_relations.py``: The form of the
  attribute, the resolver and the deletion note.
  ``test_host_attributes_relations.py``: Merging with the stored value.
  ``test_host_relations_export.py``: The export. ``host_relations_fakes.py``
  holds the shared fakes.
* ``tests/unit/cmk/gui/watolib/test_hosts_and_folders.py``: The mirror when
  hosts are created, edited, deleted and moved, and ``validate_host_relations``.
  ``test_host_rename.py``: Renaming.
* ``tests/unit/cmk/gui/watolib/test_host_relation_detection.py`` and
  ``test_host_relation_scan.py``: The detection and its jobs.
  ``tests/unit/cmk/gui/openapi/api_endpoints/test_host_relation_detection.py``
  and ``tests/openapi/test_openapi_host_relation_detection.py``: Its endpoints.
* ``tests/unit/cmk/gui/openapi/api_endpoints/test_host_config_attributes.py``
  and ``tests/openapi/test_openapi_host_config.py``: The host endpoints neither
  expose nor remove the attribute.
* ``tests/unit/cmk/gui/monitor/hosts/test_impl.py`` and ``test_sorting.py``, and
  ``tests/openapi/test_openapi_monitor_all_hosts.py``: The count, the sorting
  and the overview.
* ``tests/unit/cmk/gui/nonfree/ultimatemt/test_managed_snapshots.py`` and
  ``test_host_and_folder_validators.py``: The multi-tenant rules.
* ``packages/cmk-frontend-vue/tests/mode-host-relation-detection/`` and
  ``packages/cmk-frontend-vue/tests/monitoring/all-hosts/``: The Vue parts.

Security considerations
=======================

* **Write permissions:** Creating, changing or removing a relation writes both
  hosts. The user needs write permission for both hosts and both folders, and
  this is checked before anything is written. There are two exceptions. The
  cleanup after deleting a host runs with superuser rights, but only removes
  the link to the deleted host and still respects locks. Renaming a host
  rewrites the links on its related hosts without checking the permissions for
  these hosts, as for parents; their folders must be writable and not locked,
  or the rename stops there (see `Deleting, renaming, cloning hosts and changing
  their site`_).
* **Information in Setup:** Error messages about a related host the user may not
  see do not contain its folder or contact groups. Saving a relation to a
  related host the user may not see gets the same message as one to a missing
  host. ``validate_host_relations`` reports a missing related host only to users
  who may see all hosts (``wato.see_all_folders``); for other users it says
  nothing about related hosts they cannot see. Neither tells whether a hidden
  host exists. The stored links themselves are shown as they are, as for
  parents: the host properties and the delete confirmation name every related
  host, also one the user may not see (without a link to it). The detection
  only reads hosts in folders the user may read.
  Scan results are bound to the user who started the scan, because the
  endpoints do not require the permission to see the background jobs of others.
* **Information in the monitoring:** The page "All hosts" and the host slide-in
  only show and count related hosts the user may see. The raw ``CMK_RELATIONS``
  variable, however, contains the names and sites of *all* related hosts. The
  legacy painter "Host custom attributes" hides it, but the variable reaches
  everyone who can read the custom variables of the host:

  * Livestatus (``custom_variables`` of the ``hosts`` table),
  * the public REST API, e.g. the host collection with ``custom_variables`` in
    its columns or the service endpoints with ``host_custom_variables``,
  * the host macros ``$HOST_CMK_RELATIONS$`` and ``$_HOSTCMK_RELATIONS$``,
    which every custom host variable becomes,
  * with the CMC, the notification context, as ``HOST_CMK_RELATIONS``. With
    Nagios only if the notification template passes it on.

  Compared with parents, only the first two are a difference. The Livestatus
  columns ``parents`` and ``childs`` leave out hosts the user may not see. This
  works because a parent is monitored on the same site, so the core knows its
  contacts. A related host is often monitored on another site, which the core
  cannot ask. The notification context of parents is no stricter:
  ``HOSTCHILDREN`` lists all descendants. The variable is an internal format,
  like ``_FILENAME``, and not meant to be read by scripts.

* **Distribution of the export:** Except for ``ultimatemt``, every site gets the
  complete ``relations.mk`` with the relations of all hosts of all sites. These
  sites already get the complete Setup configuration of all hosts, so the file
  reveals no host they do not know already.
* **Input handling:** Both parsers treat their input as untrusted: the attribute
  may come from a manually edited ``hosts.mk``, the variable from a site with a
  different Checkmk version. The parser of the attribute validates host names.
  The parser of the variable checks the structure (JSON, a list of objects,
  known directions, non-empty kind, host and site). It leaves the conversion of
  host names to the reader, which skips a name that is not a valid host name.
  Whether the kind is known is asked with ``kind_accepts``. The site is only
  used to address the query and is not checked further. The export writes the
  values with ``repr`` into the ``.mk`` file.
* **Resource usage:** A scan reads all hosts in folders the user may read. It
  runs as a background job and not within a request. The suggestions before the
  scan read the same hosts within the request (see
  `Risks and technical debts`_).

Architecture decisions
======================

* **Both halves are stored.** Every host knows its relations without looking at
  other hosts, so the host properties, the deletion dialog and the validation
  never search the whole folder tree. The price is the mirror that keeps both
  halves in sync (see `Risks and technical debts`_). *Alternative:* store one
  half and derive the other on read. Every reader of a host would then have to
  scan all hosts.
* **A write states the whole pair, the last writer wins.** The mirror replaces
  what the related host stores about the saved host instead of applying a diff.
  A flipped direction is then one write, and two concurrent edits of the same
  relation still end with both halves in agreement. *Alternative:* diffs, which
  can leave two contradicting halves behind.
* **The deletion cleanup acts with superuser rights.** Deleting a host must
  neither fail over a relation nor leave a link to a host that no longer
  exists, even where the user may not write the related host. Locks are still
  respected.
* **Relations are resolved during the activation and written to a file of their
  own.** The reverse relations belong to hosts in other folders, and the site
  of a related host is only known for the whole tree. The usual way of a host
  attribute into the core (its folder's ``hosts.mk``) knows neither.
* **A custom host variable carries the relations into the monitoring.** It
  reuses ``explicit_host_conf`` and the ``custom_variables`` column, which every
  core already supports. *Consequences:* the raw value reaches everyone who can
  read the custom variables of the host (see `Security considerations`_),
  Livestatus cannot sort by the number of relations, and a change of
  ``relations.mk`` makes the CMC compile its whole configuration (see
  `Operation`_).
* **The structure is stored, not the wording.** Kind ids and directions are
  stable identifiers; titles live in ``RELATION_KINDS`` and can change without a
  migration.
* **A model of its own, not an existing attribute.** ``parents`` describes
  network reachability and changes how the core checks and notifies. The legacy
  ``management_*`` attributes describe a board on the same host, not a host of
  its own. Neither can express a relation between two monitored hosts.
* **The monitoring GUI reads Livestatus only.** It does not depend on Setup
  code, and it works against cores whose configuration another Checkmk version
  wrote.
* **The detection proposes, the user confirms.** It reads what the hosts already
  carry (names, labels, custom host attributes) and stores nothing that was not
  confirmed. *Alternative:* a ruleset with matching rules that creates relations
  dynamically. This was dropped: the user would have to describe in regular
  expressions what the configuration already says. The detection reads
  everything from Setup rather than from the monitoring, so that a host the core
  does not know yet is found as well.
* **A scan is kept where it was made.** A large fleet proposes tens of thousands
  of relations. The scan stores them in its job directory, the page reads them
  a page at a time, and accepting names the scan and what the user changed
  instead of every pair. The service discovery keeps its preview the same way.
* **The store run writes per folder, not per pair.** ``Host.edit()`` saves the
  folder on every call and records a change per half. The store run collects
  what it changes and writes each host once and logs it once.
* **The detection endpoints are internal.** They only serve the detection page
  and can change with it.

Adding a relation kind
======================

A new kind is a new ``DirectedRelationKind`` or ``SymmetricRelationKind`` in
``RELATION_KINDS`` (``cmk/gui/utils/host_relation_kinds.py``). It needs an id
(a Python identifier), a title and the wording of its ends (both ends for a
directed kind, one for a symmetric kind). Conflict messages, the export and the
monitoring GUI work with the table. The detection only offers kinds with
``name_evidence``: it declares the words in host names and the deciding end,
also for pairs found by shared values. For a symmetric kind, a shared value
proposes pairs only if a word or marker names one host of the group; with
nothing marked it proposes nothing, as it never asks group questions.

In the host properties the type decides the rest of the row: a directed kind
offers its two ends, and a symmetric kind just shows its one end. The relations
column of the page "All hosts" counts relations of every kind this version
knows.

A kind that relates many hosts to one, like virtual machines to their
hypervisor, makes the variable of that one host large. Such a kind has to
decide on a limit (see `Risks and technical debts`_).

The tests of the table (``test_host_relation_kinds.py``) pin the set of kinds
and have to be extended with the new one. The tests of the host properties, the
detection and the monitoring GUI show which behavior depends on the kind.

Risks and technical debts
=========================

Ordered by priority.

1. Livestatus cannot sort by the number of relations. With a limit (1,000 hosts
   by default), the page "All hosts" sorts by it only within the hosts the
   limit kept, and the limit applies per site (the first hosts by name of each
   site). With more hosts than the limit, the hosts with the most relations
   can be missing. Sorting correctly would have to be solved where the page
   reads its hosts, which belongs to the page as a whole.
2. The names of custom host attributes are not checked against the ones
   Checkmk uses itself, and two of them collide with relations:

   * A custom host attribute named ``relations`` replaces the host attribute,
     as one named ``parents`` replaces the parents. The host properties then
     show a text field instead of "Related hosts". A host with a text value in
     it can no longer be saved at all, with or without relations, as every save
     reads the attribute as relations.
   * A custom host attribute named ``CMK_RELATIONS``, in any case, that is
     added to the monitoring configuration becomes the same ``_CMK_RELATIONS``
     custom variable and wins over the export, also when it is set on a
     folder. The monitoring GUI then shows its value as the relations of the
     host instead of the stored ones. Whoever may edit the host can so show
     relations to hosts they may not edit. The custom variables Checkmk sets
     itself, like ``_TAGS`` and ``_FILENAME``, win over a custom host attribute
     instead. The prefix ``CMK_`` only makes such a name unlikely.

3. The raw ``CMK_RELATIONS`` variable reveals the names and sites of related
   hosts to users who may see the host, but not the related host, via
   Livestatus and the REST API. The columns of the parents leave such hosts out
   (see `Security considerations`_). Nothing else about the related host is
   revealed.
4. Each relation is stored twice, and only the mirror keeps both halves in
   sync. A manually edited ``hosts.mk``, a locked related host or a rename that
   stops at a related host the user may not write can leave one half alone.
   The export compensates for this. ``validate_host_relations``
   reports contradictions and an unreadable value on the host itself, a half
   that points to a missing host, and a related host that does not store its
   half, stores a different one, or stores a ``relations`` value that cannot be
   read. It reports one problem at a time. Saving the host again does not
   repair this, as a save only writes the pairs it changes; adding or changing
   the relation on either host writes both. The detection does not repair it
   either: it treats a relation as stored if one half is.
5. If the export fails, the activation still succeeds (outside of debug mode)
   and the monitoring GUI shows outdated relations. The reason can only be found
   in ``web.log``.
6. The only mix of versions Checkmk supports is a downgrade to an older patch
   release of the same major version. Such a version keeps links of unknown
   kinds when a host is saved in the host properties, because its host
   properties cannot show them. Deleting or renaming a host covers links of
   every kind. On every write of the host, however, it drops
   links with unknown directions and any fields a newer version added to a
   link, as it rebuilds each link from kind, direction and host. This includes
   any edit of the host, also one that only changes its IP address, and writing
   the other half onto a related host. Saving a host in the host properties
   also drops links of a known kind with a direction that kind does not have.
   The contract in `Data model`_ keeps a newer version from relying on either.
7. When hosts are created or edited with relations, or the store run writes its
   folders, and writing one folder to disk fails halfway, nothing is rolled
   back: some hosts are written and some related hosts are left without their
   half. Saving again does not repair this, as the save no longer changes the
   pair. "Revert changes" restores the state of the last activation. Moving
   hosts between folders has the same gap.
8. The ``_CMK_RELATIONS`` variable of a host grows with the number of its
   relations, and nothing bounds its size. A management board carries a few
   dozen entries at most, as a blade chassis holds up to 32 servers. The
   notification context cuts each value at 65,536 bytes, which a few hundred
   entries reach; a notification script then gets JSON it cannot parse.
9. The suggestions of the relation detection read all hosts in folders the user
   may read, with their labels and attributes, synchronously within the
   request; only the scan runs in the background. Measured were 0.2 seconds for
   5,000 hosts, growing linearly with the number of hosts.

See also
========

* :doc:`arch-comp-gui`: the GUI the component is part of.
* :doc:`arch-comp-hosts`: the monitored hosts, which relations connect.
* :doc:`arch-comp-distributed`: the config sync that distributes
  ``relations.mk`` to the remote sites.
* :doc:`arch-comp-core`: the core configuration that reads ``relations.mk``.
* :doc:`arch-comp-livestatus`: the query interface the monitoring GUI reads the
  relations from.
* :doc:`arch-comp-gui-vue`: the Vue integration used by the detection page and
  the "All hosts" page.
