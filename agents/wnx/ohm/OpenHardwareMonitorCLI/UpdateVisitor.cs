// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
//
// Based on the update visitor (GUI/UpdateVisitor.cs) of Open Hardware Monitor
// (https://github.com/openhardwaremonitor/openhardwaremonitor):
// Copyright (C) 2009-2010 Michael Möller <mmoeller@openhardwaremonitor.org>
// Adapted for LibreHardwareMonitor and the Checkmk Windows agent, 2026.

using System;
using LibreHardwareMonitor.Hardware;

namespace OpenHardwareMonitor.CLI
{
    /// <summary>Visitor that updates every hardware node (same as in the original CLI).</summary>
    internal sealed class UpdateVisitor : IVisitor
    {
        public void VisitComputer(IComputer computer)
        {
            computer.Traverse(this);
        }

        public void VisitHardware(IHardware hardware)
        {
            try
            {
                hardware.Update();
            }
            catch (Exception e)
            {
                Log.Debug("Update of " + hardware.Identifier + " failed: " + e.Message);
            }

            foreach (IHardware subHardware in hardware.SubHardware)
                subHardware.Accept(this);
        }

        public void VisitSensor(ISensor sensor)
        {
        }

        public void VisitParameter(IParameter parameter)
        {
        }
    }
}
