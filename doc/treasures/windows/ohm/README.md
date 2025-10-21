# OpenHardwareMonitor (OHM)

This directory contains all the necessary files for using OHM with the agent.
These files must be installed on the Checkmk site and shipped with the agent.

## Important security information

OHM is an inactive open-source project known to contain security-related bugs. For this reason, OHM is not part of Checkmk anymore and it is strongly advised not to use this extension at all. More specifically, Windows Defender startet to report VulnerableDriver:WinNT/Winring0.G (see CVE-2020-14979).

Use at your own risk, as doing so one means accepting that the vulnerability
can be exploited by others to compromise the affected system.

## Installation

If you choose to use OHM despite the warning above,
you must manually install the files in this folder to your Checkmk site.

First, log in as a site user:

    su - mysite

Second, copy the files to the local structure of your site:

    URL="https://github.com/Checkmk/checkmk/blob/master/doc/treasures/windows/ohm"
    wget "$URL/OpenHardwareMonitorCLI.exe" -P local/share/check_mk/agents/windows/
    wget $URL/OpenHardwareMonitorLib.dll" -P local/share/check_mk/agents/windows/

## Appendix

Reference build for Open Hardware Monitor.
Windows-10. 
MS Visual Studio 2017.