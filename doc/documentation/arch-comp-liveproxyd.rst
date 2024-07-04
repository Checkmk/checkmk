========================================
Liveproxyd - The livestatus proxy daemon
========================================

Introduction and goals
======================

The main requirement we solve with the Livestatus proxy daemon is:

* Optimize Livestatus connections from the central site to the remote site in
  :doc:`arch-comp-distributed` (Enterprise Edition).

Other features we get:

* Caching of Livestatus queries
* Transport of HW/SW Inventory information from remote to central site
* Shared livestatus connections between apache worker processes

The Livestatus proxy daemon is an Enterprise feature.

Architecture
============

Liveproxyd is a daemon running in the context of an OMD site.

Internal structure
------------------

Liveproxyd starts one child process per remote site to manage the site connections. The entry point
of the program is `enterprise/bin/liveproxyd`, which in turn calls `enterprise/cmk/cee/liveproxy/main.py`.

.. uml:: arch-comp-liveproxyd-structure.puml

Code
----

This component is implemented in `enterprise/cmk/cee/liveproxy`. There are two main loops regulating
the flow of our program. The outer one is located in `Manager.py`. This loop administrates the
individual sub-processes. Each sub-process manages the connections to one remote site. This is
administrated within an inner main loop in `Site.py`.

.. uml:: arch-comp-liveproxyd-classes.puml

Logs
----

Logs are written to `$OMD_ROOT/var/log/liveproxyd.log`. Additionally, `$OMD_ROOT/var/log/liveproxyd.state`
contains a snapshot of the current state of the program, which is updated in short intervals.

Runtime view
============

Requests typically originate from within the GUI in order to render a page which requires data from
remote sites. The diagram below shows the basic workflow for such requests. Note that there are a
number of variants not shown here, such as cached requests, timeouts and requests by special clients
(e.g. the heartbeat client).

.. uml:: arch-comp-liveproxyd-request-flow.puml

Managing the GUIs livestatus connections
========================================

The Liveproxyd has been built to optimize the Livestatus connections of the GUI.
Let's have a deeper look at the problems we solve.

The GUI needs a lot of connections
----------------------------------

Our web interface backend is driven by a preforking apache web server. In
preforking mode, there is a pool of apache processes where each process can
handle one HTTP request at a time.

Most of the HTTP requests to the Monitoring part of the GUI need information
from remote sites which are fetched using Livestatus. This means each of the
apache processes needs one Livestatus (TCP) connection to each remote site.

And in case of broken sites, this would even be worse, since the connections
would have to wait for the connect timeout to recognize a remote site is not
reachable.

Without the Liveproxyd each of the apache processes would have to make one
Livestatus connection to each remote site to get information from that site.

With e.g. 50 remote sites and 50 parallel HTTP requests, this would be 50 apache
processes requiring 50 connections each, resulting in 2500 connections in total.

Connection initialization vs. keepalive
---------------------------------------

All the apache processes would at least need the connections in the moment they
are handling a HTTP request. Here we face another problem: Initiating all
connection during request processing and disconnecting them at the end of a
request would take way too much time. We'd spend a lot of time with TCP connects
and also TLS handshakes.

This is why there is some keepalive mode implemented in the Livestatus client of
the GUI implemented, which holds connections open between HTTP requests. This
feature can optionally be enabled to solve the overhead caused by the connection
initialization.

You may already think about the fundamental drawback of this approach: All of
the connections mentioned above are held open until the apache process is
terminated and continuously blocks Livestatus threads on the remote sites. Even
if there is no query issued by that process.

In this mode, you need to carefully balance your central site apache pool size
and the remote site Livestatus thread pool size. Otherwise a saturated apache
pool may block your whole Livestatus capabilities, resulting in hanging HTTP
requests and would also block other Livestatus clients.

This is where the Liveproxyd comes in handy. It acts as a central connection
manager which initiates a pool of connections, monitors them and offers it to
the pool of apache processes.

In the moment a HTTP request is handled by an apache process, the Liveproxyd
immediately hands over the query of the apache process to an already established
connection. And in case a site is not reachable, this is already known by the
Liveproxyd, which can then respond to the query with an error message instantly.

See also
~~~~~~~~
- :doc:`arch-comp-core`
- :doc:`arch-comp-livestatus`
- :doc:`arch-comp-livestatus-client`
- :doc:`arch-comp-distributed`
- `User manual: Liveproxyd <https://docs.checkmk.com/latest/de/distributed_monitoring.html#livestatusproxy>`_
- `User manual: Retrieving status data via Livestatus <https://docs.checkmk.com/latest/en/livestatus.html>`_
