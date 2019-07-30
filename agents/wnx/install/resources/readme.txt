# New Windows Agent: FAQ


##  Where is my log files? 
The Log file is moved to %ProgramData%\checkmk\agent\log, usually you will find log file here: c:\ProgramData\checkmk\agent\log\check_mk.log

##  Where is my ini file?
The New Windows Agent uses YAML files to configure own parameters.
*check_mk.user.yml* file in the %ProgramData%\checkmk\agent is current *user configuration file*.
*check_mk.bakery.yml* file in the %ProgramData%\checkmk\agent\bakery is current bakery configuration file. 
*It is not recommended to edit this file*. This file is controlled by WATO and your changes may be lost. 
*check_mk.yml* file in the %ProgramFiles(x86)%\checkmk\service is default configuration file. 
*It is not recommended to edit this file too*. This file is part of New Windows Agent distribution.

## Where is my folders?
In %ProgramData%\checkmk\agent, usually this is c:\ProgramData\checkmk\agent\

## What happened with Legacy Agent?
Installation of the New Windows Agent stops and disables the Legacy Agent(if it is presented). 
All files of the Legacy Agent are preserved intact on the disk.
To fully uninstall the Legacy Agent you have to use Windows Uninstall Procedure using either Windows Control Panel or command line.

## What happened with plugins and configurations files of the Legacy Agent?
After installation New Agent should migrate to Legacy Agent's configuration and plugins. 
1. Ini file converted to the corresponding yml files
2. Plugins, other configurations files, state files and so on are copied to the corresponding New Agent folders
3. *Upgrade procedure is performed only once*. If you want to repeat migration/upgrade you have two possibilities:
  1. Call from command line *check_mk_agent upgrade -force*
  2. Uninstall New Agent, delete %ProgramData%\checkmk\agent folder, install New Windows Agent 

Known Problems with Migration:
1. "logfiles" section is not supported anymore by New Agent.
2. Custom user plugins with hard coded paths may not work