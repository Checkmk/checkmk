.. Plugin API documentation master file, created by
   sphinx-quickstart on Mon May 11 13:59:50 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Plugin APIs
###########

This is the plugin API reference from Checkmk.
This can help you to get exact information about the API.
If you want to know how to use the API, please have a look at the articles about extending Checkmk in the `Checkmk User Guide <https://docs.checkmk.com/2.5.0/en/devel_intro.html?origin=checkmk>`_.

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

.. toctree::
   :maxdepth: 1
   :glob:

   **/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
