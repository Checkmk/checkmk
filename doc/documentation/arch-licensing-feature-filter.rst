===========================================
License-based import filter (sitecustomize)
===========================================

TL;DR
=====

Checkmk is heading towards a single enterprise build whose features are switched on and off by the applied license.
To prepare for that, modules belonging to a disabled feature are simply not importable in the site.
Which files belong to which feature is declared once per wheel on bazel side.
Which features are enabled comes from the license options, which today are still derived purely from the edition.

Introduction and goals
======================

Today, "what a site can do" is decided at build time:
Checkmk is packaged once per edition, and a Pro package simply does not contain Ultimate code.

The goal is to get away from that.
Eventually we want to ship **a single enterprise build** and let the applied license alone decide which features a site is entitled to:
the same installed package would behave as Ultimate, Pro or Community, and features such as the bakery, telemetry, the OTel collector, the relay, the extended cloud plugin families or agent registration could be switched on and off individually.
We are not there yet.
Editions are still separate packages, and the license-derived *feature options* are currently derived from the edition alone.
The import filter is a preparatory step: it puts the enforcement mechanism in place now, so that code is already gated per feature by the time the license becomes the source of truth.

The filter works at the lowest possible layer, the Python import system.
Code that belongs exclusively to a disabled feature is **not importable** in that site, so it cannot register GUI pages, plugins, check functions, REST endpoints or cron jobs.
Ideally, this is the *only* gate a feature needs: when a feature's code is discovered rather than imported explicitly, a missing module is simply not there, and no runtime check is required anywhere.
Runtime checks remain for code shared between features (see `Interfaces`_), but a feature that needs them for its own code is a sign that it is not yet fully discoverable.

Requirements overview
---------------------

* One build, several entitlements: an Ultimate package must be able to run as Pro (and a Pro package as Community) without re-packaging, once the license is consulted.
* Fail closed by default: a feature that is disabled must not reach any registry (plugin discovery, GUI registration, entry points) just because the files are on disk.
* No per-feature boilerplate: package owners declare *which feature their package belongs to* once, in the wheel, not in every module.
* Do not break Python's own machinery (``importlib.metadata``, namespace packages, ``pip``-installed third party code in ``local/``).

Architecture
============

White-box overall system
------------------------

.. uml::

    package "Build time (Bazel)" {
        [py_wheel\n(non-free/packages/<pkg>/BUILD)] as wheel
        note right of wheel
          entry_points = {
            "cmk.features.<option>": [...]
          }
        end note
        [package_wheel] as pkgwheel
        [site-packages/<pkg>.dist-info\n(METADATA, RECORD, entry_points.txt)] as distinfo
        wheel --> pkgwheel
        pkgwheel --> distinfo
    }

    package "Site start-up (every python process)" {
        [sitecustomize.py] as sc
        [apply_feature_filter()] as apply
        [get_license_options()] as opts
        [files_for_disabled_features()] as files
        [_FeatureFilterFinder\n(one per sys.meta_path entry)] as finder
        sc --> apply
        apply --> opts : edition(omd_root)\n(+ license, later)
        apply --> files : disabled option names
        files --> distinfo : importlib.metadata.distributions()
        apply --> finder : sys.meta_path[:] = [...]
    }

    [import cmk.bakery] as imp
    [check_catalog / cmk --man] as catalog
    [blocked_feature_files()] as blocked
    imp ..> finder : find_spec()
    catalog ..> blocked : same file set,\nby path
    blocked --> files : wraps

The mechanism has three parts:

1. **Tagging (build time).**
   A wheel that implements a license-gated feature carries an entry-point *group* ``cmk.features.<option>``, where ``<option>`` is a field of ``LicenseOptions`` (``packages/cmk-licensing/cmk/licensing/basics/options.py``).
   The entry point's name and value are irrelevant; only the group is read.
   Example from ``non-free/packages/cmk-bakery/BUILD``::

       py_wheel(
           name = "wheel",
           distribution = "cmk-bakery",
           entry_points = {
               "cmk.features.bakery": ["cmk-bakery = cmk.bakery"],
           },
           ...
       )

   ``package_wheel`` (``bazel/rules/package_wheel.bzl``) unpacks the wheel into the site's ``site-packages``, so the ``*.dist-info`` directory (with ``RECORD`` and ``entry_points.txt``) is available at runtime.
   The filter only looks at distributions whose name starts with ``cmk-``.

   This is the *fine-grained* layer.
   The *coarse* layer is still build time: ``edition_deps`` in ``omd/BUILD`` selects per ``--cmk_edition`` which non-free ``pkg_tar`` targets are shipped at all (Community gets none).
   The import filter covers the remaining case: the wheel **is** installed, but the license does not enable its feature.

