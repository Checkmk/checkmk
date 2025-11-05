======================
Distributed Monitoring
======================

Introduction and goals
======================

In Checkmk we refer to a distributed monitoring when the monitoring system as a
whole consists of more than a single Checkmk site.

There are a number of good reasons for splitting monitoring over multiple sites:

* Performance: The processor load should, or must be shared over multiple
  machines.
* Organization: Various different groups should be able to administer their own
  sites independently.
* Availability: The monitoring at one location should function independently of
  other locations.
* Security: Data streams between two security domains should be separately and
  precisely controlled (DMZ, etc.)
* Network: Locations that have only narrow band or unreliable connections cannot
  be remotely-monitored reliably.

Checkmk supports various procedures for implementing a distributed monitoring.

The central component of the distributed setup is the :doc:`arch-comp-gui`. But
other components like :doc:`arch-comp-liveproxyd` and :doc:`arch-comp-mknotifyd`
are also involved in this feature.

Status: Basic principle
-----------------------

Checkmk is optimizing the amount of data replicated through a distributed
system. The monitoring status of the remote sites is not sent continuously to
the central site. The UI always only retrieves data live from the remote sites
when it is required by a user in the central site. The data is then compiled
into a centralized view. There is thus no central data holding, which means it
offers huge advantages for scaling-up!

The most important advantages are:

* *Scalable*: The monitoring itself generates no network traffic at all
  between central and remote site. In this way hundreds of locations, or more,
  can be connected.

* *Reliable*: If a network connection to a remote site fails the local
  monitoring nonetheless continues operating normally. There is no *hole* in the
  data recording and also no data *jam*. A local notification will still
  function. However, spooled notifications will be delayed until the connection
  is back again.

* *Simple*: Sites can be very easily incorporated or removed.

* *Flexible*: The remote sites are still self-contained and can be used for the
  operating in their respective location. This is then particularly interesting
  if the location should never be permitted to access the rest of the
  monitoring.

We have some commonly discussed architectural disadvantages:

* The client needs to have more features for combining the result sets from the
  different sites to a final result set.

* The data fetched via Livestatus is always gathered on demand, meaning the view
  rendering times are highly affected by the network connection reliability and
  performance between the Checkmk sites.

* Users in the central site can also only access historical information from a
  remote site in case the remote site is available.

* Changing host assignments to sites is more complex because the host-related
  data needs to be moved around.

In addition to that, we also have some limitations in the current implementation:

* The Livestatus server is currently implementing filtering and limiting.
  Sorting of results is not implemented by the Livestatus server. Instead it is
  exclusively implemented in the UI. Even if we would implement sorting in the
  Livestatus server, we could not completely drop it from the UI or Livestatus
  client, because only these components have all result sets of all sites
  available which need to be combined, then sorted and then limited. E.g. to
  produce top-X result sets. However, having sorting capabilities in the
  backend could make some things easier to implement.

* The livestatus server also does not support paginated querying which results
  in too many information being sent to the client in some cases.

* Livestatus client queries all remote sites in parallel and hands over one
  combined result set to the caller. This means the slowest responding site is
  determining the time that is needed to get the resulting rows.

* Users in the central site can also only access historical information from a
  remote site in case the remote site is available.

* Moving hosts (including their data) between sites is more complex. The data
  related to a host is stored in various files and directories. Some are
  exclusive to the host, which could be migrated easily. But there is also the
  monitoring history (text based storage), which we would have to extract the
  data of a host from, transport it to the target site and merge it with the
  monitoring history of the target site.

* Since most information is fetched live from remote sites, multiple
  simultaneous users looking at a single page would query all remote sites for
  the same information. Caching of queries and responses is possible, e.g. with
  the :doc:`arch-comp-liveproxyd`, but this is rarely used.

Use cases
=========

Use case 1: Central status view, independent configuration
----------------------------------------------------------

