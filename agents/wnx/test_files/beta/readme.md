# Short Description of files

## Files

* check_mk_agent.msi - installer 
* clean_files.bat    - remove all files after uninstallation
* lwa_enable.cmd     - switch ON Legacy agent
* wnx_enable.cmd     - switch ON New agent
* readme.md          - this readme

## Testing requirements

* Check MK 1.5.0
* Administrative Rights for EVERY Run Command

## Files&Folders

* Core files(not user) are in the "%ProgramFiles(x86)%\check_mk_service"
* User files are in the "%ProgramData%\CheckMk\Agent"
* YML to edit is "%ProgramData%\CheckMk\Agent\check_mk.user.yml"
* Log File is "%Public%\check_mk.log"

## Preinstall

* Run *openfirewall.cmd*

## Clean Install

* Run *check_mk_agent.msi* as ADMIN. **Do not change installation folder**
* Use your monitoring site to get information
* Use *check_mk.user.yml* to change behavior of the agent

## Upgrade mode

* You have to have 1.5 Agent installed
* Run *check_mk_agent.msi* as ADMIN. **Do not change installation folder**
* Use your monitoring site to get information
* New agent stops and  disables Legacy agent
* New agent also reuses check_mk.ini and plugins from Legacy agent

## Misc

* You may use *lwa_enable.cmd* and  *wnx_enable.cmd*  too switch between agents

## Uninstallation

* Using Control Panel or supplied msi
* Optionally you can clean files from the disk with *clean_files.cmd*
* If you have Legacy Agent, please, call *lwa_enable.cmd* to reenable it
* Run *closefirewall.cmd*



