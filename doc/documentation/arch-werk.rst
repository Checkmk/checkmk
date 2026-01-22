====================
Werk
====================

A "Werk" (German for work) is a changelog element. Normally it is added with the
commit that implements the feature or fix. It holds a title, a description and
some metadata.

Currently the metadata also contains the Checkmk version when the change
connected to the Werk will be released. This is why a special tool is needed to
pick changes from one branch to another, so the version can be adapted.

Versions
========

There are two different versions of Werk files (not to be confused with the
version field inside the Werk that specifies in which Checkmk version the Werk
was introduced!)

* markdown (2.3 and higher)
    * also called "v2" or "md"
    * Werk files end with ".md"
* nowiki (2.2 and below)
    * also called "classic", "legacy" or "v1"
    * Werk files have no file extension

Systems getting in touch with Werks
===================================

Release Process
---------------

Announcing
~~~~~~~~~~

A Mail and a Forum post is generated from the Werk files added in this version.

See ``announce`` sub-command of ``python -m cmk.utils.werks``

Rewrite Versions of Werks
~~~~~~~~~~~~~~~~~~~~~~~~~

During the release process, a new release candidate may need to be created.
In this case, dedicated commits will be picked onto the corresponding release
branch ``release/A.B.CpX``. Potentially picked werks therefore may need a fix-up
of their version field. In case the ``werk`` script is used, the version field
will be automatically rewritten. However in the upstream branch ``A.B.C`` the
version of the corresponding werk would also need to be updated.
This is a current design flaw and should be fixed in the future.

Precompiled Werks
~~~~~~~~~~~~~~~~~

Precompiled Werks is the "database" (a json dump) that is shipped with Checkmk
which contains Werks relevant for this release.

Version 2.2 and below shipped Werks from all versions, suggesting that the
database shipped with Checkmk contains all Werks from all versions. But this is
not true. It only contains:

* all versions of the current major version
* all Werks that were added on the master branch (normally Werks assigned to the
  first beta release of a major version)
* some random Werks, which were probably added by accident

Version 2.3 and higher ship only Werks from the current major version.

Precompiled Werks consist of multiple files: one for each edition. It is created
while building Checkmk. A make-target is executing ``python -m cmk.werks.utils precompile``


Website
-------

You can search and filter Werks on the official Checkmk website: https://Checkmk.com/werks

To compile a list of all Werks, you have to look for Werks in all branches of
Checkmk. This is done via ``python -m cmk.werks.utils collect``. There is a
jenkins job that executes this command in a 10 minutes interval. The command
creates a json dump, which will then be copied to the server hosting the
homepage and read by a cron job.

Beside the Checkmk git repository, also the repository for the Checkmk appliance and
the kubernetes repository contain Werks (robotmk will join this club eventually).
As all of them have different configuration and version numbers you have to
specify the flavor for collecting Werks from there. In the jenkins job those
json dumps are joined to one big json dump.

One Werk can be specified in multiple branches potential with different content.
Higher versions and finally the master branch will always overwrite others.


Mailing-lists
-------------

In Werks you can specify the impact of a change via the "level" metadata. There
are three levels (1=trivial change, 3=big impact), for each of those levels a
mailing-list exists. An additional security mailing-list is also available (each
Werk is either a fix, a feature or security related).

The mails are sent via ``python -m cmk.utils.werks mail``. The command is
executed daily on jenkins for each currently supported branch. It sends mails
directly to the mailing-list addresses.

Each and every edit on a Werk will result in at least one mail to the
mailing lists. So if you need to modify many (>10) Werks, you should think about
disabling sending mails. The normal workflow for that is:

* ask IT-Admins to add you to the moderators of the Werk mailing lists
* ask IT-Admins to enable emergency moderation of all Werk mailing lists
* (optional) wait one day to see if this works correctly
* merge your mass editing Werks change
* wait one day until the cron job runs
* reject unwanted mails on the mailing list
* ask IT-Admins to disable emergency moderation

If a mail was sent for a particular commit is saved in git notes.

Checkmk
-------

Checkmk also includes a Werk browser which reads the precompiled Werks created
during the build process.

Werks can be marked as incompatible. This means that the user has to do
something in their Checkmk installation if they use the feature that was
modified with this Werk. In order to keep track of the to-dos, incompatible Werks
need to be acknowledged.

When updating to the next major version the user is warned when there are still
unacknowledged Werks from the previous version: Those can not be displayed in
the updated Checkmk, as it only ships with Werks from the current major version.

This is also why Checkmk 2.3.0 still needs code to read v1 Werks from the
precompiled Werks file: The code warning about the unacknowledged Werks is
execute from 2.3.0, but reads the Werks and unacknowledged Werks from a 2.2.0
site.


Werk-tool
---------

The source of all Werks are files. You can create, grep and edit them via normal
tools, but there is also a specialized helper called ``werk``. It lives in
``/packages/cmk-werks/``. It is used to pick Werks between version branches, and
can pick from branches using v1 Werks and automatically transform them to v2
Werks if the destination branch has markdown Werks enabled.

There are also some convenience functions to grep, list or edit Werks from the
command-line.


Technical background
====================

Reading Werks from disk is a two step process: first the file is parsed (meta
data is translated to a key-value structure, description is handled as a blob)
and then it is loaded (meta-data is validated and markdown/nowiki is transformed
to html).
This has the benefit that parsing a Werk is quite fast, but loading it can be
slow. For listing or grepping Werks it does not have to be validated and also
the description has not be interpreted, so parsing is enough in those instances.


There is no loading function for Werk v1 files: Those files are parsed, then
transformed to v2 files and then again parsed and loaded as Werk v2 files. This
way there is no difference if the file is automatically translated to markdown
and written to disk as markdown file, or loaded from v1 files and automatically
translated. They are exactly the same.

But this is only true when talking about Werks in 2.3 or higher. Werks in 2.2
and below have two different render targets with slightly different behavior:
The description may contain markdown formatting which is interpreted when
displayed on the website, but not interpreted when displayed in the built in
Werks viewer of Checkmk 2.2. and below.
