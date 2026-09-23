==================
Experimental flags
==================

An experimental flag is a site-wide, file-backed boolean that lets developers merge
unfinished work into the development and stable branches without exposing it to
users. Unlike a config option, it does not live forever, every flag carries a
removal deadline, and a test fails the build once that deadline passes.

Design
======

All flags live as fields on a single Pydantic model, ``ExperimentalFlagConfig``
(``packages/cmk-flags/cmk/flags/_config.py``), persisted as JSON in
``$OMD_ROOT/etc/check_mk/release_flag.json``. ``experimental_field()`` declares a
field: it fixes the type to ``bool``, defaults it to ``False``, and attaches:

* ``description`` -- what the flag gates.
* ``remove_ticket`` -- the ticket tracking its removal.
* ``remove_after`` -- the Checkmk version by which the flag must be gone.
* ``owner`` -- the person responsible for removing it.

.. uml::

    [GUI: Global Settings] as gui
    [ConfigDomainExperimentalFlags] as domain
    () "_pending_release_flag.json" as pending
    () "release_flag.json" as file
    [any reader] as reader

    gui ..> domain: writes via
    domain ..> pending: save()
    domain ..> file: activate()
    reader ..> file: load_experimental_flags()

``ConfigDomainExperimentalFlags`` (``cmk/gui/experimental_flags/global_config.py``) is
the only writer of both files. Every other consumer only reads ``release_flag.json``,
through ``cmk.flags.load_experimental_flags``.

Visibility
----------

Flags are a developer tool, not a user-facing setting. The "Experimental flags"
group in Global Settings appears only on sites installed with ``cmk-dev-install``
(see the ``cmk-dev-site`` repository). On every other site the group is not
registered, so users cannot change a flag from the GUI. Achieved with
the environment variable CMK_DEV=TRUE, which defaults to false.

Changing a flag
---------------

Setting a flag is a two-stage write that follows the usual activate-changes flow:

1. Saving the setting in Global Settings writes the new state to
   ``$OMD_ROOT/etc/check_mk/pre_flag.json``. Nothing reads this file except
   ``ConfigDomainExperimentalFlags``, so the running site is unaffected.
2. Activating changes copies that state to ``release_flag.json`` and then restarts
   the whole site.

Flags are read in many processes, and many of them, like the GUI registration
below, read a flag only once at startup. On activate changes the whole site
is restarted for experimental flags.

Usage
=====

Declaring a flag
-----------------

Add a field to ``ExperimentalFlagConfig`` in ``packages/cmk-flags/cmk/flags/_config.py``::

    new_monitoring_views: Annotated[bool, experimental_field(
        description="Enable the experimental new monitoring views.",
        remove_ticket="CMK-12345",
        remove_after="2.6.0",
        owner="some.owner@checkmk.com",
    )] = False

That field alone makes the flag appear as an "Experimental flags (for testing only)"
setting in Global Settings on sites installed with ``cmk-dev-install`` (see
`Visibility`_).

Reading a flag
---------------

::

    from cmk.flags import load_experimental_flags
    import cmk.utils.paths

    if load_experimental_flags(cmk.utils.paths.default_config_dir).new_monitoring_views:
        ...

A missing config file yields an all-off config, so it is safe to call before a site
has ever touched the setting. Call it fresh wherever the current state matters:
``ExperimentalFlagConfig`` is frozen per instance, but the backing file can change
between two calls.

Proven strategies for gating code
-----------------------------------

Gate registration in the GUI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the GUI, check the flag where the feature registers its pages, config variables
and other plugins, and skip the registration when the flag is off. Import the
feature module inside the gated branch, so that none of its code is loaded while the
flag is off::

    def register(page_registry: PageRegistry) -> None:
        ...
        if load_experimental_flags(cmk.utils.paths.default_config_dir).new_monitoring_views:
            from cmk.gui import new_monitoring_views

            new_monitoring_views.register(page_registry)

Registration runs only once, when a GUI process starts. This is safe because a
changed flag always restarts the whole site (see `Changing a flag`_).
