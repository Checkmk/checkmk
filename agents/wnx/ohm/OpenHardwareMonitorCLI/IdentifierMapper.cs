// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Collections.Generic;
using LibreHardwareMonitor.Hardware;

namespace OpenHardwareMonitor.CLI
{
    /// <summary>
    /// Translates LibreHardwareMonitor identifiers to the identifiers the original
    /// OpenHardwareMonitor used, so Checkmk service names (items) and the default
    /// temperature levels per device class ("cpu", "hdd", ...) stay the same.
    ///
    ///   LibreHardwareMonitor         OpenHardwareMonitor (compat mode)
    ///   /motherboard              -> /mainboard
    ///   /lpc/nct6798d/0           -> /lpc/nct6798d
    ///   /gpu-nvidia/0             -> /nvidiagpu/0
    ///   /gpu-amd/0                -> /atigpu/0
    ///   /nvme/1, /ata/0, /scsi/2  -> /hdd/1, /hdd/0, /hdd/2
    ///   /intelcpu/0, /amdcpu/0, /ram  unchanged
    ///
    /// Identifiers OHM never had (e.g. /gpu-intel-integrated/..., /memory/dimm/0, /vram,
    /// /nic/..., /battery/...) are passed through unchanged.
    ///
    /// TODO(LHM rename): the identifier mapping (MapIdentifier) exists only for the OHM based item names in
    /// cmk/plugins/openhardwaremonitor (_create_openhardwaremonitor_full_name). It can be dropped once the
    /// check plugins understand LibreHardwareMonitor identifiers. The other adaptations (GB conversion,
    /// limit values, fans, NaN and separator sanitizing) stay useful.
    /// </summary>
    public sealed class IdentifierMapper
    {
        private static readonly HashSet<string> StoragePrefixes = new HashSet<string>(StringComparer.Ordinal)
        {
            "ata", "scsi", "nvme", "usb", "sd", "mmc", "hdd", "ssd", "storage"
        };

        private const float BytesPerGigabyte = 1024f * 1024f * 1024f;

        // LibreHardwareMonitor up to 0.9.6 reported SensorType.Data in GB (and had SmallData in MB),
        // like OpenHardwareMonitor. Since commit 677a3a5 (2026-09-29) Data is reported in bytes and
        // SmallData no longer exists. Checkmk multiplies Data values by 2^30, i.e. expects GB.
        private static readonly bool DataIsInBytes = !Enum.IsDefined(typeof(SensorType), "SmallData");

        private readonly bool _compat;

        public IdentifierMapper(bool compat)
        {
            _compat = compat;
        }

        public static bool LibraryReportsDataInBytes
        {
            get { return DataIsInBytes; }
        }

        /// <summary>
        /// Factor applied to Value/Min/Max. In compat mode Data sensors are published in GB
        /// (OpenHardwareMonitor semantics) regardless of the LibreHardwareMonitor version.
        /// </summary>
        public float GetValueScale(ISensor sensor)
        {
            if (_compat && DataIsInBytes && sensor.SensorType == SensorType.Data)
                return 1f / BytesPerGigabyte;

            return 1f;
        }

        public bool Compat
        {
            get { return _compat; }
        }

        public string MapIdentifier(string identifier)
        {
            // Separators would break the agent's CSV output in every mode (see MapName).
            identifier = StripSeparators(identifier, '_');

            if (!_compat || string.IsNullOrEmpty(identifier) || identifier[0] != '/')
                return identifier;

            string[] parts = identifier.Substring(1).Split('/');
            if (parts.Length == 0)
                return identifier;

            switch (parts[0])
            {
                case "motherboard":
                    parts[0] = "mainboard";
                    break;

                case "gpu-nvidia":
                    parts[0] = "nvidiagpu";
                    break;

                case "gpu-amd":
                    parts[0] = "atigpu";
                    break;

                case "lpc":
                    // LHM: /lpc/<chip>/<index>[/<sensortype>/<n>]   OHM: /lpc/<chip>[/<sensortype>/<n>]
                    // Only the first SuperIO chip (index 0) is collapsed, further chips keep their index
                    // so identifiers stay unique.
                    if (parts.Length >= 3 && parts[1] != "ec" && parts[2] == "0")
                    {
                        List<string> list = new List<string>(parts);
                        list.RemoveAt(2);
                        parts = list.ToArray();
                    }
                    break;

                default:
                    if (StoragePrefixes.Contains(parts[0]) && parts.Length >= 2)
                        parts[0] = "hdd";
                    break;
            }

            return "/" + string.Join("/", parts);
        }

