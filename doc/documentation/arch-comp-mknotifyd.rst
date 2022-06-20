================================
mknotifyd - Notification Spooler
================================

Introduction and goals
======================

The mknotifyd (Notification Spooler) is processing monitoring notifications
created by notification sources (the :doc:`arch-comp-core` and Event console
actions).

The main requirements we solve with the mknotifyd are:

* Deliver site local notifications asynchronously to prevent blocking the
  monitoring core during notification processing.
* Forward notifications from origin sites in distributed setups to realize
  central delivery of notifications from a destination site.
* Allow origin or destination sites to establish the network connection to
  support different network segmentation scenarios.

The notifications source produces so called raw notification contexts which are
not yet personalized notifications. Then the mknotifyd is performing it's
spooling, either locally or remotely. After spooling the final notifications are
sent to users.

If a site is forwarding notifications to another site, the raw notification
contexts are transported to the destination site between two mknotifyd
instances, the one of the origin site and the destination site.

The mknotifyd is an Enterprise feature.

Architecture
============

The mknotifyd is a daemon running in the context of an OMD site. The mknotifyd
is a single threaded application that connects with mknotifyd instances of other
sites through asynchronous socket IO.

Internal structure
------------------

You can get a good overview by looking at the `run_notifyd` function in
`enterprise/cmk/cee/mknotifyd` which contains the main loop. From there you
can dig into the individual functions.

Code
----

The entry point to the program can be found in the Checkmk git in
`enterprise/bin/mknotifyd` and the code of this component is located in
`enterprise/cmk/cee/mknotifyd`.

The mknotifyd has it's dedicated configuration which is located in
`$OMD_ROOT/etc/mknotify.d`.

Logs
----

The logs of the mknotifyd are written to `$OMD_ROOT/var/log/mknotifyd.log`.

Runtime view
============

Use cases
---------

In general the asynchronous processing of notification in Checkmk works like
this:

The notifications source produces so called raw notifications which are not yet
personalized notifications. After spooling, either locally or remotely, the raw
notifications will be matched against the configured notification rules on the
destination site which creates the final notification contexts (actually decides
who should be notified and using which notification plugins). The notifications
plugins will be invoked on the destination site. And after processing in the
destination site notification results are sent back to the origin site to add
their result to the monitoring history of the core.

Depending on the needs of a user the notification mechanic can be configured in
different ways. The most common use cases are:

Use case 0: Notification delivery without mknotifyd
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This actually does not involve the mknotifyd, but is shown for completeness.

.. uml:: arch-comp-mknotifyd-uc0-no-mknotifyd.puml

Use case 1: Asynchronous local delivery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. uml:: arch-comp-mknotifyd-uc1-mknotifyd-async-local.puml

Use case 2: Forward to destination site for central delivery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. uml:: arch-comp-mknotifyd-uc2-mknotifyd-remote.puml

Bulk notifications
------------------

Besides handling of single notifications the notification system also supports
`bulk notifications <https://docs.checkmk.com/latest/en/notifications.html#bulk>`_.
These are handled quiet differently during processing and also need to be
supported by the `notification plugins <https://docs.checkmk.com/latest/en/notifications.html#_bulk_notifications>`_.

TODO: Visualize processing of single vs. bulk notifications

Interfaces
==========

Encrypted connections between sites
-----------------------------------

.. uml::

  package "Site A" {
    component mknotifyd as mknotifyd_site_a
    component stunnel as stunnel_site_a
  }
  package "Site B" {
    component mknotifyd as mknotifyd_site_b
    component stunnel as stunnel_site_b
  }
  interface TLS as tls

  mknotifyd_site_a - stunnel_site_a
  stunnel_site_a - tls
  tls - stunnel_site_b
  stunnel_site_b - mknotifyd_site_b

The mknotifyd is establishing a connection with a local stunnel instance which
is responsible for the encryption of the transport with the destination site. On
the destination site a stunnel instance is caring for the transport encryption.

The mknotifyd specific stunnel configuration
(`$OMD_ROOT/etc/stunnel/conf.d/99-mknotifyd.conf`) is written and applied to
stunnel by mknotifyd during initialization based on the given mknotifyd
configuration.

Risks and technical debts
=========================

The line protocol of the mknotifyd is a home grown protocol which is based on
exchanging of python dictionaries. The actual format is currently not fully
understood, not well defined and parsed during process which can easily lead to
confusions and errors.

See also
========
- `User manual: Notifications in distributed systems <https://docs.checkmk.com/latest/en/distributed_monitoring.html#notifications>`_

