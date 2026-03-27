.. Plugin API documentation master file, created by
   sphinx-quickstart on Mon May 11 13:59:50 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Plugin APIs
###########

This is the plugin API reference from Checkmk.
This can help you to get exact information about the API.
If you want to know how to use the API, please have a look at the articles about extending Checkmk in the `Checkmk User Guide <https://docs.checkmk.com/master/en/devel_intro.html?origin=checkmk>`_.

.. _plugin-location-and-loading:

Plugin location and loading
===========================
Most of the plugin APIs (Agent based, Ruleset, Server-side calls, Graphing and Bakery API) share the same logic when it comes to location and loading of the plugins.
This section will cover those APIs.

The shipped plugins are located under the ``~/lib/python3/cmk/plugins`` folder, while local third party plugins are placed under the ``~/local/lib/python3/cmk_addons/plugins`` folder in the site.
As a general rule, code `should` reside below ``cmk`` if and only if it is supplied by Checkmk (but that's not always the case yet).

If you want to override the behavior of existing plugins, you can put code under ``~/local/lib/python3/cmk/plugins``.
Please be aware that you are doing such changes at your own risk and that Checkmk does not offer support for such modifications.

Below the top-level folder, plugins are organized in families, e.g. all plugins concerning cisco devices will be found under the folder named ``cisco``.
Plugins belonging to the same family can share code, regardless of the plugin group.
For example a `server-side call` plugin can share code with the `agent based` plugins if they belong to the same family.

Below the family folder, plugins are categorized into plugin groups:

   * server-side calls are located under the ``server_side_calls`` folder
   * rulesets under the ``rulesets`` folder
   * agent based plugins under the ``agent_based`` folder
   * graphing plugins under the ``graphing`` folder
   * bakery plugins under the ``bakery`` folder
   * man pages are found in ``checkman``
   * executables (to be run by the code, for instance) go into ``libexec``
   * inventory UI plugins are located under the ``inventory_ui`` folder

In order for Checkmk to load your plugin, you have to follow the folder structure described above.
Checkmk will load an agent based plugin only if it's located under ``~/local/lib/python3/cmk/plugins/{family_name}/agent_based`` or ``~/local/lib/python3/cmk_addons/plugins/{family_name}/agent_based`` folder.

Apart from the right location, it's also important to name the variable of a plugin object with the right prefix.
An agent based plugin is created by instantiating the CheckPlugin object and naming the variable with a ``check_plugin_`` prefix, for example ``check_plugin_aws_status``.

Each plugin expects a different prefix in the variable name:

   - SNMP sections expect the ``snmp_section_`` prefix
   - agent sections the ``agent_section_`` prefix
   - check plugins the ``check_plugin_`` prefix
   - inventory plugins the ``inventory_plugin_`` prefix
   - active checks the ``active_check_`` prefix
   - special agents the ``special_agent_`` prefix
   - rule specs the ``rule_spec_`` prefix
   - bakery plugins the ``bakery_plugin_`` prefix
   - metrics the ``metric_`` prefix
   - translations the ``translation_`` prefix
   - perfometers the ``perfometer_`` prefix
   - graphs the ``graph_`` prefix
   - nodes (inventory UI) the ``node_`` prefix

Type annotations
================

Type annotations are present throughout the plugin APIs.

Using type checking tools (such as mypy) is encouraged when developing plugins.
This helps catch potential issues early and ensures your code adheres to the expected interfaces.

**Important:** The behavior for code that violates the type annotations is unspecified and may change without warning.
While the type annotations document the expected types, runtime behavior when passing incorrect types is not guaranteed to be stable across versions.

"Internal" and "unstable" APIs
==============================

Along with the regular versioned plugin APIs you might find "internal" and "unstable" APIs.
These APIs adhere to the same architectural principles.
**However: They do not provide a stable interface!**
They might change without prior notice.

"Unstable" APIs are still in an experimental state, but they are built with the intention of becoming the next version of a regular API in the future.
Third party developers are encouraged to try them out and provide feedback.

The "internal" APIs are used by plugins maintained by Checkmk, but they are not intended for use by third party developers.
Their contents may or may not become part of a future regular API.

Overriding plugin families and the role of ``__init__.py``
==========================================================

Shipped plugins can be overriden by placing your own plugins in the local folder.
The recommended way to do this by installing an MKP.
This section explains how the shadowing mechanism works and how it is affected by the presence or absence of ``__init__.py`` files in plugin family folders.

Understanding Python namespace packages
---------------------------------------

Checkmk's plugin system leverages Python's standard import mechanics to determine which plugins are loaded and how they can be overridden.
A crucial aspect of this mechanism is the presence or absence of ``__init__.py`` files in plugin family folders.
Understanding this concept is essential for developers who want to customize or extend Checkmk's functionality.

When you add your own plugins into the local folder (``~/local/lib/python3/cmk/plugins``), they are placed earlier on ``PYTHONPATH`` than the shipped Python libraries.
This allows you to shadow (override) shipped plugins with your own implementations.

The shadowing mechanism
-----------------------

Python's import system works similarly to how a shell finds commands: it searches through a list of directories (``sys.path``) in order and uses the first match it finds.
However, there's an important complication: **if a folder contains an ``__init__.py`` file, that folder becomes the smallest unit that can be shadowed**.

The key principle: **The first folder where an ``__init__.py`` file is found wins, and takes precedence over all other folders with the same name.**

Coherent plugin families (with ``__init__.py``)
-----------------------------------------------

Some plugin families in Checkmk are organized as coherent units and contain an ``__init__.py`` file.
For example, ``cmk/plugins/fritzbox`` has an ``__init__.py`` file, which makes the entire family "atomic" in terms of shadowing.

**Consequences for shadowing:**

- If you want to shadow such a family, you **must** include an ``__init__.py`` file in your local version
- Once you do this, **all** shipped files from that family folder will be shadowed
- If you don't include an ``__init__.py`` file, your custom plugin files will be completely ignored
- This ensures consistency: you can shadow the family, but then you must take responsibility for the entire family

**Example:**

.. code-block:: text

   # Shipped plugins:
   ~/lib/python3/cmk/plugins/fritzbox/__init__.py
   ~/lib/python3/cmk/plugins/fritzbox/agent_based/device.py

   # Your local override (correct):
   ~/local/lib/python3/cmk/plugins/fritzbox/__init__.py
   ~/local/lib/python3/cmk/plugins/fritzbox/agent_based/custom.py
   # Result: Only your local plugins are loaded

   # Your local override (incorrect):
   ~/local/lib/python3/cmk/plugins/fritzbox/agent_based/custom.py
   # Result: Your plugin is ignored because __init__.py is missing!

This approach makes sense for coherent plugin families where the plugins work together as a unit.

Namespace packages (without ``__init__.py``)
--------------------------------------------

Other plugin families, particularly the ``collection`` family (which contains plugins that haven't been categorized into specific families yet), are organized as namespace packages without ``__init__.py`` files.

**Consequences for shadowing:**

- Individual plugin files can be shadowed independently
- You don't need to take responsibility for the entire family
- Each plugin file is treated as a separate unit
- No ``__init__.py`` file is needed in your local version

**Example:**

.. code-block:: text

   # Shipped plugins:
   ~/lib/python3/cmk/plugins/collection/agent_based/plugin_a.py
   ~/lib/python3/cmk/plugins/collection/agent_based/plugin_b.py
   
   # Your local override:
   ~/local/lib/python3/cmk/plugins/collection/agent_based/plugin_a.py
   # Result: Your plugin_a.py shadows the shipped one, 
   #         but plugin_b.py still loads from the shipped location

This approach is ideal for collections where plugins are independent and can be customized individually.

Further reading
---------------

For more details about Python's namespace package concept, see `PEP 420 – Implicit Namespace Packages <https://peps.python.org/pep-0420/>`_.

Table of contents
=================

.. toctree::
   :maxdepth: 1
   :glob:

   **/index

Indices
=======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
