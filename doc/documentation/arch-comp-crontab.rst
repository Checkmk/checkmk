=======
Crontab
=======

Introduction and goals
======================

Schedules site specific jobs in the context of the site user to run at periodic
intervals.

Architecture
============

The site individual crontab is one of the :doc:`integrations of OMD <arch-comp-omd>`
with the Operating System.

The crontab of the site is populated through the files located in
`$OMD_ROOT/etc/cron.d`.

The actual crontab is then installed to the system by the OMD init script
`$OMD_ROOT/etc/init.d/crontab`. Even if the management of the crontab is
realized as init script, there is no site specific continuously running cron
service. The sites crontab is installed as site user cron tab to
`/var/spool/cron/crontabs/$OMD_SITE`.

Since it is realized as init script, the crontab is installed during startup of
the site and removed when the site is stopped. This means there is no site cron
job executed when a site was stopped cleanly.

The crontab service is considered running as long a site user crontab is known
to the cron of the Operating System.

Risks and technical debts
=========================

Technical debts
---------------

In case a site is not stopped cleanly, e.g. because of a crash of the
Operating System, the crontab may still be installed and considered running even
before the site is being started. This is an inconsistency which we should solve
at some point.
