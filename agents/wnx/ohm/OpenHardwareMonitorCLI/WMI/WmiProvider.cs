// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
//
// Based on the WMI provider (WMI/WmiProvider.cs) of Open Hardware Monitor
// (https://github.com/openhardwaremonitor/openhardwaremonitor):
// Copyright (C) 2009-2010 Paul Werelds <paul@werelds.net>
// Copyright (C) 2012 Michael Möller <mmoeller@openhardwaremonitor.org>
// Adapted for LibreHardwareMonitor and the Checkmk Windows agent, 2026.

using System;
using System.Collections.Generic;
using System.Management.Instrumentation;
using LibreHardwareMonitor.Hardware;
using OpenHardwareMonitor.CLI;

namespace OpenHardwareMonitor.WMI
{
    /// <summary>
    /// Publishes hardware and sensors as WMI instances (decoupled WMI.NET provider),
    /// mirroring the behaviour of the original OpenHardwareMonitorCLI.exe.
    /// </summary>
    internal sealed class WmiProvider : IDisposable
    {
        private readonly object _lock = new object();
        private readonly IdentifierMapper _mapper;
        private readonly bool _publish;
        private List<IWmiObject> _activeInstances = new List<IWmiObject>();

        // Sensors that are only published once they report a value > 0 (fans in compat mode,
        // like OpenHardwareMonitor did: unconnected fan headers never show up).
        private readonly List<Sensor> _pending = new List<Sensor>();
        private int _publishErrors;

        public WmiProvider(IComputer computer, IdentifierMapper mapper, bool publish)
        {
            _mapper = mapper;
            _publish = publish;

            foreach (IHardware hardware in computer.Hardware)
                ComputerHardwareAdded(hardware);

            computer.HardwareAdded += ComputerHardwareAdded;
            computer.HardwareRemoved += ComputerHardwareRemoved;
        }

        public int PublishErrors
        {
            get { return _publishErrors; }
        }

        /// <summary>Snapshot of all currently known WMI objects.</summary>
        public List<IWmiObject> Snapshot()
        {
            lock (_lock)
                return _activeInstances == null ? new List<IWmiObject>() : new List<IWmiObject>(_activeInstances);
        }

        public void Update()
        {
            lock (_lock)
            {
                if (_activeInstances == null)
                    return;

                foreach (IWmiObject instance in _activeInstances)
                {
                    try
                    {
                        instance.Update();
                    }
                    catch (Exception e)
                    {
                        Log.Debug("Update of " + instance.Identifier + " failed: " + e.Message);
                    }
                }

                for (int i = _pending.Count - 1; i >= 0; i--)
                {
                    Sensor sensor = _pending[i];
                    try
                    {
                        sensor.Update();
                    }
                    catch (Exception)
                    {
                        continue;
                    }

                    if (sensor.Value > 0)
                    {
                        _pending.RemoveAt(i);
                        _activeInstances.Add(sensor);
                        Publish(sensor);
                        Log.Debug("Sensor became active: " + sensor.Identifier + " (" + sensor.Name + ")");
                    }
                }
            }
        }

        private void ComputerHardwareAdded(IHardware hardware)
        {
            lock (_lock)
            {
                if (_activeInstances == null)
                    return;

                if (!Exists(_mapper.MapIdentifier(hardware.Identifier.ToString())))
                {
                    foreach (ISensor sensor in hardware.Sensors)
                        HardwareSensorAdded(sensor);

                    hardware.SensorAdded += HardwareSensorAdded;
                    hardware.SensorRemoved += HardwareSensorRemoved;

                    Hardware hw = new Hardware(hardware, _mapper);
                    _activeInstances.Add(hw);
                    Publish(hw);
                    Log.Debug("Hardware added: " + hw.Identifier + " (" + hw.Name + ", " + hw.HardwareType + ")");
                }

                foreach (IHardware subHardware in hardware.SubHardware)
                    ComputerHardwareAdded(subHardware);
            }
        }

        private void HardwareSensorAdded(ISensor data)
        {
            lock (_lock)
            {
                if (_activeInstances == null)
                    return;

                if (_mapper.IsExcluded(data))
                {
                    Log.Debug("Skipping sensor " + data.Identifier + " (" + data.Name + ")");
                    return;
                }

                // LHM keeps a 24h value history per sensor by default (for the GUI plots).
                // A headless provider never needs it - disable it to keep memory flat.
                try
                {
                    data.ValuesTimeWindow = TimeSpan.Zero;
                }
                catch (Exception)
                {
                    // not supported by this sensor implementation
                }

                Sensor sensor = new Sensor(data, _mapper);
                if (Exists(sensor.Identifier))
                    return;

                sensor.Update();

                if (_mapper.PublishOnlyWhenActive(data) && !(sensor.Value > 0))
                {
                    _pending.Add(sensor);
                    Log.Debug("Sensor deferred until it reports a value: " + sensor.Identifier + " (" + sensor.Name + ")");
                    return;
                }

                _activeInstances.Add(sensor);
                Publish(sensor);
            }
        }

        private void ComputerHardwareRemoved(IHardware hardware)
        {
            lock (_lock)
            {
                hardware.SensorAdded -= HardwareSensorAdded;
                hardware.SensorRemoved -= HardwareSensorRemoved;

                foreach (ISensor sensor in hardware.Sensors)
                    HardwareSensorRemoved(sensor);

                foreach (IHardware subHardware in hardware.SubHardware)
                    ComputerHardwareRemoved(subHardware);

                RevokeInstance(_mapper.MapIdentifier(hardware.Identifier.ToString()));
            }
        }

        private void HardwareSensorRemoved(ISensor sensor)
        {
            lock (_lock)
                RevokeInstance(_mapper.MapIdentifier(sensor.Identifier.ToString()));
        }

        private bool Exists(string identifier)
        {
            return _activeInstances.Exists(h => h.Identifier == identifier) ||
                   _pending.Exists(h => h.Identifier == identifier);
        }

        private void RevokeInstance(string identifier)
        {
            if (_activeInstances == null)
                return;

            _pending.RemoveAll(item => item.Identifier == identifier);

            int index = _activeInstances.FindIndex(item => item.Identifier == identifier);
            if (index == -1)
                return;

            Revoke(_activeInstances[index]);
            _activeInstances.RemoveAt(index);
        }

        private void Publish(object instance)
        {
            if (!_publish)
                return;

            try
            {
                Instrumentation.Publish(instance);
            }
            catch (Exception e)
            {
                _publishErrors++;
                if (_publishErrors <= 3)
                    Log.Warn("WMI publish failed (are we running as administrator/SYSTEM?): " + e.Message);
            }
        }

        private void Revoke(object instance)
        {
            if (!_publish)
                return;

            try
            {
                Instrumentation.Revoke(instance);
            }
            catch (Exception)
            {
                // ignored, same as original implementation
            }
        }

        public void Dispose()
        {
            lock (_lock)
            {
                if (_activeInstances == null)
                    return;

                foreach (IWmiObject instance in _activeInstances)
                    Revoke(instance);

                _activeInstances = null;
                _pending.Clear();
            }
        }
    }
}
