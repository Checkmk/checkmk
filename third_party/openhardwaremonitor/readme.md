OpenHardwareMonitor USAGE
=========================

# Build

1. cd agents/wnx
2. build_ohm.cmd or build_release.cmd
3. check artefacts folder

Resulting build consists form 4 files
Thos files are to be placed in the resulting Distro(Classic) or
MSI(Future)

| File                       |  Classic |  Future  | Testing  |
|----------------------------|:--------:|:--------:|:--------:|
| OpenHardwareMonitorLib.dll |      +   |    +     |    +     |
| OpenHardwareMonitorLib.exe |      +   |          |          |
| ohm_bridge.dll             |          |    +     |    +     |
| ohm_host.exe               |          |          |    +     |
| ohm_call.exe               |          |          |    +     |

Classic is a current state with OHM distributed as exe + dll
Future is a next gen build with OHM distributed as dll + dll
Testing uses next gen build plus exe either in C# or in managed C++


# Update

1. Replace(or add) openhardwaremomonitor's zip with new one
2. Correctly set version OHM_VERSION in the check_mk/agents/wnx/Makefile
3. Set in check_mk/agents/wnx/ohm/ohm.sln correct version too
4. Set in check_mk/agents/wnx/ohm/OpenHardwareMonitorCLI/OpenHardwareMonitorCLI.csproj correct version too
