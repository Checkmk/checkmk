// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System.ComponentModel;
using System.Management.Instrumentation;

// Same WMI namespace as the original OpenHardwareMonitorCLI.exe. The Checkmk Windows agent queries
// "SELECT Index,Name,Parent,SensorType,Value FROM Sensor" in Root\OpenHardwareMonitor.
// TODO(LHM rename): change together with kWmiPathOhm (agents/wnx/include/wnx/section_header.h)
// and the namespace in kResetCommand (agents/wnx/include/providers/ohm.h).
[assembly: Instrumented("root/OpenHardwareMonitor")]

/// <summary>
/// Allows the WMI schema to be registered up-front with InstallUtil.exe
/// (optional; the schema is also registered automatically on first start as administrator/SYSTEM).
/// </summary>
[RunInstaller(true)]
public class InstanceInstaller : DefaultManagementProjectInstaller
{
}
