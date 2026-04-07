======
Bakery
======

.. automodule:: cmk.base.plugins.bakery.bakery_api
   :members:
   :show-inheritance:

Version 2 (UNSTABLE): `cmk.bakery.v2_unstable`
==============================================

.. automodule:: cmk.bakery.v2_unstable
   :members:


Version 1: `cmk.base.plugins.bakery.bakery_api.v1`
==================================================

bakery_api.v1
*************

.. automodule:: cmk.base.plugins.bakery.bakery_api.v1
   :members:
   :show-inheritance:


bakery_api.v1.register
**********************

.. py:function:: bakery_plugin(*, name: str, files_function: FilesFunction | None = None, scriptlets_function: ScriptletsFunction | None = None, windows_config_function: WindowsConfigFunction | None = None) -> None

   Register a Bakery Plugin (Bakelet) to Checkmk

   This registration function accepts a plug-in name (mandatory) and up to three
   generator functions that may yield different types of artifacts.
   The generator functions will be called with keyword-arguments 'conf' and/or 'aghash'
   while processing the bakery plug-in (Callbacks), thus the specific call depends on the
   argument names of the provided functions.
   For keyword-arg 'conf', the corresponding WATO configuration will be provided.
   For keyword-arg 'aghash', the configuration hash of the resulting agent package
   will be provided.
   Unused arguments can be omitted in the function's signatures.

   :param name: The name of the agent plug-in to be processed. It must be unique, and match
       the name of the corresponding WATO rule. It may only contain ascii
       letters (A-Z, a-z), digits (0-9), and underscores (_).
   :param files_function: Generator function that yields file artifacts.
       Allowed function argument is 'conf'.
       Yielded artifacts must must be of types 'Plugin', 'PluginConfig',
       'SystemConfig', or 'SystemBinary'.
   :param scriptlets_function: Generator function that yields scriptlet artifacts.
       Allowed function arguments are 'conf' and 'aghash'.
       Yielded artifacts must be of type 'Scriptlet'.
   :param windows_config_function: generator function that yields windows config artifacts.
       Allowed function arguments are 'conf' and 'aghash'.
       Yielded artifacts must be of types 'WindowsConfigEntry', 'WindowsGlobalConigEntry',
       'WindowsSystemConfigEntry', 'WindowsConfigItems', or 'WindowsPluginConfig'.