2. **Deciding (site start-up).**
   ``get_license_options(...)``  returns a ``LicenseOptions`` with one ``LicenseFlag`` per option.
   Today the result is derived from the edition alone.
   The license verification response is wired in but deliberately not yet consulted.
   Once this concept goes live a real license will downgrade an Ultimate install to Pro behavior.
   ``LicenseOptions.disabled()`` yields the names of all disabled options.

3. **Blocking (import time).**
   We collect all files (from ``dist.files``, i.e. the wheel ``RECORD``) of every ``cmk-*`` distribution whose feature tags are **all** in the disabled set.
   We then replaces each finder in ``sys.meta_path`` with a custom finder that delegates ``find_spec`` to the original and returns ``None`` (i.e. "not found")  whenever the resulting spec's ``origin`` is one of the blocked files.
   The importing code sees a plain ``ModuleNotFoundError``.

Where it is installed
---------------------

``omd/packages/Python/sitecustomize.py`` is installed into ``lib/python3.X/`` of the OMD Python (see ``omd/packages/Python/BUILD.Python.bazel``) and is therefore executed by **every** interpreter start in a site: the GUI's WSGI workers, ``cmk``, cron jobs, the agent receiver, ``omd`` in site context, ad-hoc ``python3`` in a site shell.
The filter is only installed when ``OMD_ROOT`` is set; as root (``omd`` outside a site) nothing is filtered.

Because ``sitecustomize.py`` runs before anything else, its imports must stay minimal: ``cmk.licensing.basics`` is the only allowed dependency.
Anything imported here is imported by every Python process in the site, and cannot itself be license-gated.

Do not confuse this file with the ``sitecustomize.py`` that the root ``BUILD`` generates for the *development venv*: that one only prepends the repository's ``packages/*`` to ``sys.path`` and installs no filter.
In a Git checkout nothing is blocked.

Interfaces
----------

