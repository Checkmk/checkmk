// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Collections.Generic;
using System.Configuration;
using System.Globalization;
using System.IO;

namespace OpenHardwareMonitor.CLI
{
    internal enum RunMode
    {
        Provider,
        Dump,
        Report,
        Help,
        Version
    }

    /// <summary>
    /// Settings come from (in this order, later wins):
    ///   1. built-in defaults (= the hardware groups the original OpenHardwareMonitorCLI enabled)
    ///   2. OpenHardwareMonitorCLI.exe.config  (appSettings, optional)
    ///   3. command line
    /// The Checkmk agent starts the EXE without arguments, so for agent deployments use the .config file.
    /// </summary>
    internal sealed class Options
    {
        public static readonly string[] AllGroups =
        {
            "cpu", "gpu", "memory", "motherboard", "controller", "storage", "network", "psu", "battery", "powermonitor"
        };

        // Same groups as the original OpenHardwareMonitorCLI: CPU, RAM, mainboard, fan controller, HDD.
        private static readonly string[] DefaultGroups = { "cpu", "memory", "motherboard", "controller", "storage" };

        public Options()
        {
            Groups = new HashSet<string>(DefaultGroups, StringComparer.OrdinalIgnoreCase);
            IntervalMs = 1000;
            CompatIdentifiers = true;
            Mode = RunMode.Provider;
            DumpCycles = 2;
        }

        public HashSet<string> Groups { get; private set; }
        public int IntervalMs { get; set; }
        public bool CompatIdentifiers { get; set; }
        public RunMode Mode { get; set; }
        public string LogFile { get; set; }
        public bool Verbose { get; set; }
        public bool NoWmi { get; set; }
        public int DumpCycles { get; set; }
        public bool IncludeHeader { get; set; }
        public int DurationSeconds { get; set; }

        public bool IsEnabled(string group)
        {
            return Groups.Contains(group);
        }

        public static Options Load(string[] args)
        {
            Options options = new Options();
            options.ApplyAppSettings();
            options.ApplyArguments(args);
            return options;
        }

        private void ApplyAppSettings()
        {
            try
            {
                string value = ConfigurationManager.AppSettings["Enable"];
                if (!string.IsNullOrWhiteSpace(value))
                    SetGroups(value, true);

                value = ConfigurationManager.AppSettings["Disable"];
                if (!string.IsNullOrWhiteSpace(value))
                    SetGroups(value, false);

                value = ConfigurationManager.AppSettings["IntervalMs"];
                if (!string.IsNullOrWhiteSpace(value))
                    IntervalMs = ParseInterval(value);

                value = ConfigurationManager.AppSettings["CompatIdentifiers"];
                if (!string.IsNullOrWhiteSpace(value))
                    CompatIdentifiers = ParseBool(value);

                value = ConfigurationManager.AppSettings["LogFile"];
                if (!string.IsNullOrWhiteSpace(value))
                    LogFile = ResolvePath(value);

                value = ConfigurationManager.AppSettings["Verbose"];
                if (!string.IsNullOrWhiteSpace(value))
                    Verbose = ParseBool(value);
            }
            catch (Exception e)
            {
                throw new ArgumentException("Invalid OpenHardwareMonitorCLI.exe.config: " + e.Message, e);
            }
        }

        private void ApplyArguments(string[] args)
        {
            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i];
                string key = arg;
                string value = null;

                int eq = arg.IndexOf('=');
                if (eq > 0)
                {
                    key = arg.Substring(0, eq);
                    value = arg.Substring(eq + 1);
                }

                key = key.TrimStart('-', '/').ToLowerInvariant();

