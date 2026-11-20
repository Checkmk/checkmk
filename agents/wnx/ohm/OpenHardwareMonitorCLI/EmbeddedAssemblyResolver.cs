// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

namespace OpenHardwareMonitor.CLI
{
    /// <summary>
    /// Resolves the dependencies of the CLI without additional files on disk:
    ///
    ///  * LibreHardwareMonitorLib  -> OpenHardwareMonitorLib.dll next to the EXE
    ///    (this is the file name the Checkmk agent bakery deploys)
    ///  * everything else (HidSharp, DiskInfoToolkit, RAMSPDToolkit, System.Memory, ...)
    ///    -> embedded resources "deps.&lt;name&gt;.dll" inside this EXE
    ///
    /// Regular .NET probing still wins: if a real LibreHardwareMonitorLib.dll / HidSharp.dll
    /// lies next to the EXE, it is used and this resolver is never asked.
    /// </summary>
    internal static class EmbeddedAssemblyResolver
    {
        private const string LhmAssemblyName = "LibreHardwareMonitorLib";
        // TODO(LHM rename): LibreHardwareMonitorLib.dll is shipped as OpenHardwareMonitorLib.dll only because
        // the bakery plugin (cmk/base/plugins/bakery/win_openhardwaremonitor.py) deploys that file name.
        private const string LhmFileName = "OpenHardwareMonitorLib.dll";

        private static readonly Dictionary<string, Assembly> Loaded = new Dictionary<string, Assembly>(StringComparer.OrdinalIgnoreCase);
        private static readonly object Sync = new object();
        private static bool _installed;

        public static void Install()
        {
            if (_installed)
                return;

            _installed = true;
            AppDomain.CurrentDomain.AssemblyResolve += OnAssemblyResolve;
        }

        private static Assembly OnAssemblyResolve(object sender, ResolveEventArgs args)
        {
            AssemblyName requested = new AssemblyName(args.Name);
            string name = requested.Name;

            // Localized satellite assemblies are not shipped on purpose (stable, English sensor
            // names on every host). Returning null makes ResourceManager use the neutral resources.
            if (name.EndsWith(".resources", StringComparison.OrdinalIgnoreCase))
                return null;

            lock (Sync)
            {
                Assembly assembly;
                if (Loaded.TryGetValue(name, out assembly))
                    return assembly;

                // Already loaded under the same simple name (e.g. different version requested)?
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (string.Equals(a.GetName().Name, name, StringComparison.OrdinalIgnoreCase))
                    {
                        Loaded[name] = a;
                        return a;
                    }
                }

                assembly = LoadAssembly(name);
                if (assembly != null)
                    Loaded[name] = assembly;

                return assembly;
            }
        }

        private static Assembly LoadAssembly(string name)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;

            if (string.Equals(name, LhmAssemblyName, StringComparison.OrdinalIgnoreCase))
            {
                string path = Path.Combine(baseDir, LhmFileName);
                if (File.Exists(path))
                    return Assembly.LoadFrom(path);
            }

            Assembly self = typeof(EmbeddedAssemblyResolver).Assembly;
            string resourceName = "deps." + name + ".dll";

            byte[] data = ReadResource(self, resourceName);
            if (data != null)
                return Assembly.Load(data);

            // Fallback: the embedded file name may differ from the assembly name.
            // Load the remaining embedded assemblies and look for a matching identity.
            foreach (string candidate in self.GetManifestResourceNames())
            {
                if (!candidate.StartsWith("deps.", StringComparison.Ordinal))
                    continue;

                byte[] bytes = ReadResource(self, candidate);
                if (bytes == null)
                    continue;

                Assembly assembly = Assembly.Load(bytes);
                string simpleName = assembly.GetName().Name;
                if (!Loaded.ContainsKey(simpleName))
                    Loaded[simpleName] = assembly;

                if (string.Equals(simpleName, name, StringComparison.OrdinalIgnoreCase))
                    return assembly;
            }

            return null;
        }

        private static readonly HashSet<string> LoadedResources = new HashSet<string>(StringComparer.Ordinal);

        private static byte[] ReadResource(Assembly assembly, string resourceName)
        {
            if (LoadedResources.Contains(resourceName))
                return null;

            using (Stream stream = assembly.GetManifestResourceStream(resourceName))
            {
                if (stream == null)
                    return null;

                LoadedResources.Add(resourceName);

                byte[] data = new byte[stream.Length];
                int offset = 0;
                while (offset < data.Length)
                {
                    int read = stream.Read(data, offset, data.Length - offset);
                    if (read <= 0)
                        break;
                    offset += read;
                }

                return data;
            }
        }
    }
}
