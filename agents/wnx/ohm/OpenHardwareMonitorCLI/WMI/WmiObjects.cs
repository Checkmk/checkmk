// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
//
// Based on the WMI classes (WMI/Hardware.cs, WMI/Sensor.cs, WMI/IWmiObject.cs) of Open Hardware Monitor
// (https://github.com/openhardwaremonitor/openhardwaremonitor):
// Copyright (C) 2009-2010 Paul Werelds <paul@werelds.net>
// Adapted for LibreHardwareMonitor and the Checkmk Windows agent, 2026.
//
// WMI classes published in root\OpenHardwareMonitor.
// Class names, property names and property types are identical to the original
// OpenHardwareMonitorCLI.exe so the Checkmk agent and existing WMI consumers keep working.

using System.Management.Instrumentation;
using LibreHardwareMonitor.Hardware;
using OpenHardwareMonitor.CLI;

namespace OpenHardwareMonitor.WMI
{
    internal interface IWmiObject
    {
        string Name { get; }
        string Identifier { get; }
        void Update();
    }

    [InstrumentationClass(InstrumentationType.Instance)]
    public class Hardware : IWmiObject
    {
        public string HardwareType { get; private set; }
        public string Identifier { get; private set; }
        public string Name { get; private set; }
        public string Parent { get; private set; }

        internal Hardware(IHardware hardware, IdentifierMapper mapper)
        {
            Name = mapper.MapName(hardware.Name);
            Identifier = mapper.MapIdentifier(hardware.Identifier.ToString());
            HardwareType = hardware.HardwareType.ToString();
            Parent = hardware.Parent == null ? "" : mapper.MapIdentifier(hardware.Parent.Identifier.ToString());
        }

        public void Update()
        {
        }
    }

    [InstrumentationClass(InstrumentationType.Instance)]
    public class Sensor : IWmiObject
    {
        private readonly ISensor _sensor;
        private readonly float _scale;

        public string SensorType { get; private set; }
        public string Identifier { get; private set; }
        public string Parent { get; private set; }
        public string Name { get; private set; }
        public float Value { get; private set; }
        public float Min { get; private set; }
        public float Max { get; private set; }
        public int Index { get; private set; }

        internal Sensor(ISensor sensor, IdentifierMapper mapper)
        {
            _sensor = sensor;
            _scale = mapper.GetValueScale(sensor);
            Name = mapper.MapSensorName(sensor);
            Index = sensor.Index;
            SensorType = sensor.SensorType.ToString();
            Identifier = mapper.MapIdentifier(sensor.Identifier.ToString());
            Parent = mapper.MapIdentifier(sensor.Hardware.Identifier.ToString());
        }

        internal string RawIdentifier
        {
            get { return _sensor.Identifier.ToString(); }
        }

        public void Update()
        {
            float? value = _sensor.Value;
            Value = value.HasValue ? IdentifierMapper.SanitizeValue(value.Value * _scale) : 0f;

            float? min = _sensor.Min;
            if (min.HasValue)
                Min = IdentifierMapper.SanitizeValue(min.Value * _scale);

            float? max = _sensor.Max;
            if (max.HasValue)
                Max = IdentifierMapper.SanitizeValue(max.Value * _scale);
        }
    }
}
