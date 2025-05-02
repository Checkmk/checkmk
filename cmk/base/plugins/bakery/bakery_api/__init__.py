#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The Bakery API is available for writing custom bakery plugins, that can be then
used to include functionalities to the agent packages at the Agent Bakery.

In most cases, these are plugins in the form of additional scripts to be executed by the checkmk
agent (agent plugin), and their configuration files. However, functionalities can also be
implemented that relate to the structure of the package itself, as long as this can be mapped
by including files, executing package scriplets (RPM/DEB/Solaris PKG) or specifying Windows
agent-specific configuration entries (yaml).

The Bakery API is intended to allow all artifacts to be described using a uniform syntax.
It is designed based on the Agent based API.

Not covered by the Bakery API are

* Definition of the config belonging to the plugin
* Writing agent plugins or other additional files that are required for the plugin

Quick Guide
===========

We are working on a more thorough documentation for the bakery API, that will soon be
available at our `official guide <https://checkmk.com/cms.html>`_. Until then, you
can refer to this Quick Guide for a brief introduction.

Bakery plugins are created in the form of a file that is imported as a Python module.
Below is a description of how a Bakery plug-in is structured.

Registration
------------
The registration is a function that is called when importing the Bakery Plugin as a module.

The individual components of the Bakery Plugin are passed to the function as arguments.
These are the :data:`name` and appropriate :data:`functions`, that themselves yield
artifacts each of one category.

The following arguments are available:

* :data:`name`
* :data:`files_function`
* :data:`scriptlets_function`
* :data:`windows_config_function`

Name
----
The name of a Bakery plug-in corresponds in meaning to the name of the plug-in that is to be
distributed in the Agent Bakery. It must be identical to the name of the corresponding
agent ruleset to provide the appropriate config.

Artifacts
---------
The actual components of a plug-in are described using appropriate classes. These can be
divided into the following categories:

* Files: Each file to be deployed with the checkmk agent is described with an object.
  The file type (e.g. plug-in file, system binary, plug-in configuration file) is described
  by the class. A separate object must be defined for each operating system on which the
  file is to be deployed. Files are described completely by their properties and contents
  (as init arguments). For example, there is no need to specify a full source or destination
  path, as this is an implementation detail. The current agent configuration is available
  for the specification of each file.
* Scriptlets: Represent a scriptlet to be executed by a package manager (RPM/DEB) at a given
  transaction step. They are described per packaging system (RPM/DEB) and per step
  (e.g. preinstall, postremove). In addition to the agent configuration, the current agent
  hash is also available for the specification
* Windows configurations: Configuration entries (yaml-Config) for the Windows agent are also
  described using suitable classes.

Functions
---------
As described above, the artifacts are each described inside of functions that correspond to
their category. These are generator functions that yield the individual specified artifacts.
The order is not important. The individual functions are passed to the registration function
with the arguments :data:`files_function`, :data:`scriptlets_function`, and
:data:`windows_config_function`

Input Parameters
----------------
The functions described above receive one or two parameters as arguments, which can be evaluated
to construct and determine the returned artifacts/objects. If the respective parameter is required,
it is specified accordingly in the argument list. The following names are available:

* :data:`conf`: contains the specific config for this plugin. Available for all three functions.
* :data:`aghash`: Contains the hash from the current agent configuration and plug-in files. Since
  this is only formed from the files to be packaged, it is only available
  for :data:`scriptlets_function` and :data:`windows_config_function`

Example bakery plugin
---------------------

Let's consider the following scenario

* An agent plug-in **my_example_plugin** is to be deployed with the agent.
* It is available in 3 versions for Linux, Solaris and Windows, and is to be packaged in the agent
  packages for these three operating systems as well. (The content of the agent plugins are not
  subject to the Bakery API - we assume ready-made files in the following). The files are available
  as ``my_example_plugin.linux.py``, ``my_example_plugin.solaris.sh`` and
  ``my_example_plugin.vbs``. (Python, shell and VB script are only examples of possible files.
  An agent plug-in can be any file executable on the target system).
* It should be configurable that the output of the plug-in is cached. That is, it will not be
  executed again by the agent until the configured time has elapsed.
* The plug-in can be configured with the variables *user* and *content*. The two Unix plugins
  read this configuration via a configuration file my_example_plugin.conf, the Windows plugin
  reads the entries *my_example_plugin.user* and *my_example_plugin.content* of the Windows
  Agent Config-yaml. (The access to these resources are to be implemented in the agent plugin
  itself and are not subject of the Bakery API).
* For Linux and Solaris there is also a program that we want to deliver - E.g., a small
  shell-script, with which we can also start our plug-in via command independently from the Checkmk
  agent: ``my_example``
