# Beta-Version of New "Windows Agent" of "Check MK Monitoring Software 1.6"


## About beta testing

*The New Windows Agent is designed to be safe, i.e. non-intrusive and non-destructive.
This is one of the our design targets. This fact gives us possibility to install and remove 
the New Agent relativeley safely even on a computer system used in production.*

Algorithm
* **Install** MSI
* checking/testing
* **Uninstall** Check MK Service
* **lwa_enable.cmd**

## Files description 

* check_mk_agent.msi - agent installer 
* clean_files.bat    - removes all files after uninstallation
* lwa_enable.cmd     - switches ON Legacy agent and OFF New one
* wnx_enable.cmd     - switches ON New agent and OFF Legacy one
* readme.md          - this readme
* openfirewall.cmd   - opens firewall for the agent
* closefirewall.cmd  - closes firewall back


## Testing requirements

* [mandatory] Windows 2008R2/Windows or newer
* [recommended] Check MK 1.5.0 with installed Windows Agent
* [mandatory] Administrative Rights for to run any Command


## Preinstall

* Run *openfirewall.cmd*


## Clean Install

Assuming you have no Legacy Windows agent:
* Run *check_mk_agent.msi* as ADMIN. **Do not change installation folder**
* Use your monitoring site to get information
* Use *check_mk.user.yml* to change behavior of the agent


## Upgrade mode

Assuming you have 1.5 Windows Agent installed:
* Run *check_mk_agent.msi* as ADMIN. **Do not change installation folder**
* Use your monitoring site to get information
* Important: New agent stops and  disables Legacy agent
* Safety: New Agent doesn't change Legacy agent files and settings
* Important: New agent also reuses check_mk.ini and plugins from Legacy agent


## Misc

* You may use *lwa_enable.cmd* and  *wnx_enable.cmd*  too switch between agents, both command are safe to use


## Reporting

* You can use supplied zipall.cmd or ziplog.cmd and send obtained file to sk@mathias-kettner.de or skipnis@gmail.com

## Uninstallation

* Using Control Panel (or msi-file)
* Optionally you can clean files from the disk with *clean_files.cmd*
* If you have Legacy Agent, please, call *lwa_enable.cmd* to reenable it
* Run *closefirewall.cmd*

## New Agent Files&Folders

* Core files of agent are located now in the "%ProgramFiles(x86)%\check_mk_service"
* User files are located in the "%ProgramData%\CheckMk\Agent"
* YML with user settings:  "%ProgramData%\CheckMk\Agent\check_mk.user.yml"
* The Log File is "%Public%\check_mk.log"