* ``cmk.licensing.basics.finder.apply_feature_filter(omd_root, meta_path)`` -- used once, by ``sitecustomize.py``.
* ``cmk.licensing.basics.finder.blocked_feature_files(omd_root)`` -- the same file set, realpath-normalized, for code that walks the file system instead of importing: the man-page catalog in ``cmk --man`` / ``cmk -M`` (``cmk/base/modes/check_mk.py``) and the Setup check catalog (``cmk/gui/wato/pages/check_catalog.py``) pass it as ``blocked_paths`` to ``cmk.utils.man_pages``. Any new file-system based discovery of license-gated content must do the same, otherwise the GUI advertises checks the site cannot run.
* ``cmk.licensing.registry.is_option_enabled(omd_root, option)`` and ``get_license_options(...)`` -- the *runtime* counterpart for code that is shared between features and must branch on a flag (REST API schema restrictions, GUI fields, ``cmk.gui.main_modules.register``, the agent receiver's relay switch).
  Use these when a module is imported in all editions but only part of its behavior is licensed.

Rule of thumb: **whole packages** are gated by tagging the wheel; **code paths inside shared packages** are gated with ``is_option_enabled``.

Runtime view
============

Adding a license-gated package
------------------------------

1. Add the option to ``OptionName`` and ``LicenseOptions`` in ``options.py`` (including ``get_flag`` and each edition's defaults), or reuse an existing one.
2. Tag the wheel: add ``"cmk.features.<option>": ["<dist> = <top pkg>"]`` to the ``entry_points`` of the package's ``py_wheel``.
3. If several wheels are delivered under one option, tag them all with that option (see ``_FEATURE_BY_FAMILY`` in ``non-free/packages/cmk-plugins-nonfree/BUILD``: both Azure extended families carry ``cmk.features.azure_extended``).
   An untagged wheel is never blocked and silently leaks into lower editions.
4. Make sure the code that *uses* the package tolerates its absence: either it lives behind ``is_option_enabled``, or it is discovered dynamically (plugin families, GUI registration) and copes with a missing module.

Semantics worth knowing
-----------------------

* **All tags must be disabled for a file to be blocked.**
  A wheel tagged with ``bakery`` and ``reporting`` stays importable as long as either feature is enabled.
  Tag a wheel with several features only if its code is genuinely needed by each of them; otherwise split the wheel.
* **Namespace packages are never blocked.**
  A spec without ``origin`` (``cmk``, ``cmk.plugins``, ``cmk.gui.nonfree`` ...) is passed through, because several wheels contribute to it and it carries no functionality.
  Blocking happens at the first real file.
* **Blocking means "not found", not an exception.**
  Raising inside ``find_spec`` would abort plugin discovery for everybody; returning ``None`` lets ``importlib`` continue with the next finder and finally raise a normal ``ModuleNotFoundError`` in the importer.
* **``find_distributions`` is forwarded.**
  The wrapper copies the wrapped finder's ``find_distributions`` so that ``importlib.metadata`` (``version()``, ``entry_points()``) keeps working.
* **Only finders present at start-up are wrapped.**
  A finder appended to ``sys.meta_path`` later (e.g. by a third-party import hook) is not filtered.
* **Only ``cmk-*`` distributions are considered.**
  Third-party wheels and everything under ``$OMD_ROOT/local/lib/python3`` are never blocked, even though the path finder that serves them is wrapped.
* **Not a security boundary.**
  ``python3 -S``, a manually constructed ``PathFinder``, or reading the files from disk bypass the filter.
  It exists to make the *default* behavior of a site correct and consistent, not to protect the code.
* **Edition detection falls back to Community.**
  ``cmk.ccc.version.edition`` returns ``COMMUNITY`` when no ``omd version`` can be read (Git checkout, doctests, spec generation).
  In such contexts everything would be blocked; ``sitecustomize`` is not active there, but code calling ``blocked_feature_files`` directly should keep that in mind.

Debugging
---------

A ``ModuleNotFoundError`` for a module whose file exists on disk is the signature of this filter.
To check what is blocked:

.. code-block:: python

    # run as the site user, e.g. via ``python3 -`` in a site shell
    import os
    from pathlib import Path

    from cmk.licensing.basics.finder import blocked_feature_files

    for path in sorted(blocked_feature_files(Path(os.environ["OMD_ROOT"]))):
        print(path)

``python3 -S`` starts an interpreter without ``sitecustomize`` (and hence without the filter or the ``local/lib/python3`` path) for comparison.

Deployment view
===============

Nothing edition-specific is deployed for the filter itself: ``sitecustomize.py`` and ``cmk-licensing`` are part of every edition.
The edition-specific input is (a) which tagged wheels the package contains and (b) the site's edition and, in the future, license.

Risks and technical debts
=========================

* ``get_license_options`` ignores the license verification response; the "Ultimate installed, Pro licensed" case is not yet live.
  The dependency is kept on purpose so the refactoring path stays open (see  ``options.py``).
* Tagging is by convention.
  Nothing verifies that a wheel under ``non-free/`` carries a ``cmk.features.*`` tag, or that the tag names an  existing ``OptionName``.
  Today the two sides already disagree:
  There are options without any tagged wheel (they are runtime-only flags), while some wheels carry tags that match no option and can therefore never be blocked (because they are part of all commercial editions).
* Tests in ``packages/cmk-licensing/tests/test_finder.py`` cover the file selection but not ``_FeatureFilterFinder`` against real ``sys.meta_path`` finders; system tests exercise it only implicitly.
* ``cmk.flags`` (``packages/cmk-flags``) looks similar but is unrelated: it holds *experimental developer toggles*, not license entitlement.
* See also :doc:`arch-migrations` ("Packaging: non-free code out of the free module hierarchy") for the move of non-free code under ``non-free/`` that makes per-wheel tagging possible in the first place.