        /// <summary>
        /// Sensor name as published. In compat mode, storage sensors are renamed to the names
        /// the Checkmk check plugins expect from OHM (e.g. "Life" -> "Remaining Life", used by
        /// the openhardwaremonitor_smart check).
        /// </summary>
        public string MapSensorName(ISensor sensor)
        {
            string name = MapName(sensor.Name);
            if (!_compat)
                return name;

            if (IsStorage(sensor) && sensor.SensorType == SensorType.Level && name == "Life")
                return "Remaining Life";

            return name;
        }

        /// <summary>
        /// In compat mode, constant limit/configuration values that LibreHardwareMonitor reports as
        /// temperature sensors are not published. Checkmk would discover them as temperature services,
        /// and e.g. a DIMM "Thermal Sensor Critical High Limit" of 85 °C would be permanently CRIT.
        ///   NVMe:  Warning Temperature, Critical Temperature, Available Spare Threshold
        ///   DIMM:  Temperature Sensor Resolution, Thermal Sensor (Critical) Low/High Limit
        /// </summary>
        public bool IsExcluded(ISensor sensor)
        {
            if (!_compat)
                return false;

            string name = sensor.Name ?? "";

            if (sensor.SensorType == SensorType.Temperature)
            {
                if (name == "Warning Temperature" || name == "Critical Temperature")
                    return true;

                if (name.IndexOf("Limit", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    name.IndexOf("Resolution", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    name.IndexOf("Threshold", StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            }

            if (sensor.SensorType == SensorType.Level && IsStorage(sensor) && name == "Available Spare Threshold")
                return true;

            return false;
        }

        /// <summary>
        /// OpenHardwareMonitor only activated a fan sensor after it had reported a speed &gt; 0, so
        /// unconnected fan headers never appeared. In compat mode the same applies here.
        /// </summary>
        public bool PublishOnlyWhenActive(ISensor sensor)
        {
            return _compat && sensor.SensorType == SensorType.Fan;
        }

        private bool IsStorage(ISensor sensor)
        {
            IHardware hardware = sensor.Hardware;
            if (hardware == null)
                return false;

            if (hardware.HardwareType == HardwareType.Storage)
                return true;

            return MapIdentifier(hardware.Identifier.ToString()).StartsWith("/hdd/", StringComparison.Ordinal);
        }

        /// <summary>
        /// The Checkmk agent emits the WMI data as comma separated values (sep(44)), one sensor per
        /// line, and its parser drops every line that does not have exactly 5 (+ WMIStatus) columns.
        /// Commas and line breaks are therefore always replaced, in compat and native mode.
        /// </summary>
        public string MapName(string name)
        {
            return StripSeparators(name, ' ').Trim();
        }

        private static string StripSeparators(string value, char replacement)
        {
            if (value == null)
                return "";

            if (value.IndexOf(',') < 0 && value.IndexOf('\r') < 0 && value.IndexOf('\n') < 0)
                return value;

            return value.Replace(',', replacement).Replace('\r', replacement).Replace('\n', replacement);
        }

        /// <summary>
        /// The agent formats floats with std::to_wstring, which turns NaN into "-nan(ind)".
        /// Checkmk's parser cannot convert that and the whole openhardwaremonitor section fails
        /// (all services UNKNOWN). Invalid values are therefore published as 0, like a missing value.
        /// </summary>
        public static float SanitizeValue(float value)
        {
            return float.IsNaN(value) || float.IsInfinity(value) ? 0f : value;
        }
    }
}
