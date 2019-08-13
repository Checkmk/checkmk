# New Windows Agent: FAQ

## New Directory structures
The fabric files are located in the directory %ProgramFiles(x86)%\checkmk\service\
Normally you should never switch to this folder or change files in this folder. 

The user and bakery files are located in the directory %ProgramData%\checkmk\agent\
This directory has structure similar to directory structure of the Legacy Agent.
For example
- the Log file is in %ProgramData%\checkmk\agent\log, usually you will find log file here: c:\ProgramData\checkmk\agent\log\check_mk.log
- state files are in %ProgramData%\checkmk\agent\state
- temporary directory is %ProgramData%\checkmk\agent\tmp
- config, mrpe, bin, spool, plugins, local and so on

New subdirectories are
- bakery, %ProgramData%\checkmk\agent\bakery, which contains bakery config
- install %ProgramData%\checkmk\agent\install, which contains files installed internally by Windows Agent
- upgrade %ProgramData%\checkmk\agent\upgrade, which is used to install MSI files automatically
- backup %ProgramData%\checkmk\agent\backup, in which the Agent saves last known good user YML.
Those subdirectories are intended for internal use by bakery, agent and updater.
Backup may be used to restore your yml config

##  Where is my ini file?
The New Windows Agent uses YAML files to configure own parameters.
*check_mk.user.yml* file in the %ProgramData%\checkmk\agent is current *user configuration file*.
*check_mk.bakery.yml* file in the %ProgramData%\checkmk\agent\bakery is current bakery configuration file. 
*It is not recommended to edit this file*. This file is controlled by WATO and your changes may be lost. 
*check_mk.yml* file in the %ProgramFiles(x86)%\checkmk\service is default configuration file. 
*It is not recommended to edit this file too*. This file is part of New Windows Agent distribution.

## Where is my folders?
In %ProgramData%\checkmk\agent, usually this is c:\ProgramData\checkmk\agent\


## Quick switch to factory settings
- Stop Agent
- rename ProgramData\checkmk\agent to agent.sav, for example
- Start agent

## Quick switch to bakery settings
- rename ProgramData\checkmk\agent\check_mk.user.yml to check_mk.user.yml.sav, for example
- check_mk_agent.exe reload_config


## Configuration reloading
To reload configuration after edit you may use nexte methods
- start and stop service
- command line option reload_config
The Agent supports also an automatic reload on every call from the Monitoring Site. 
To enable this feature you have to set CMA_AUTO_RELOAD=yes

## What happened with Legacy Agent?
Installation of the New Windows Agent stops and disables the Legacy Agent(if it is presented). 
All files of the Legacy Agent are preserved intact on the disk.
To fully uninstall the Legacy Agent you have to use one of those methods
- use Windows Uninstall Procedure using either Windows Control Panel or command line.
- use command line option of the new Agent remove_lgacy
- set in section global remove_legacy: yes
- use bakery

## Firewall
The current Agent version doesn't support Firewall Automation, do not forget to open for new Agent.
An old rule may be incompatible with new Agent.


## What happened with plugins and configurations files of the Legacy Agent?
After installation New Agent should migrate to Legacy Agent's configuration and plugins. 
You have to use packaged version of the Agent Installer to Upgrade Legacy configurations

Upgrade procedure consists of next steps:
1. The Ini files are converted to the corresponding yml files
2. The Plugins, other configurations files, state files and so on are copied to the corresponding New Agent folders
3. The relative paths to the plugins are corrected in the output yml files.

*Upgrade procedure is performed only once*. If you want to repeat migration/upgrade you have two possibilities:
  1. Call from command line *check_mk_agent upgrade -force*
  2. Uninstall New Agent, delete %ProgramData%\checkmk\agent folder, install New Windows Agent 

Known Problems with Migration:
1. The section 'logfiles' is not supported anymore by New Agent. Please, use corresponding check_mk plugin
2. Custom user plugins with hard coded paths may not work
3. The installation of the Baked Agent(Including Vanilla) prevents the Migration. 
You have to use Packaged agent if you want to upgrade your current configuration.


## Uninstallation
The uninstallation routine will preserve user data in next directories
%ProgramData%\checkmk\agent\state
%ProgramData%\checkmk\agent\config
%ProgramData%\checkmk\agent\plugins
%ProgramData%\checkmk\agent\local
%ProgramData%\checkmk\agent\mrpe
%ProgramData%\checkmk\agent\
This is done intentionally to prevent occasional user data loss due to uninstallation.


