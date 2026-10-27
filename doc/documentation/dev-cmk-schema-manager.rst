==========================
Database schema migrations
==========================

A component that keeps its data in a database owns that database's schema. The
schema changes over time, and every site has to end up at the schema the
installed Checkmk version expects, no matter which version created the database.
``cmk-schema-manager`` (``packages/cmk-schema-manager``) applies these changes as an
append-only chain of revisions. Today it supports SQLite only.

Design
======

.. uml::

    [component] as app
    [cmk.schema_migrations.<component>] as migrations
    [cmk.schema_manager] as manager
    [omd create / omd update / omd backup] as omd
    database "database" as db

    migrations ..> manager: declares ManagedDatabase
    omd ..> manager: discovers and applies
    manager ..> db: applies revisions
    app ..> migrations: imports declaration
    app ..> manager: connects
    app ..> db: reads and writes

A component declares its database as a ``ManagedDatabase`` in the
``cmk.schema_migrations`` namespace, where omd finds it by plugin discovery. The
declaration lives apart from the component on purpose: the module layer check
forbids a migrations module from importing the component it migrates, so a revision
cannot silently change when the component's code changes later. The component may
import its declaration, e.g. to call ``ensure_schema``.

Lifecycle
---------

``omd_lifecycle`` decides which omd events handle the database:

``create``
    ``omd create`` creates the database, so every site has it from the start.
    Together with ``update``, ``omd update`` also creates it on sites that
    predate the database; without ``update``, those sites never get it.

``update``
    ``omd update`` applies pending revisions. It tries every database and then
    fails if any of them failed: Checkmk cannot guarantee a working site with an
    outdated schema, but the log should name every broken database at once.

``backup``
    ``omd backup`` snapshots the database through SQLite's backup API, which stays
    consistent while the database is being written to.

An optional feature leaves out ``create`` and calls
``ensure_schema`` when it starts, so sites that never use the feature do not get its
database.

At runtime, connecting never creates a missing database. A database that disappears
from a running site is a severe error, and an empty database would only hide it.

Usage
=====

Give the database its own package in the ``cmk.schema_migrations`` namespace: one
module per revision, named after its id, and the ``ManagedDatabase`` in
``__init__.py``, bound to a name starting with ``schema_manager_`` (e.g.
``schema_manager_oauth``) -- discovery ignores it otherwise. To change the
schema, add a revision module and append it to the chain. Sites apply it on their
next ``omd update``, or, for a database outside ``update``, the next time its
component calls ``ensure_schema``.

For tests, ``cmk.testlib.schema_manager`` has ``RevisionTestSuite``, which checks
the chain, and ``migrated_connection``, which gives code under test a database at
the latest schema. For a revision
that migrates data, also add a test that applies the chain up to the revision before
it, inserts rows, applies the rest and checks the result.

Hints
=====

Never change a shipped revision
    The database only records the id of its last revision. Editing, reordering or
    removing a revision that already reached a site goes unnoticed on that site,
    and its schema silently differs from the one new sites get. Fix a mistake with
    a new revision.

Do not end the transaction
    ``upgrade`` runs inside the backend's transaction. Do not ``COMMIT``,
    ``ROLLBACK`` or ``BEGIN`` in it, also not in SQL passed to ``executescript``.
    ``RevisionTestSuite`` catches revisions that do.

Keep revisions self-contained
    A revision must produce the same result in every future version. Copy the
    constants and queries it needs instead of importing them from the component.

Rebuild tables instead of fighting ``ALTER TABLE``
    SQLite's ``ALTER TABLE`` cannot change a column's type or constraints. Use
    SQLite's `procedure to rebuild a table
    <https://www.sqlite.org/lang_altertable.html#otheralter>`_. Revisions run with
    foreign keys off, so dropping the old table does not cascade.

Plan for large tables
    A revision holds the database's write lock until it commits. Every writer of
    the database waits meanwhile, and ``omd update`` takes as long as the slowest
    revision. Avoid rewriting large tables when adding a column or an index is
    enough.

Handling upgrades
=================

To be defined. This section will describe how revisions interact with Checkmk
version upgrades, for example adding a revision on a stable branch.
