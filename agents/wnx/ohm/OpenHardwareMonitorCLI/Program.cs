// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Principal;
using System.Text;
using System.Threading;
using Microsoft.Win32;
using OpenHardwareMonitor.WMI;

// TODO(LHM rename): the namespaces OpenHardwareMonitor.CLI / OpenHardwareMonitor.WMI and the executable name
// are kept from Open Hardware Monitor for compatibility with the unchanged agent (see agents/wnx/ohm/README.md).
namespace OpenHardwareMonitor.CLI
{
    internal static class Program
    {
        private const string InstanceMutexName = @"Global\OpenHardwareMonitorCLI_LibreHardwareMonitor";

        private static readonly ManualResetEvent ExitEvent = new ManualResetEvent(false);

        public static int Main(string[] args)
        {
            // Must happen before any LibreHardwareMonitor type is touched (JIT of Run()).
            EmbeddedAssemblyResolver.Install();

            try
            {
                return Run(args);
            }
            catch (Exception e)
            {
                Log.Error(e.ToString());
                return 1;
            }
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static int Run(string[] args)
        {
            Options options;
            try
            {
                options = Options.Load(args);
            }
            catch (Exception e)
            {
                Console.Error.WriteLine(e.Message);
                return 2;
            }

            Log.FilePath = options.LogFile;
            Log.Verbose = options.Verbose;

            switch (options.Mode)
            {
                case RunMode.Help:
                    Console.WriteLine(Options.HelpText);
                    return 0;

                case RunMode.Version:
                    PrintVersion();
                    return 0;

                case RunMode.Dump:
                    return RunDump(options);

                case RunMode.Report:
                    return RunReport(options);

                default:
                    return RunProvider(options);
            }
        }

        private static int RunProvider(Options options)
        {
            bool createdNew;
            using (Mutex mutex = new Mutex(true, InstanceMutexName, out createdNew))
            {
                if (!createdNew)
                {
                    Log.Warn("Another OpenHardwareMonitorCLI instance is already running - exiting.");
                    return 0;
                }

                Log.Info("Starting " + VersionString() + ", interval " + options.IntervalMs + " ms, groups: " +
                         string.Join(",", options.Groups) + (options.CompatIdentifiers ? ", OHM compatible identifiers" : ", native identifiers"));
                CheckEnvironment();

                using (DataProvider provider = new DataProvider(options, !options.NoWmi))
                {
                    Log.Info("Publishing " + provider.Wmi.Snapshot().Count + " WMI objects in root\\OpenHardwareMonitor" +
                             (options.NoWmi ? " (disabled by --no-wmi)" : ""));

                    Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs e)
                    {
                        e.Cancel = true;
                        ExitEvent.Set();
                    };
                    AppDomain.CurrentDomain.ProcessExit += delegate { ExitEvent.Set(); };

                    provider.Start();
                    if (options.DurationSeconds > 0)
                        ExitEvent.WaitOne(TimeSpan.FromSeconds(options.DurationSeconds));
                    else
                        ExitEvent.WaitOne();

                    Log.Info("Stopping");
                    provider.Stop();
                }

                mutex.ReleaseMutex();
            }

            return 0;
        }

        private static int RunDump(Options options)
        {
            CheckEnvironment();

            using (DataProvider provider = new DataProvider(options, false))
            {
                // Load values need two samples - do a few cycles before printing.
                for (int i = 1; i < options.DumpCycles; i++)
                {
                    Thread.Sleep(Math.Min(options.IntervalMs, 1000));
                    provider.UpdateNow();
                }

                List<Sensor> sensors = new List<Sensor>();
                foreach (IWmiObject o in provider.Wmi.Snapshot())
                {
                    Sensor s = o as Sensor;
                    if (s != null)
                        sensors.Add(s);
                }

                sensors.Sort(delegate(Sensor a, Sensor b)
                {
                    int c = string.CompareOrdinal(a.Parent, b.Parent);
                    if (c == 0)
                        c = string.CompareOrdinal(a.SensorType, b.SensorType);
                    if (c == 0)
                        c = a.Index.CompareTo(b.Index);
                    return c;
                });

                StringBuilder sb = new StringBuilder();
                sb.AppendLine("<<<openhardwaremonitor:sep(44)>>>");
                if (options.IncludeHeader)
                    sb.AppendLine("Index,Name,Parent,SensorType,Value");

                foreach (Sensor s in sensors)
                {
                    sb.Append(s.Index.ToString(CultureInfo.InvariantCulture)).Append(',')
                      .Append(s.Name).Append(',')
                      .Append(s.Parent).Append(',')
                      .Append(s.SensorType).Append(',')
                      .Append(s.Value.ToString("0.000000", CultureInfo.InvariantCulture))
                      .AppendLine();
                }

                Console.Write(sb.ToString());
            }

            return 0;
        }

        private static int RunReport(Options options)
        {
            CheckEnvironment();

            using (DataProvider provider = new DataProvider(options, false))
            {
                Thread.Sleep(1000);
                provider.UpdateNow();
                Console.WriteLine(provider.Computer.GetReport());
            }

            return 0;
        }

        private static void CheckEnvironment()
        {
            if (!IsElevated())
                Log.Warn("Not running as administrator - most sensors will be missing and WMI publishing will fail.");

            string pawnIo = GetPawnIoVersion();
            if (pawnIo == null)
                Log.Warn("PawnIO driver is not installed - CPU temperatures, mainboard (SuperIO) and RAM SPD sensors are unavailable. " +
                         "Install it from https://pawnio.eu or: winget install namazso.PawnIO");
            else
                Log.Debug("PawnIO driver version " + pawnIo);
        }

        private static bool IsElevated()
        {
            try
            {
                using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
                    return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator) || identity.IsSystem;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private static string GetPawnIoVersion()
        {
            const string key = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO";

            foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
            {
                try
                {
                    using (RegistryKey baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view))
                    using (RegistryKey sub = baseKey.OpenSubKey(key))
                    {
                        string version = sub == null ? null : sub.GetValue("DisplayVersion") as string;
                        if (!string.IsNullOrEmpty(version))
                            return version;
                    }
                }
                catch (Exception)
                {
                    // ignored
                }
            }

            return null;
        }

        private static string VersionString()
        {
            return "OpenHardwareMonitorCLI " + typeof(Program).Assembly.GetName().Version +
                   " (LibreHardwareMonitorLib " + LhmVersion() + ")";
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static string LhmVersion()
        {
            Assembly lhm = typeof(LibreHardwareMonitor.Hardware.Computer).Assembly;
            AssemblyInformationalVersionAttribute info =
                (AssemblyInformationalVersionAttribute)Attribute.GetCustomAttribute(lhm, typeof(AssemblyInformationalVersionAttribute));
            return info != null ? info.InformationalVersion : lhm.GetName().Version.ToString();
        }

        private static void PrintVersion()
        {
            Console.WriteLine(VersionString());
            Console.WriteLine("Data unit: " + (IdentifierMapper.LibraryReportsDataInBytes ? "bytes (converted to GB in compat mode)" : "GB"));
            Console.WriteLine("Runtime: .NET Framework " + Environment.Version + (Environment.Is64BitProcess ? " (64 bit)" : " (32 bit)"));
            string pawnIo = GetPawnIoVersion();
            Console.WriteLine("PawnIO:  " + (pawnIo ?? "not installed"));
        }
    }
}
