================================
rrdcached - The RRD cache daemon
================================

Introduction and goals
======================

The rrdcached is a 3rd party component provided by the rrdtool project.

The time series data of our metric system is stored in RRD databases in the
file system of a OMD site. The rrdcached helps to optimize the IO with these RRD
databases.

Since we are producing continuous write operations this is an important feature
in larger setups because the disk IO is almost always a limiting factor in
scaling out.

The rrdcached receives updates to existing RRD files from the monitoring core,
accumulates them and, if enough have been received or a defined time has passed,
writes the updates to the RRD file. A flush command may be used to force writing
of values to disk, so that graphing facilities and similar can work with
up-to-date data.

See also
--------
- :doc:`arch-comp-core`
- `User manual: Graphing - The RRDS <https://docs.checkmk.com/master/en/graphing.html#rrds>`_
- `rrdcached man page <https://oss.oetiker.ch/rrdtool/doc/rrdcached.en.html>`_
