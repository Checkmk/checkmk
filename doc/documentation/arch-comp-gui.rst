===
GUI
===

Introduction and goals
======================

From the user perspective the GUI is separated in two component:

* *Monitoring* (aka status GUI): It is providing views, dashboards, availability
  insights, reporting and similar capabilities. All these features are using
  Livestatus to gather the information to be displayed from the Monitoring
  cores. The *Monitoring* is responsible for providing access to the current
  status data and to provide capabilities for operating actions (like setting a
  downtime).

  The monitoring is also providing access to historic status information in the
  form of events and metrics.

* *Configuration* (aka Setup, WATO): It is the GUI component to manage the
  configuration of all Checkmk components. The Setup is responsible for
  providing privileged Checkmk users capabilities to update and activate the
  configuration of Checkmk.

Architecture
============

Components and interfaces
-------------------------

The GUI is mostly backend rendered and powered by a home grown framework. We
consider features like HTTP request and response handling, authentication,
authorization, logging, HTML rendering and various other capabilities to be part
of the *Framework* component.

The functionality the GUI is providing is built in so called "main modules". For
example the modules `cmk.gui.views` and `cmk.gui.dashboard` are main modules of
the *Monitoring*.

.. note::
   The following diagram shows some of the most important modules. It is
   currently not exhaustive, because there is a lot of restructuring ongoing. In
   the end this diagram should give a complete overview.

.. uml:: arch-comp-gui-components.puml

.. _wsgi-routing:

WSGI routing
------------

.. uml:: arch-comp-gui-wsgi-routing.puml

The GUI is realized as WSGI applications in `index.wsgi`. Besides multiple
specialized WSGI helper applications, the two major applications are:

* The `CheckmkApp`: It serves all endpoints of the GUI together with some
  GUI application specific AJAX endpoints.

* The `CheckmkRESTAPI`: It serves all REST API endpoints, the API spec together
  with the swagger UI.

There are several WSGI applications involved in processing of these main
applications for serving different needs (profiling, debugging, environment
cleanups and so on). For details have a look at the code.

Plugins
-------

The GUI has a plugin mechanic which is used to address the two requirements:

* Allow external developers to extend the functionality of the GUI.
* Allow non Checkmk Raw Editions to extend the functionality of the GUI.

Each of the GUI's "main modules" can be extended with plugins. For example a
main module `cmk.gui.views` can be extended with plugins from the
`cmk.gui.plugins.views` module hierarchy.

The user extensions, so called local plugins, are located in the local hierarchy
of the users site below `local/lib/python3/cmk/gui/plugins/[main_module]`.

The import of plugins is executed like this:

.. uml:: arch-comp-gui-plugin-imports.puml

Configuration
-------------

The main configuration file of the GUI is `$OMD_ROOT/etc/check_mk/multisite.mk`.
Initially this was the only configuration file of the GUI. However, these days
the configuration of the GUI is located in `$OMD_ROOT/etc/check_mk/multisite.d`.
All `.mk` files are read as configuration files recursively. Below this
directory there are files controlled by the *Configuration* or by the user.

This is the standard configuration layout of the Checkmk components that are
configurable through the *Configuration*. Other components, like the
:doc:`arch-comp-checkengine`, Event Console, :doc:`arch-comp-liveproxyd`,
`Notification spooler` and so on are also using this scheme.

The configuration is loaded during processing of each HTTP request by the
`cmk.gui.config` module. The components of the GUI are only allowed to use the
configuration loaded by this mechanic instead of using some other `load`
function.

The only exception is the *Configuration* component (`watolib`). This component
is allowed to read and write specific configuration files that are defined to be
under the control of WATO.

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
* After the module import cleanup in 2.1, it is now again possible to move all
  shared code between builtin modules from `cmk.gui.plugins.[main_module].utils`
  to the `cmk.gui.[main_module]` name-space. This would make the hierarchy much
  clearer. We should consider structuring it the exact same way as `cmk.base`
  for the `agent_based` API.
* Too many parts of the GUI are realized in plugins. The program structure would
  be easier to understand if more parts would be built as normal modules.
  Nothing internal should rely on code implemented in a plugin. There should be
  not a single import of things from `cmk.gui.plugins.*` things
* The API which is available to plugins is not defined. In the past we added
  things as needed to support the development of plugins we shipped. We should
  tighten this and reduce it to the functionality that is most used externally.
* The home grown components of our framework make it hard to onboard new
  developers. We should consider replacing some of the home grown things with
  external components.
