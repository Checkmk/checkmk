.. Check API documentation master file, created by
   sphinx-quickstart on Mon May 11 13:59:50 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Plugin API
##########

This is the plugin API reference from Checkmk. This can help you to get exact
information about the API. If you want to know how to use the API, please have
a look at the articles about extending Checkmk in our `user guide <https://docs.checkmk.com/master>`_.

Plugin location and loading
===========================
Most of the plugin APIs (Agent based, Ruleset, Server-side calls and Graphing API) share
the same logic when it comes to location and loading of the plugins. This section will
cover those APIs.
The Bakery API has a different logic for now, but will be adapted in the future versions.

The shipped plugins  are located under the `cmk/plugins` folder, while local plugins have
to be placed under the `local/cmk_addons/plugins` folder in the site.

Below the top-level folder, plugins are organized in families, e.g. all plugins concerning
cisco devices will be found under the folder named `cisco`. Plugins belonging to the same family can
share code between both plugins of a same and plugins of a different type, e.g. server-side
call plugin can share common code with the agent based plugins if they belong to the same family.

Below the family folder, plugins are grouped by type:

   * server-side calls are located under the `server_side_calls` folder
   * rulesets under the `rulesets` folder
   * agent based plugins under the `agent_based` folder
   * graphing plugins under the `graphing` folder

In order for Checkmk to load your plugin, you have to follow the folder structure described above.
Checkmk will load the agent based plugin only if it's located under
`cmk/plugins/{family_name}/agent_based` or `local/cmk_addons/plugins/{family_name}/agent_based` folder.

Apart from the right location, it's also important to name the variable of a plugin object with
the right prefix.
An agent based plugin is created by instantiating the CheckPlugin object and naming the variable with
a `check_plugin_` prefix, e.g. `check_plugin_aws_status`.

Each plugin type expects a different prefix in the variable name:

   - SNMP sections expect the `snmp_section_` prefix
   - agent sections the `agent_section_` prefix
   - check plugins the `check_plugin_` prefix
   - inventory plugins the `inventory_plugin_` prefix
   - active checks the `active_check_` prefix
   - special agents the `special_agent_` prefix
   - rule specs the `rule_spec_` prefix
   - metrics the `metric_` prefix
   - translations the `translation_` prefix
   - perfometers the `perfometer_` prefix
   - graphs the `graph_` prefix

.. toctree::
   :caption: Base

   cmk.agent_based/index
   cmk.base.plugins.bakery.bakery_api/index
   cmk.server_side_calls/index
   cmk.graphing/index
   cmk.rulesets/index

.. toctree::
   :caption: Dynamic configuration

   cmk.cee.dcd.plugins.connectors.connectors_api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
