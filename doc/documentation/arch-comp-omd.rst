===
OMD
===

Introduction and goals
======================

The main requirements we solve with OMD are:

* Make start using Checkmk as easy as possible (it's just three commands!)
* Make maintenance of Checkmk installations as easy as possible

Other features we get from OMD:

* The ability to run multiple instances (or *sites*) in parallel
* The ability to operate instances with differing Checkmk versions
* Single command upgrade from one version to another
* Complete isolation of sites from each other
* A standardized environment (paths, dependencies) across Linux distributions
* A clear separation of data and software
* An initial configuration of all components

Architecture
============

OMD has two main components:

* Creating *Checkmk software packages* (deb, RPM or CMA (Checkmk appliance archive))
* The *omd command* for managing the sites

Site integration with the OS
----------------------------

OMD hooks into different parts of the Operating system.

* Each site has it's own operating system user (The *site user*)
* Each site is located in it's dedicated *site directory*
* Each site creates a ramdisk for temporary file processing
* Each site hooks into the system wide apache configuration for HTTP access
* Each site has a dedicated crontab

The integration with the OS configuration should be as lean as possible so that
they are easy to manage and do not need to be updated often.

OMD command architecture
------------------------

The capabilities of the omd command depend on the execution context. This can
either be the system wide ``root`` context or the ``site`` context.

The root context is mainly intended to be used for managing sites from the
outside (e.g. creating, deleting sites). But for convenience it is also possible
to perform site internal actions (like starting all processes of a site).

All site internal actions are done with site user permissions.

The code can be found at ``omd/packages/omd/omd.bin`` and
``omd/packages/omd/omdlib``.

Packaging architecture
----------------------

The packaging part of OMD is mostly realized in Makefiles.

The entry point is in ``omd/Makefile``. Have a look at ``omd/README.md`` for
more detailed information.

OMD is packaging multiple independent software projects, our own and 3rd party,
to a single Checkmk software package.

Each software package is integrated into OMD as so called *OMD package*. These
are located at ``omd/packages/[omd_package_name]``. Each software package has
one dedicated Makefile which cares about building that software and packaging
the files of that software.

*TODO: Add graphic for omd/Makefile structure*

Runtime view
============

Systemd is executing ``omd.service`` which executes the omd command.

It's the responsibility of the omd command to manage (start, stop, ...) the main
server processes of all sites which are configured to be automatically started.

Multiple main server processes have child processes that they are responsible
for to manage. For example the monitoring core has its own child processes.

Some main server processes are always started and some are started depending
on the configuration.

.. uml::

   [OMD]
   node "Site processes" as omd_p {
      [mknotifyd]
      [mkeventd]
      [rrdcached]
      [liveproxyd]
      component "[[../arch-comp-liveproxyd.html liveproxyd]]" as liveproxyd
      [crontab]
      component "[[../arch-comp-dcd.html dcd]]" as dcd
      [apache]
      [agent-receiver]
      [redis]
      [stunnel]
      [systemd]
      [cmc]
   }
   node "Microcore helper processes" as cmc_p {
      [checkhelper] as checker
      [icmpsender]
      [icmpreceiver]
      [fetcher]
      [cmk --notify]
      [cmk --handle-alerts]
      [cmk --create-rrd]
      [cmk --checker]
      [cmk --real-time-checks]
   }
   node "liveproxyd processes" as liveproxyd_p {
      [Site process]
   }
   node "Apache processes" as apache_p {
      [Worker process]
   }
   OMD -> omd_p
   cmc -> cmc_p
   liveproxyd -> liveproxyd_p
   apache -> apache_p
