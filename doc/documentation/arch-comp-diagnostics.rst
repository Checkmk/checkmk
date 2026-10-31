===================
Support diagnostics
===================

Introduction and goals
======================

Support diagnostics collect the information support needs to analyze a
problem of a site into one archive, the dump. The requirements are:

* Collect site and server data without support needing access to the site.
* Let the user choose what to include, by topic and by sensitivity.
* Never include data more sensitive than the user chose.
* Let every feature contribute its own data without changes to the core.

Creating a dump
===============

A user creates a dump in the GUI (Setup > Maintenance > Support diagnostics) or
with ``cmk --create-diagnostics-dump``.

The data is grouped into topics, such as configuration files, log files or the
monitoring core. For each topic, the user chooses a sensitivity threshold:

* ``LOW``: no sensitive data.
* ``MEDIUM``: may include IP addresses, host names, user names and mail
  addresses.
* ``HIGH``: may include passwords.

The GUI preselects ``MEDIUM``. A dump then contains everything of a topic up
to the threshold, plus some basic data that is part of every dump, such as the
Checkmk version, the installed packages and the hardware.

What a dump never contains
--------------------------
* Known password patterns in collected configuration and log files are replaced
  with ``REDACTED``, at every threshold.
* The secret files of the site are never collected, for example
  ``etc/htpasswd``, ``etc/*.secret`` and ``var/check_mk/stored_passwords``.
  Only their paths and sizes appear in the file list.
* Configuration files nobody classified appear only at ``HIGH``.

Some topics contain data of the whole server, not only of the site. For
example, the process list shows every process.

Extending the diagnostics
=========================

Files below etc/check_mk and var/log
------------------------------------
Configuration files (``*.mk``, ``*.conf``, ``*.bi``, ``.wato``) a feature writes
below ``etc/check_mk`` and log files (``*.log``, ``*.state`` and their
rotations) below ``var/log`` are collected without further work. Other files
there need a plug-in, see `Other data`_. Two tables in
``cmk/plugins/diagnostics/lib/_classification.py`` decide their sensitivity,
with paths relative to the folder:

* A *name entry* (``CheckmkFileInfoByNameMap``) classifies every file with that
  name, wherever it is, for example all ``hosts.mk`` files of all folders.
* A *path entry* (``CheckmkFileInfoByRelFilePathMap``) classifies one file, for
  example ``conf.d/wato/global.mk``. It takes precedence over a name entry.

A file without either entry counts as ``HIGH``. So:

* The settings of a new Setup config domain need no entry, as long as the
  domain keeps the default files ``global.mk`` and ``sitespecific.mk``, which
  have name entries. A domain overriding ``config_file()`` needs its own entry.
* A file with a new name needs a name entry to appear below ``HIGH``. Add a
  path entry instead only when files of the same name differ in sensitivity.

Keep secrets in the password store and only references in the configuration.
Redaction only matches known patterns, so a secret in a new format reaches the
dump.

Other data
----------
Data anywhere else, or data that has to be generated, needs a plug-in in the
plug-in family of the feature: a ``DiagnosticsPlugin`` from
``cmk.diagnostics.internal``, named ``diagnostics_plugin_*``, in
``cmk/plugins/<family>/diagnostics/``. Examples are the state of a daemon, the
output of a command, or files below ``var`` other than logs.

A plug-in declares a topic, a description shown in the GUI and one sensitivity.
It must only yield data of that sensitivity, because the threshold selects
whole plug-ins. A source with data of different sensitivities needs one
plug-in per sensitivity. Text that may contain passwords goes through
``redact_passwords_in_content``.

Architecture
============

The diagnostics consist of these parts:

* The plug-in API ``cmk.diagnostics.internal``, which defines plug-ins,
  sensitivities, topics and the redaction helpers.
* The plug-ins in ``cmk/plugins/<family>/diagnostics/``.
* The engine ``cmk.diagnostics.engine``, which discovers the plug-ins and
  resolves the user's selection.
* The dump creation in ``cmk/base/diagnostics.py``, which runs the selected
  plug-ins and packs their files into the archive.

The GUI calls the automation ``create-diagnostics-dump-v2``, so the GUI and the
CLI run the same code.

A plug-in's handler yields ``DumpItem`` objects: generated content or a
verbatim copy of an existing file, each with its path in the archive. The
engine only packs what the handlers yield; reading, filtering and redaction are
up to the plug-in. A plug-in marked ``always`` runs in every dump.

The configuration and log files are collected by the plug-ins in
``cmk/plugins/diagnostics/diagnostics/files.py``, one per folder and
sensitivity, for example ``config_files_medium``. Each one walks its folder,
classifies every file with ``get_checkmk_file_info`` and yields only the files
of its own sensitivity, redacted. ``multisite.d/sites.mk`` is sanitized
instead.
