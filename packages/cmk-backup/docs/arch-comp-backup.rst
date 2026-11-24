======
Backup
======

Introduction and goals
======================

The main requirements we need solve are:

* Create a backup archive of a stopped Checkmk site
* Create a backup archive of a running Checkmk site
* Restore a backup from an archive with the same site name
* Restore a backup from an archive with a different site name
* Create a backup of the Checkmk Appliance
* Restore a backup of the Checkmk Appliance

Architecture
============

These requirements are addressed by these components:

* `mkbackup`: Manage Checkmk site and Checkmk Appliance system backups
* `omd backup/restore`: Execute the actual site backup

`omd` is responsible for managing the Checkmk sites. Accordingly, it also
provides the simple basic site backup mechanism for executing site backups
without the need to configure anything.

Backup jobs, backup targets, encryption and so on are higher level features of
mkbackup.

There is another important reason for the split: When we think of the Appliance
system backup, we have one component that is responsible for each thing to be
backed up (mkbackup for the system, the omd command of each site). We can easily
deal with sites having different omd versions, since every site cares for it's
own backup.

.. uml:: arch-comp-backup.puml

mkbackup
========

The mkbackup command is implemented in `bin/mkbackup` and has been built to
deal with two types of backups:

Site backup
-----------

It is executed in the site context as site user with the responsibility of
creating an backup of the site (optionally compressed, encrypted).

To execute the actual site backup, mkbackup makes use of the `omd backup` and
`omd restore` commands (see below).

System backup of the Checkmk Appliance
--------------------------------------

It is executed in the system context as root user with the responsibility of
creating an backup of the users files stored on the Checkmk appliance which
includes the system configuration and (optionally) the sites.

Encryption
----------

The backups of mkbackup can optionally be encrypted. This encryption is
realized using asymmetric encryption.

In case the encryption is enabled, the RSA public key is used to encrypt the
backup without the need for entering a passphrase. To be able to restore the
backup, the passphrase needs to be provided by the user to decrypt the private
key.

The site backup key pairs are stored in `[omd_root]/etc/check_mk/backup_keys.mk`
and the *system backup* key pairs are stored in `/etc/cma/backup_keys.conf`.

Configuration
-------------

The backups are executed as `job` which store their backups on `targets`.

The jobs can be configured to optionally compress and encrypt the backup with
backup keys managed by the user. The jobs can either be created according to a
given schedule or manually.

The targets always point to local file system paths. However, the path can
point to a mounted network file system. On the appliance there is a mount
management, which enables the user to configure network file systems for the
backup.

The user manages the configuration of *system backup* through the Appliance UI
on the Checkmk appliance. It is stored at `/etc/cma/backup.conf`.

The *site backup* configuration is managed through the Setup module "Backup"
It is stored in `[omd_root]/etc/check_mk/backup.mk`.

The Setup integration is implemented in:

* `cmk.gui.backup.backup`: Shared code with the Appliance UI
* `cmk.gui.wato.pages.backup`: Configuration views

The backup targets configured in the *system backup* can be used by the *site
backup*.

Scheduling
----------

The execution of the time triggered jobs is done by cron. The configuration is
written with the Job configuration. The path to the cron configuration
`/etc/cron.d/mkbackup` for the *System backup* and
`[omd_root]/etc/cron.d/mkbackup` for the site backup.

Logging
-------

Logs are written to the system log `/var/log/syslog` in case a *system backup*
is executed.

omd backup and restore
======================

OMD is the tool for managing Checkmk sites. Besides others it has the following
responsibilities:

* Create a backup archive of a stopped Checkmk site
* Create a backup archive of a running Checkmk site
* Restore a backup from an archive with the same site name
* Restore a backup from an archive with a different site name

All actions need to work with a local file on disk or with an input or output
stream.

The command is configured through the command line.

See also
--------
- :doc:`arch-comp-omd`

Technical debts
---------------

* Initially mkbackup was implemented in the Checkmk git and upstreamed to the
  CMA git to keep both repositories in Sync. Since the Appliance is still using
  Python 2.7 the implementations have diverged. This needs to be cleaned up.
  There is an ongoing approach to do the 2 to 3 transition for the appliance,
  but it will take some time to be merged.

* The site backup output does not seem to be logged which makes it hard to
  analyze issues.

* Delimitation: The cmk command has `--backup` and `--restore` sub commands which
  can be executed within the context of a site to create a backup archive of
  the Checkmk configuration (not the whole site configuration). It is implemented
  in `cmk.base.backup`.
  These commands are from the early days of Checkmk and does not create complete
  configuration backups. A large number of necessary files for having a
  complete configuration dump is missing. So it might be better to drop this.
