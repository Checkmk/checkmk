===
GUI
===

Introduction and goals
======================

From the user perspective the GUI is separated in two component:

* *Monitoring* (aka status GUI): It is providing views, dashboards, availability
  and reporting and similar capabilities. All these pages are using Livestatus to gather the
  information to be displayed from the Monitoring cores. The *Monitoring* is
  responsible for providing access to the current status data and to provide
  capabilities for operating actions (like setting a downtime).

  The monitoring is also prodiving access to historic status information in the
  form of events and metrics.

* *Configuration* (aka Setup, WATO): It is the GUI component to manage the
  configuration of all Checkmk components. The Setup is responsible for
  providing privileged Checkmk users capabilities to update and activate the
  configuration of Checkmk.

Architecture
============

Components and interfaces
-------------------------

The GUI is powered by a home grown framework for receiving HTTP requests, HTML
rendering and building HTTP responses.

The functionality the GUI is providing is built in so called "main modules". For
example the modules `cmk.gui.views` and `cmk.gui.dashboard` are main modules of
the *Monitoring*.

.. uml:: arch-comp-gui-components.puml

.. _wsgi-routing:

WSGI routing
------------

.. uml:: arch-comp-gui-wsgi-routing.puml

The GUI is realized as WSGI applications. Even if there are more specialized
WSGI applications, we can split the GUI into the two major ones:

* The `CheckmkApp`: It serves all endpoints of the GUI together with some
  GUI application specific AJAX endpoints.

* The `CheckmkRESTAPI`: It serves all REST API endpoints, the API spec together
  with the swagger UI.

There are several WSGI applications involved in processing of these main
applications for serving different needs (profiling, debugging, environment
cleanups and so on). For details have a look at the code.

Plugins
-------

TODO: Describe the plugin mechanic

Configuration
-------------

The configuration of the GUI is located in `$OMD_ROOT/etc/check_mk/multisite.d`.
Below this directory there are files controlled by the *Configuration* or by the
user. The configuration is loaded during processing of each HTTP request by the
`cmk.gui.config` module. The components of the GUI are only allowed to use the
configuration loaded by this mechanic.

The only exception is the the *Configuration* component (`wato`, `watolib`).
This component is allowed to read and write specific configuration files that
are defined to be under the control of WATO.

Logging, Profiling, Debugging
-----------------------------

The application log of the GUI is `$OMD_ROOT/var/log/web.log`. The log level can
be controlled by the global setting *User interface > Logging*.

The GUI configured to
`profile specific HTTP requests <https://kb.checkmk.com/display/KB/Checkmk+profiling#Checkmkprofiling-GUIProfiling>`_.

See also
--------
- :doc:`arch-comp-apache`
- `User manual: User interface <https://docs.checkmk.com/latest/en/user_interface.html>`_

Risks and technical debts
=========================

Technical debts
---------------

* The conceptual ideas described above are not clearly reflected in the module
  hierarchy of the application. This makes it hard to understand for developers.
  The module hierarchy should be cleaned up to be more in line.
* The home grown components of our framework make it hard to onboard new
  developers. We should consider replacing some of the home grown things with
  external components.