The simplest form of distributed setup. There are multiple Checkmk sites and you
want to have one site building an umbrella above all sites. The Monitoring UI
integrates the data of multiple sites to get a `central view on the status
<https://docs.checkmk.com/latest/en/distributed_monitoring.html#central_status>`_
information.

Use case 2: Central status view, central configuration
------------------------------------------------------

The standard form of distributed setup. You have the features of *Use case 1*
with the addition that the central site is used for `managing the configuration
<https://docs.checkmk.com/latest/en/distributed_monitoring.html#distr_wato>`_
of all sites.

Use case 3: Viewer sites
------------------------

You can extend *Use case 1* and *Use case 2* with a number viewer sites. The
configuration is basically the same as *Use case 1*.

Use case 4: View remotely monitored hosts in gapped networks
------------------------------------------------------------

This use case is addressed with a different architecture than the Livestatus
based use cases above. It uses a push based approach where host- and service
configuration and state dumps can be pushed from a remote site.

This is useful for situations with separated (gapped) networks, or even a strict
one-way data transfer from the periphery to the center there is a `push method
<https://docs.checkmk.com/latest/en/distributed_monitoring.html#livedump>`_
using Livedump, or respectively, CMCDump. The scenario is described well in
the linked chapter of the user manual.

Interfaces between sites
========================

.. uml:: arch-comp-distributed-interfaces.puml

Livestatus is for status
------------------------

Livestatus is the central unified interface for transporting Monitoring status
information from remote sites to the central site. This is the single
communication channel used by the status UI.

The :doc:`arch-comp-liveproxyd` is helping the UI to manage the connections in
the commercial editions.

TODO: Document how to debug these

HTTP API of Setup (Remote automation calls)
-------------------------------------------

The distributed configuration communication is realized using HTTP(s). The
remote site offers various HTTP endpoints the central site can use to control
the remote site. These are named *Remote automations* or *Remote WATO
automations*.

Please note: The *Automation calls*, named *checkmk-automation* in the
description below, are not only used in distributed setups. They are also used
in single sites to transport information between the Setup and the Checkmk base
(`cmk.base`) components.

Authentication: Site login
``````````````````````````

During configuration an *admin* user needs to establish a site level trust
between the central and the remote site (the remote site trusts the central
site) and hands over.

This diagram shows the process of a user configuring a remote site for a full
integration in the Monitoring and Setup.

.. uml:: arch-comp-distributed-site-login.puml

Implementation
``````````````

The API client (`do_remote_automation`, `do_site_login`), which is executed on
the central site to call remote automation commands, is implemented in
`cmk.gui.watolib.automations`.

The endpoints on the remote site are the generic `login.py` (implemented by
`cmk.gui.login`) and `automation_login.py` (implemented by
`cmk.gui.wato.pages.automation.ModeAutomationLogin`) to perform the site login
(see below).

The actual implementation of the automation commands is `automation.py`
(implemented by `cmk.gui.wato.pages.automation.ModeAutomation`)

We currently have three different types of automation commands:

* *checkmk-automation*: Calls *Automation calls* (aka *Checkmk base automations*)
  (`cmk --automation COMMAND...`) which are implemented by the component *cmk.base*.
* *push-profile*: Process a user profile synchronization (TODO: Clarify why this
  is handled differently than the following type of commands)
* Commands registered with the `automation_command_registry` (e.g.
  `AutomationReceiveConfigSync` and `AutomationGetConfigSyncState` which are
  used for the configuration synchronization).

Diagnose
````````

The execution is logged in `$OMD_ROOT/var/log/web.log` on remote and central
sites.

Notification Spooler
--------------------

By default notifications are sent out locally from every site. This can be
customized with the commercial editions using the
:doc:`arch-comp-mknotifyd`.

See also
========

- :doc:`arch-comp-gui`
- :doc:`arch-comp-livestatus`
- :doc:`arch-comp-liveproxyd`
- :doc:`arch-comp-mknotifyd`
- `User manual: Distributed monitoring <https://docs.checkmk.com/latest/en/distributed_monitoring.html>`_
