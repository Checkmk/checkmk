# OpenHardwareMonitorCLI based on LibreHardwareMonitor

Headless replacement for the `OpenHardwareMonitorCLI.exe` that provides the agent section
`<<<openhardwaremonitor>>>`. Open Hardware Monitor was removed from the distribution with
[Werk #18537](https://checkmk.com/werk/18537) because Windows Defender reports its WinRing0 driver as
vulnerable (CVE-2020-14979). This implementation uses the actively developed
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) library and the
signed [PawnIO](https://pawnio.eu) driver instead.

It is a drop-in replacement: no changes are needed in the Windows agent, in the bakery plugin
`win_openhardwaremonitor` or in the check plugins `cmk/plugins/openhardwaremonitor`.

## Important: Open Hardware Monitor naming is a temporary compatibility layer

To work with the current, unchanged agent and bakery, this CLI deliberately presents itself as Open
Hardware Monitor, i.e. "Libre" becomes "Open":

- the executable is named `OpenHardwareMonitorCLI.exe`, assembly and C# namespaces are
  `OpenHardwareMonitor.*`
- `LibreHardwareMonitorLib.dll` is shipped renamed as `OpenHardwareMonitorLib.dll`
- the sensors are published in the WMI namespace `root\OpenHardwareMonitor`
- LibreHardwareMonitor identifiers are translated to Open Hardware Monitor identifiers (`/nvme/0` →
  `/hdd/0`, `/motherboard` → `/mainboard`, ...)

This is not meant to stay. For the official integration, the naming should be changed to
LibreHardwareMonitor **on both sides in one change**, otherwise agent and CLI no longer find each other.

In Checkmk:

- `agents/wnx/include/providers/ohm.h`: `kExeModule` / `kExeModuleWide` (`OpenHardwareMonitorCLI.exe`),
  `kResetCommand` (deletes the WMI namespace `OpenHardwareMonitor`), `kDriverNameWide`
  (`winring0_1_2_0`, obsolete with PawnIO)
- `agents/wnx/include/wnx/section_header.h`: `kWmiPathOhm` (`Root\OpenHardwareMonitor`) and the section
  name `kOhm` (`openhardwaremonitor`)
- `agents/wnx/src/engine/providers/ohm.cpp` and `agents/wnx/src/engine/providers/wmi.cpp` (WMI object
  `Sensor` and its columns)
- `cmk/base/plugins/bakery/win_openhardwaremonitor.py` (deployed file names) and
  `cmk/plugins/collection/rulesets/win_openhardwaremonitor.py` (rule title and help text)
- `agents/wnx/Makefile` (`PACKAGE_OHM`, `OHM_VERSION`), `third_party/openhardwaremonitor`,
  `doc/treasures/windows/ohm`, `agents/wnx/scripts/tools/openhardwaremonitor-clean.cmd`,
  `doc/treasures/windows/openhardwaremonitor-clean.cmd`
- `cmk/plugins/openhardwaremonitor`: the section and plugin names and the item naming in
  `_create_openhardwaremonitor_full_name`. Keeping them avoids vanished services; if the CLI publishes
  native LibreHardwareMonitor identifiers, the item naming has to handle them (e.g. `nvme`,
  `gpu-nvidia`, `memory/dimm`).

In this CLI (all places are marked with `TODO(LHM rename)`):

- `OpenHardwareMonitorCLI.csproj`: `AssemblyName` and the renaming of `LibreHardwareMonitorLib.dll` in
  the target `CreateDist`
- `EmbeddedAssemblyResolver.cs`: `LhmFileName`
- `AssemblyInfo.cs`: `[assembly: Instrumented("root/OpenHardwareMonitor")]`
- `Program.cs` and the other files: namespaces `OpenHardwareMonitor.CLI` / `OpenHardwareMonitor.WMI`,
  mutex name and help text
- `IdentifierMapper.cs`: the identifier mapping can be dropped once the check plugins understand
  LibreHardwareMonitor identifiers. The other adaptations (GB conversion, limit values, fans, NaN and
  separator sanitizing) stay useful.

## How it works

- Same behaviour as the original CLI: all sensors are read every second and published as WMI instances
  in `root\OpenHardwareMonitor` (classes `Sensor` and `Hardware`, same properties and types). The agent
  starts `bin\OpenHardwareMonitorCLI.exe` without arguments and queries
  `SELECT Index,Name,Parent,SensorType,Value FROM Sensor`.
- Same two files as before, so the bakery can deploy them unchanged:
  - `OpenHardwareMonitorCLI.exe` contains all dependencies (HidSharp, DiskInfoToolkit, RAMSPDToolkit,
    System.Memory, ...) as embedded resources and loads them itself.
  - `OpenHardwareMonitorLib.dll` is the unmodified `LibreHardwareMonitorLib.dll`, renamed.
- Default hardware groups are the ones the original CLI enabled: CPU, memory, mainboard, fan
  controllers and storage.

## Compatibility with the check plugins

All adjustments are in [`OpenHardwareMonitorCLI/IdentifierMapper.cs`](OpenHardwareMonitorCLI/IdentifierMapper.cs):

- LibreHardwareMonitor identifiers are mapped to the Open Hardware Monitor ones, so existing service
  names stay the same: `/nvme/0`, `/ata/1`, ... → `/hdd/0`, `/hdd/1`; `/motherboard` → `/mainboard`;
  `/lpc/<chip>/0` → `/lpc/<chip>`; `/gpu-nvidia/0` → `/nvidiagpu/0`; `/gpu-amd/0` → `/atigpu/0`.
- `Data` sensors are published in GB. LibreHardwareMonitor reports bytes since commit
  [677a3a5](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/commit/677a3a5); the parser
  multiplies `Data` by 2^30.
- The storage sensor `Life` is published as `Remaining Life`, which `openhardwaremonitor_smart` expects.
- Constant limit values that LibreHardwareMonitor reports as temperatures are not published (NVMe
  `Warning/Critical Temperature`, DIMM `Thermal Sensor ... Limit`, `Temperature Sensor Resolution`).
  They would be discovered as temperature services that are permanently CRIT.
- Fans are published after their first rotation, like in Open Hardware Monitor, so unconnected fan
  headers do not show up as services with 0 RPM.
- Commas and line breaks in names and identifiers are replaced (the section uses `sep(44)`).
- NaN and infinite values are published as 0. The agent formats NaN with `std::to_wstring` as
  `-nan(ind)`, and `float()` in the parser fails for the whole section.
- Localized satellite assemblies are not shipped, so sensor names do not depend on the Windows display
  language.

`--native-ids` (or `CompatIdentifiers=false`) publishes the LibreHardwareMonitor data unchanged.

## Requirements on the monitored host

- Windows x64, .NET Framework 4.7.2 or newer
- PawnIO driver for CPU, mainboard (SuperIO) and DIMM sensors, e.g. `winget install namazso.PawnIO`.
  Without it, storage (SMART/NVMe), CPU load and memory usage still work.

## Build

Requirements: git and the .NET 10 SDK (`winget install Microsoft.DotNet.SDK.10`).

```console
build.cmd                 :: LibreHardwareMonitor at the pinned, tested commit
build.cmd <commit|tag>    :: any other LibreHardwareMonitor revision
```

`build.cmd` fetches LibreHardwareMonitor into `external\LibreHardwareMonitor` and builds the library
from source together with the CLI. The result is written to `dist\`:
`OpenHardwareMonitorCLI.exe`, `OpenHardwareMonitorLib.dll` and an example configuration.

Alternatively, the last stable NuGet release can be used:

```console
dotnet build OpenHardwareMonitorCLI\OpenHardwareMonitorCLI.csproj -c Release -p:LhmSource=nuget
```

## Deployment

- Bakery: copy both files to `local/share/check_mk/agents/windows/` and enable the rule
  _OpenHardwareMonitor (Windows)_.
- Manually: copy both files to `C:\ProgramData\checkmk\agent\bin` and restart the agent service.

## Testing

```console
OpenHardwareMonitorCLI.exe --dump --header   :: sensors in agent format, without WMI
OpenHardwareMonitorCLI.exe --version         :: versions and PawnIO status
OpenHardwareMonitorCLI.exe --help            :: all options
```

What has been verified:

- The current agent code (`agents/wnx`: process start, WMI query, value formatting, status column),
  the bakery plugin and the check plugins were reviewed against this implementation.
- Parser, discovery and all five check plugins (clock, temperature, fan, power, SMART) were executed with
  real sensor data of a Ryzen system (NVMe and SATA SSDs, Nuvoton NCT6799D, DDR5); the existing unit
  tests in `tests/unit/cmk/plugins/openhardwaremonitor` pass.
- On `windows-latest` (GitHub Actions), the CLI was built from the LibreHardwareMonitor source and the
  WMI query of the agent returned the published sensors.

The standalone project with CI and release builds is maintained at
<https://github.com/Tinnitus97/Libre_Hardware_Monitor_checkmk>.

## Configuration (optional)

Rename `OpenHardwareMonitorCLI.exe.config.example` to `OpenHardwareMonitorCLI.exe.config` next to the
executable. Keys: `Enable`/`Disable` (hardware groups `cpu, gpu, memory, motherboard, controller,
storage, network, psu, battery, powermonitor, all`), `IntervalMs`, `CompatIdentifiers`, `LogFile`,
`Verbose`. The same settings exist as command line options.

## Licensing

- New files are licensed under the GNU GPL v2 like the rest of the agent.
- `OpenHardwareMonitorCLI/WMI/*.cs` and `OpenHardwareMonitorCLI/UpdateVisitor.cs` are based on Open
  Hardware Monitor and remain under the Mozilla Public License 2.0, which is compatible with the GPL
  (MPL-2.0 section 3.3).
- LibreHardwareMonitor (MPL-2.0) and its dependencies are fetched at build time and keep their own
  licenses.

## Open points for the integration

- Rename the Open Hardware Monitor compatibility layer to LibreHardwareMonitor on both sides, see
  [above](#important-open-hardware-monitor-naming-is-a-temporary-compatibility-layer).
- Build pipeline: `agents/wnx/Makefile` still extracts `third_party/openhardwaremonitor`. The
  LibreHardwareMonitor revision could be provided the same way (`third_party/librehardwaremonitor`)
  instead of being fetched by `build.cmd`.
- Distribution of the PawnIO driver (prerequisite, optional agent dependency or documentation).
- `doc/treasures/windows/ohm` and the text of Werk #18537 still point to the old binaries.
- Independent of this CLI, the parser could skip lines with non-numeric values, and the default
  temperature levels (`cpu` 60/70 °C, `hdd` 40/50 °C) are low for current hardware.
