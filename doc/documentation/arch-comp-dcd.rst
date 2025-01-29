==================================
DCD - Dynamic configuration daemon
==================================

Introduction and goals
======================

The DCD is realizing the dynamic host configuration feature. The main capability
is:

* Automatic life cycle management of host configurations

This is especially useful in case of dynamic infrastructures where monitored
hosts are created and removed continuously and the monitoring is expected to
automatically adapt the changes.

The DCD is built in a generic way, and is not limited only to host creation.
The DCD forms the basis for future extensions of Checkmk which may dynamically
adjust the configuration. This can also mean the management of users, for
example. For this purpose the DCD works with so-called connectors. Each
connector can get information from a very specific type of source, and has its
own specific configuration.

The DCD is an Enterprise feature.

Architecture
============

The DCD is a daemon running in the context of an OMD site. The main thread of
the program is managing the configuration and the instances of the connectors
which are called connections.

Each of these connections is executed in a dedicated thread in synchronization
ticks of fixed intervals. The synchronization is separated in two phases. The
first phase is for gathering the information from external sources about hosts
and the second phase is creating or removing hosts from the Checkmk
configuration using the REST API.

Internal structure
------------------

These are the most important classes defining the structure of the DCD:

.. uml::

   object Manager {
     connection_manager: ConnectionManager
     command_manager: CommandManagerThread
   }
   object ConnectionManager {
     connections : [Connection1, Connection2]
     web_api : WebAPI
   }
   object CommandManagerThread {
     command_manager: CommandManager
   }
   object CommandManager {
   }
   object ConnectionThread1 {
     connection : Connection1
   }
   object ConnectionThread2 {
     connection : Connection2
   }
   object Connection1
   object Connection2
   object WebAPI
   Manager *-- ConnectionManager
   Manager *-- CommandManagerThread
   CommandManagerThread *-- CommandManager
   ConnectionManager *-- ConnectionThread1
   ConnectionThread1 *-- Connection1
   ConnectionManager *-- ConnectionThread2
   ConnectionThread2 *-- Connection2
   ConnectionManager *-- WebAPI

Distributed environments
------------------------

In a standalone site both phases are executed sequentially in one DCD.

In case a connection is assigned to a remote site, a synchronization tick is
executed by the DCD instances of the central and remote site in cooperation.
phase 1 is executed by the DCD of the remote site and phase 1 is executed by the
DCD of the central site.

TODO: Describe phase 1 and 2 of the synchronization

Runtime view
============

.. uml::

    control "Manager" as M
    control "Connection\nManager" as ConnManager
    control "Command\nManager" as CommManager
    participant "Connection N" as Connection
    participant Connector as Conn
    database "Filesystem" as FS
    control "REST\nAPI" as RA
    control "Automation\nAPI" as Auto

    M -> ConnManager : start
    M -> CommManager : start
    ConnManager -> Connection : create
    activate Connection
    |||
    Connection -> Conn : execute_sync
    deactivate Connection
    activate Conn

    group Phase1
        Conn -> FS : get_source_and_piggyback_hosts
        activate FS
        FS --> Conn : retrieve PiggybackHosts
        deactivate FS
    end
    |||
    alt local case
        Conn -> Conn : get result (piggyback hosts)
    else distributed case
        note right Conn
            On remote DCD instances, //phase 2// is not executed, but the
            result of //phase 1// is stored and fetched by the central DCD.
            The central DCD then executes //phase 2//.
        end note
        Conn -> RA : REST API call\nfetch_phase_one/invoke
        RA -> Auto : execute-dcd-command\n[get_phase1_result]
        Auto -> CommManager : get_phase1_result
        CommManager -> Connection : get_connection
        Connection -> Conn: serialize
        Connection <-- Conn: result:serialize
        CommManager <-- Connection : result:get_connection
        Auto <-- CommManager : result:get_phase1_result
        RA <-- Auto : result:execute-dcd-command\n[get_phase1_result]
        Conn <-- RA : result:REST API call
    end
    |||
    group Phase2
        note right Conn
            This phase receives the final output of //phase 1// as input.
        end note
        Conn -> Conn : Execution status OK?\n(abort/continue)
        Conn -> RA : Fetch all configured hosts
        activate RA
        RA --> Conn : Retrieve configured hosts
        deactivate RA

        Conn -> Conn : partition hosts to:\n* create\n* modify\n* delete
        |||
        Conn -> RA : create
        Conn -> RA : modify
        Conn -> RA : delete
        |||
        Conn -> RA : activate changes
        deactivate Conn
    end

Risks and technical debts
=========================

Hosts may exist as source hosts and piggyback hosts at the same time in
the data files, as this is not prevented by the layout of the data on disk.
This may lead to problems.


Interfaces
==========

.. uml::

  interface "Filesystem" as fs
  database "Piggyback" as piggyback
  interface HTTP as http_rest_api
  component "REST API" as rest_api
  component "DCD" as dcd

  rest_api - http_rest_api
  http_rest_api - dcd
  dcd - fs
  fs - piggyback

Plugin API
----------

The DCD has a extendable plugin API. The reference of that API can be found in
the Plugin API UI (Navigation > Help > Plugin API reference).

Such plugins can be placed by users in their site
`local/lib/python3/cmk/cee/dcd/plugins/connectors/`.

See also
~~~~~~~~
- `User manual: Dynamic host configuration <https://docs.checkmk.com/latest/en/dcd.html>`_

Risks and technical debts
=========================
1. With the DCD one can circumvent the permission for activating changes.
2. Any host can provide piggyback data for each host. A rogue agent can, with
   enabled piggyback data, inject monitoring data.