                switch (key)
                {
                    case "h":
                    case "?":
                    case "help":
                        Mode = RunMode.Help;
                        break;

                    case "version":
                        Mode = RunMode.Version;
                        break;

                    case "d":
                    case "dump":
                        Mode = RunMode.Dump;
                        break;

                    case "header":
                        IncludeHeader = true;
                        break;

                    case "cycles":
                        DumpCycles = Math.Max(1, int.Parse(RequireValue(args, ref i, key, value), CultureInfo.InvariantCulture));
                        break;

                    case "r":
                    case "report":
                        Mode = RunMode.Report;
                        break;

                    case "enable":
                        SetGroups(RequireValue(args, ref i, key, value), true);
                        break;

                    case "disable":
                        SetGroups(RequireValue(args, ref i, key, value), false);
                        break;

                    case "all":
                        foreach (string g in AllGroups)
                            Groups.Add(g);
                        break;

                    case "interval":
                        IntervalMs = ParseInterval(RequireValue(args, ref i, key, value));
                        break;

                    case "native-ids":
                        CompatIdentifiers = false;
                        break;

                    case "compat-ids":
                        CompatIdentifiers = true;
                        break;

                    case "log":
                        LogFile = ResolvePath(RequireValue(args, ref i, key, value));
                        break;

                    case "v":
                    case "verbose":
                        Verbose = true;
                        break;

                    case "no-wmi":
                        NoWmi = true;
                        break;

                    case "duration":
                        DurationSeconds = Math.Max(1, int.Parse(RequireValue(args, ref i, key, value), CultureInfo.InvariantCulture));
                        break;

                    default:
                        throw new ArgumentException("Unknown option: " + arg + " (use --help)");
                }
            }
        }

        private static string RequireValue(string[] args, ref int i, string key, string value)
        {
            if (value != null)
                return value;

            if (i + 1 < args.Length && !args[i + 1].StartsWith("-", StringComparison.Ordinal))
                return args[++i];

            throw new ArgumentException("Option --" + key + " needs a value");
        }

        private void SetGroups(string list, bool enable)
        {
            foreach (string raw in list.Split(new[] { ',', ';', ' ' }, StringSplitOptions.RemoveEmptyEntries))
            {
                string group = NormalizeGroup(raw.Trim());

                if (group == "all")
                {
                    foreach (string g in AllGroups)
                    {
                        if (enable)
                            Groups.Add(g);
                        else
                            Groups.Remove(g);
                    }

                    continue;
                }

                if (Array.IndexOf(AllGroups, group) < 0)
                    throw new ArgumentException("Unknown hardware group '" + raw + "'. Valid: " + string.Join(", ", AllGroups) + ", all");

                if (enable)
                    Groups.Add(group);
                else
                    Groups.Remove(group);
            }
        }

        private static string NormalizeGroup(string group)
        {
            switch (group.ToLowerInvariant())
            {
                case "ram":
                    return "memory";
                case "mainboard":
                case "mb":
                    return "motherboard";
                case "fancontroller":
                case "fan":
                    return "controller";
                case "hdd":
                case "disk":
                case "disks":
                    return "storage";
                case "nic":
                    return "network";
                default:
                    return group.ToLowerInvariant();
            }
        }

        private static int ParseInterval(string value)
        {
            int ms = int.Parse(value.Trim(), CultureInfo.InvariantCulture);
            if (ms < 250)
                ms = 250;
            return ms;
        }

        private static bool ParseBool(string value)
        {
            switch (value.Trim().ToLowerInvariant())
            {
                case "1":
                case "true":
                case "yes":
                case "on":
                    return true;
                case "0":
                case "false":
                case "no":
                case "off":
                    return false;
                default:
                    throw new FormatException("'" + value + "' is not a boolean");
            }
        }

        private static string ResolvePath(string path)
        {
            path = Environment.ExpandEnvironmentVariables(path.Trim());
            return Path.IsPathRooted(path) ? path : Path.Combine(AppDomain.CurrentDomain.BaseDirectory, path);
        }

        public const string HelpText =
@"OpenHardwareMonitorCLI (LibreHardwareMonitor edition) - headless sensor provider for Checkmk

Without arguments the program runs like the original OpenHardwareMonitorCLI.exe:
it reads all sensors every second and publishes them via WMI in
root\OpenHardwareMonitor (classes Sensor and Hardware), where the Checkmk Windows
agent picks them up (section <<<openhardwaremonitor>>>). Run as administrator/SYSTEM.

Usage:
  OpenHardwareMonitorCLI.exe [options]

Modes:
  (none)              WMI provider, runs until terminated (used by the Checkmk agent)
  --dump, -d          Print sensors once in Checkmk format and exit (no WMI needed)
     --header         ... include the header line Index,Name,Parent,SensorType,Value
     --cycles=N       ... number of update cycles before printing (default 2)
  --report, -r        Print the full LibreHardwareMonitor diagnostic report and exit
  --version           Print versions and exit

Options:
  --enable=LIST       Enable hardware groups (comma separated)
  --disable=LIST      Disable hardware groups
  --all               Enable all hardware groups
                      Groups: cpu, gpu, memory, motherboard, controller, storage,
                              network, psu, battery, powermonitor
                      Default: cpu, memory, motherboard, controller, storage
  --interval=MS       Update interval in milliseconds (default 1000, min 250)
  --native-ids        Publish LibreHardwareMonitor identifiers unchanged
                      (default: OHM compatible, e.g. /nvme/0 -> /hdd/0, /gpu-nvidia/0 -> /nvidiagpu/0)
  --log=FILE          Write log messages to FILE
  --verbose, -v       More log output
  --no-wmi            Provider mode without publishing to WMI (testing)
  --duration=SEC      Provider mode: exit after SEC seconds (testing)

The same settings can be put into OpenHardwareMonitorCLI.exe.config (appSettings keys
Enable, Disable, IntervalMs, CompatIdentifiers, LogFile, Verbose).

Low level sensors (CPU temperature, mainboard/SuperIO, RAM SPD) require the PawnIO
driver: https://pawnio.eu  (winget install namazso.PawnIO)
";
    }
}
