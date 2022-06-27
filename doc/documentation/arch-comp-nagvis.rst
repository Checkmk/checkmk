======
NagVis
======

Introduction and goals
======================

NagVis is a 3rd party component. It is a visualization add-on for monitoring
information gathered by Nagios or Checkmk. It allows users to create custom
graphical views, for example network topology views based on parent and child
relationships, geographical maps or custom maps.

Interfaces
----------

NagVis information sources are named backend. Each of these backends is
interfacing with one source to get monitoring state information. For Checkmk we
have the following backends:

* The main backend is `mklivestatus` which uses the
  :doc:`arch-comp-livestatus` interface to get monitoring
  information from the :doc:`arch-comp-core`.

* The `mkbi` backend is used to interface with the Web API of the user interface
  to get status information of Checkmk BI aggregates.

Risks and technical debts
=========================

Today NagVis is the only component of Checkmk which is based on PHP. It uses the
PHP installation provided by the Linux distribution.

See also
--------
- :doc:`arch-comp-livestatus`
- :doc:`arch-comp-core`
- `User manual: NagVis <https://docs.checkmk.com/latest/en/nagvis.html>`_
- `NagVis website <https://nagvis.org/>`_
