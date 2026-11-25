=================
Automation helper
=================

Introduction and goals
======================

An *automation* is a backend action that the GUI or the REST API asks ``cmk.base`` to perform, e.g. ``service-discovery``, ``analyse-host`` or the config generation during "Activate changes".
Each automation needs the site's configuration and the plug-ins loaded before it can run.
Without the helper, every call starts a new ``cmk --automation <name> ...`` process, which loads all of this again and then exits.

The automation helper is a site service that keeps the automation engine loaded.
It loads the configuration and the plug-ins once, serves automations over a Unix socket, and reloads the configuration when the relevant files change.

It was introduced with Checkmk 2.4.0 (`Werk #17678 <https://checkmk.com/werk/17678>`_) to speed up UI interactions such as service discovery and activating changes.
The speed-up depends on the size of the site: on small sites, activating changes is substantially faster, on large sites the difference is smaller.

Requirements overview
---------------------

* An automation must never run against a configuration that is older than the last change on disk.
* Results must be identical to those of ``cmk --automation``.
  Automations run as ``cmk --automation`` only when the helper is switched off or a caller asks for it, not when the helper fails.
* The helper must be optional.
  It is on by default, and can be switched off with ``omd config set AUTOMATION_HELPER off``, mainly for error diagnosis: if the helper is suspected to cause an error, switching it off shows whether the error goes away.

Architecture
============

White-box overall system
------------------------

.. uml::

    node "Site Apache" {
        [GUI / REST API] as gui
        [HelperExecutor] as helper_executor
        [SubprocessExecutor] as subprocess_executor
    }
    () "Unix socket" as socket
    node "cmk-automation-helper" {
        component "master process" {
            [uvicorn supervisor] as supervisor
            [watcher] as watcher
        }
        component "worker processes (2)" {
            [FastAPI app] as app
            [reloader task] as reloader
            [Automations engine] as engine
        }
    }
    database "Site Redis" as redis
    folder "etc/check_mk/\nvar/check_mk/" as files
    [cmk --automation] as cli

    gui --> helper_executor
    gui --> subprocess_executor
    helper_executor ..> socket: "POST /automation"
    socket - supervisor
    supervisor --> app: spawns
    app --> engine: execute()
    reloader --> engine: update()
    watcher ..> files: watches
    watcher --> redis: last change
    reloader --> redis: polls
    app --> redis: reload required?
    subprocess_executor ..> cli: runs

Code entry points:

``cmk/base/automation_helper/__init__.py``
    The launcher (``cmk-automation-helper``): daemonizes, starts the watcher and runs the server.

``cmk/automations/helper/``
    The server: ``make_application()`` builds the FastAPI app and its reloader, ``run_server()`` serves it on the Unix socket through uvicorn, ``run_watcher()`` runs the file watcher, ``Cache`` holds the Redis access, and ``config_from_disk_or_default_config()`` provides the defaults.

``cmk/automations/engine.py``
    ``Automations``, the engine that discovers the automation plug-ins and runs them.
    ``cmk --automation`` uses the same class, so both paths run the same code.

``cmk/automations/backends/``
    The clients: ``HelperExecutor`` talks to the socket, ``SubprocessExecutor`` runs ``cmk --automation``.

``cmk/automations/client.py``
    ``cmk-automation-client``, an internal command that sends a request to the helper.
    The init script uses it to wait until the helper is ready.

Interfaces
----------

The helper serves HTTP on the Unix socket ``tmp/run/automation-helper.sock``:

``POST /automation``
    Runs one automation and returns its result, like ``cmk --automation``.

``GET /health``
    Returns the time of the last successful configuration load.

The main caller is ``check_mk_local_automation_serialized()`` in ``cmk/gui/watolib/automations.py``.
It is used for all local automations of the GUI, the REST API, background jobs, and automation requests a remote site receives from its central site.
It uses the helper unless the helper is switched off or the caller forces the CLI path.

In the commercial editions, the notification spooler (``cmk --notify spoolfile``) also calls the helper.
When the helper is switched off, the spooler processes the notification in its own process (`Werk #22747 <https://checkmk.com/werk/22747>`_).
When the helper is switched on but unreachable, the notification fails and the spooler retries it.

Runtime view
============

**Processes.**
A master process runs the file watcher and the uvicorn supervisor, which starts two worker processes.
Each worker loads the configuration and the plug-ins itself and handles one request at a time.
The helper uses processes instead of threads because ``cmk.base`` is not thread-safe.

**Automation states.**
Each automation plug-in names a state factory.
The engine builds a state the first time an automation needs it and keeps it between requests.
On a configuration reload, the engine hands the new configuration to the existing states.
The helper saves time in three ways.
It doesn't start a process or load the plug-ins for each call.
It loads the configuration and updates the states only after a change.
And the reloader can do that in the background, before a request needs it.

**Change detection and reload.**
The watcher records the time of every change to the configuration files in Redis.
Redis is the channel between the one watcher in the master and the workers.

.. uml::

    participant "Setup / cmk" as writer
    participant "watcher\n(master)" as watcher
    participant "Redis" as redis
    participant "worker" as worker

    writer -> watcher: file change
    watcher -> redis: last change = now
    loop reloader task
        worker -> redis: last change?
    end
    worker -> worker: wait until changes settle,\nthen reload
    ...
    [-> worker: POST /automation
    worker -> redis: last change newer than my last reload?
    opt yes
        worker -> worker: reload now
    end
    worker -> worker: run automation

Two mechanisms work together:

* The reloader task in each worker reloads in the background, after a burst of changes (e.g. from "Activate changes") has settled.
* Before each automation, the worker checks Redis and reloads if its configuration is older than the last recorded change.
  The aim is that no automation runs on stale configuration, even if the reloader has not run yet.

The helper prefers a slower automation to a stale result.
When it cannot tell whether its configuration is current, e.g. because Redis is unreachable or the watcher may have missed changes, it reloads before every automation.
If the watcher may have missed changes, this lasts until the helper restarts.
When a reload fails, the helper reports the error instead of running the automation.

Deployment view
===============

The helper runs on every site where the OMD setting ``AUTOMATION_HELPER`` is ``on`` (the default).
In a distributed setup each site runs its own helper.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Location
   * - Processes
     - ``cmk-automation-helper[master]``, ``cmk-automation-helper[worker]`` (2)
   * - Init script
     - ``etc/init.d/automation-helper``
   * - Socket
     - ``tmp/run/automation-helper.sock``
   * - Logs
     - ``var/log/automation-helper/``

Risks and technical debts
=========================

1. **Limited concurrency.**
   Two workers handle one request each.
   A long automation, e.g. the config generation of an activation, occupies one worker, and further requests wait.
2. **cmk.base is not thread-safe.**
   This forces the process model, and every worker loads the configuration separately.

Related pages
=============

* :doc:`arch-comp-gui`: the main caller.
* :doc:`arch-comp-distributed`: remote automation calls, which a remote site runs through its own helper.
* :doc:`arch-comp-relay-monitoring`: which automations run during configuration, discovery and "execute active check".
