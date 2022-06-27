===========
RRD backend
===========

Introduction and goals
======================

The RRD backends is responsible for storing and serving the metrics Checkmk
collects during monitoring in the context of the local site.

Checkmk stores all metric data in round-robin database files (RRDs).

The RRDs offer important advantages for the storage of performance data in
comparison to classic SQL data bases:

* RRDs store data in a compact and IO efficient way
* The space used per metric on the drive is static. RRDs can neither grow nor
  shrink. The required disk space can be planned well.
* The CPU and disk time per update is always the same. RRDs are (virtually)
  real-time capable, so that reorganizations can't cause data jams.

Architecture
============

Components and interfaces
-------------------------

.. uml:: arch-comp-rrd-backend-components-enterprise.puml

You can do all RRD IO directly via `librrd`. However, to optimize disk IO when
reading and writing metrics, we need to communicate with the
:doc:`arch-comp-rrdcached`. But the rrdcached path can not be used to create
RRDs for new metrics.

So we need two paths:

* Reading/Writing metrics to RRDs via rrdcached
* Create RRD databases via RRD create helper

Differences between Raw and Enterprise editions
-----------------------------------------------

The RRD backend architecture differs between Nagios core and Microcore. In the
Raw Edition, when the Nagios core is used, the NPCD an `process_perfdata.pl`,
components of PNP4Nagios, are used to write the metrics to the RRD storage.

.. uml:: arch-comp-rrd-backend-components-raw.puml

See also
~~~~~~~~
- `Man page: rrdtool <https://oss.oetiker.ch/rrdtool/doc/rrdtool.en.html>`_
- `User manual: Checkmk and RRDs <https://docs.checkmk.com/master/en/graphing.html#rrds>`_
- `User manual: Data organization in RRDs <https://docs.checkmk.com/master/en/graphing.html#data_rrds>`_
- :doc:`arch-comp-core`
- :doc:`arch-comp-livestatus`

Risks and technical debts
=========================

Technical debts
---------------

The Raw Edition with the Nagios core follows a different approach for creating
RRD databases of new hosts and services. This functionality currently needs to
be kept in sync.