* On Linux and Solaris we want to write in the syslog after installing the agent that we have
  installed my_example as well as write in the syslog after uninstalling the agent that my_example
  has been uninstalled. (This is not modern and may not make sense, but provides a simple example).

**Files**

The following files have to be deployed to the Checkmk site in order to realize the above scenario:

* ``~/local/share/check_mk/agents/plugins/my_example_plugin.linux.py``: Linux agent plugin
* ``~/local/share/check_mk/agents/plugins/my_example_plugin.solaris.sh``: Solaris agent plugin
* ``~/local/share/check_mk/agents/windows/plugins/my_example_plugin.vbs``: Windows agent plugin
* ``~/local/share/check_mk/agents/my_example``: Linux program/shell script
* ``~/local/share/check_mk/web/plugins/wato/my_example.py``: agent ruleset
* ``~/local/lib/python3/cmk/base/cee/plugins/bakery/my_example_plugin.py``: bakery plugin

**The bakery plugin**

The following code is a possible implementation of the bakery plugin, using the bakery API::

   #!/usr/bin/env python3

   import json
   from collections.abc import Iterble
   from pathlib import Path
   from typing import TypedDict

   from .bakery_api.v1 import (
      OS,
      Plugin,
      PluginConfig,
      Scriptlet,
      WindowsConfigEntry,
      DebStep,
      RpmStep,
      SolStep,
      SystemBinary,
      register,
      quote_shell_string,
      FileGenerator,
      ScriptletGenerator,
      WindowsConfigGenerator,
   )


   class MyExampleConfig(TypedDict, total=False):
      interval: int
      user: str
      content: str


   def get_my_example_plugin_files(conf: MyExampleConfig) -> FileGenerator:
      interval = conf.get('interval')

      yield Plugin(
         base_os=OS.LINUX,
         source=Path('my_example_plugin.linux.py'),
         target=Path('my_example_plugin'),
         interval=interval,
      )
      yield Plugin(
         base_os=OS.SOLARIS,
         source=Path('my_example_plugin.solaris.sh'),
         target=Path('my_example_plugin'),
         interval=interval,
      )
      yield Plugin(
         base_os=OS.WINDOWS,
         source=Path('my_example_plugin.vbs'),  # target=source
         interval=interval,
      )

      yield PluginConfig(base_os=OS.LINUX,
                        lines=_get_linux_cfg_lines(conf['user'], conf['content']),
                        target=Path('my_example_plugin.cfg'),
                        include_header=True)
      yield PluginConfig(base_os=OS.SOLARIS,
                        lines=_get_solaris_cfg_lines(conf['user'], conf['content']),
                        target=Path('my_example_plugin.cfg'),
                        include_header=True)

      for base_os in [OS.LINUX, OS.SOLARIS]:
         yield SystemBinary(
               base_os=base_os,
               source=Path('my_example'),
         )


   def _get_linux_cfg_lines(user: str, content: str) -> list[str]:
      # Let's assume that our Linux example plug-in uses json as a config format
      config = json.dumps({'user': user, 'content': content})
      return config.split('\\n')


   def _get_solaris_cfg_lines(user: str, content: str) -> list[str]:
      # To be loaded with 'source' in Solaris shell script
      return [
         f'USER={quote_shell_string(user)}',
         f'CONTENT={quote_shell_string(user)}',
      ]


   def get_my_example_scriptlets(conf: MyExampleConfig) -> ScriptletGenerator:
      installed_lines = ['logger -p Checkmk_Agent "Installed my_example"']
      uninstalled_lines = ['logger -p Checkmk_Agent "Uninstalled my_example"']

      yield Scriptlet(step=DebStep.POSTINST, lines=installed_lines)
      yield Scriptlet(step=DebStep.POSTRM, lines=uninstalled_lines)
      yield Scriptlet(step=RpmStep.POST, lines=installed_lines)
      yield Scriptlet(step=RpmStep.POSTUN, lines=uninstalled_lines)
      yield Scriptlet(step=SolStep.POSTINSTALL, lines=installed_lines)
      yield Scriptlet(step=SolStep.POSTREMOVE, lines=uninstalled_lines)


   def get_my_example_windows_config(conf: MyExampleConfig) -> WindowsConfigGenerator:
      yield WindowsConfigEntry(path=["my_example_plugin", "user"], content=conf["user"])
      yield WindowsConfigEntry(path=["my_example_plugin", "content"], content=conf["content"])


   register.bakery_plugin(
      name="my_example_plugin",
      files_function=get_my_example_plugin_files,
      scriptlets_function=get_my_example_scriptlets,
      windows_config_function=get_my_example_windows_config,
   )
"""
