// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Globalization;
using System.IO;

namespace OpenHardwareMonitor.CLI
{
    /// <summary>Minimal logger: stderr and an optional log file (size-capped).</summary>
    internal static class Log
    {
        private const long MaxLogSize = 5 * 1024 * 1024;
        private static readonly object Sync = new object();

        public static string FilePath { get; set; }
        public static bool Verbose { get; set; }
        public static bool Quiet { get; set; }

        public static void Info(string message)
        {
            Write("INFO ", message);
        }

        public static void Warn(string message)
        {
            Write("WARN ", message);
        }

        public static void Error(string message)
        {
            Write("ERROR", message);
        }

        public static void Debug(string message)
        {
            if (Verbose)
                Write("DEBUG", message);
        }

        private static void Write(string level, string message)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + " " + level + " " + message;

            lock (Sync)
            {
                if (!Quiet)
                {
                    try
                    {
                        Console.Error.WriteLine(line);
                    }
                    catch (Exception)
                    {
                        // no console attached
                    }
                }

                if (string.IsNullOrEmpty(FilePath))
                    return;

                try
                {
                    FileInfo info = new FileInfo(FilePath);
                    if (info.Exists && info.Length > MaxLogSize)
                    {
                        string old = FilePath + ".old";
                        if (File.Exists(old))
                            File.Delete(old);
                        File.Move(FilePath, old);
                    }

                    File.AppendAllText(FilePath, line + Environment.NewLine);
                }
                catch (Exception)
                {
                    // logging must never break the provider
                }
            }
        }
    }
}
