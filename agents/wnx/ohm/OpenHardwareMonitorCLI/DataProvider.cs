// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

using System;
using System.Threading;
using LibreHardwareMonitor.Hardware;
using OpenHardwareMonitor.WMI;

namespace OpenHardwareMonitor.CLI
{
    /// <summary>
    /// Owns the LibreHardwareMonitor Computer object, the WMI provider and the update timer.
    /// </summary>
    internal sealed class DataProvider : IDisposable
    {
        private readonly Computer _computer;
        private readonly UpdateVisitor _visitor = new UpdateVisitor();
        private readonly Options _options;
        private WmiProvider _wmiProvider;
        private Timer _timer;
        private int _updating;
        private bool _disposed;

        public DataProvider(Options options, bool publishToWmi)
        {
            _options = options;

            _computer = new Computer
            {
                IsCpuEnabled = options.IsEnabled("cpu"),
                IsGpuEnabled = options.IsEnabled("gpu"),
                IsMemoryEnabled = options.IsEnabled("memory"),
                IsMotherboardEnabled = options.IsEnabled("motherboard"),
                IsControllerEnabled = options.IsEnabled("controller"),
                IsStorageEnabled = options.IsEnabled("storage"),
                IsNetworkEnabled = options.IsEnabled("network"),
                IsPsuEnabled = options.IsEnabled("psu"),
                IsBatteryEnabled = options.IsEnabled("battery"),
                IsPowerMonitorEnabled = options.IsEnabled("powermonitor")
            };

            Log.Debug("Opening LibreHardwareMonitor (groups: " + string.Join(",", options.Groups) + ")");
            _computer.Open();

            UpdateNow();

            _wmiProvider = new WmiProvider(_computer, new IdentifierMapper(options.CompatIdentifiers), publishToWmi);
            _wmiProvider.Update();
        }

        public IComputer Computer
        {
            get { return _computer; }
        }

        public WmiProvider Wmi
        {
            get { return _wmiProvider; }
        }

        public void Start()
        {
            if (_timer == null)
                _timer = new Timer(OnTick, null, _options.IntervalMs, _options.IntervalMs);
            else
                _timer.Change(_options.IntervalMs, _options.IntervalMs);
        }

        public void Stop()
        {
            if (_timer != null)
                _timer.Change(Timeout.Infinite, Timeout.Infinite);
        }

        /// <summary>Runs one full update cycle synchronously.</summary>
        public void UpdateNow()
        {
            _computer.Accept(_visitor);
            if (_wmiProvider != null)
                _wmiProvider.Update();
        }

        private void OnTick(object state)
        {
            // Never run two updates in parallel (slow SMART/GPU reads can exceed the interval).
            if (Interlocked.CompareExchange(ref _updating, 1, 0) != 0)
                return;

            try
            {
                if (!_disposed)
                    UpdateNow();
            }
            catch (Exception e)
            {
                Log.Warn("Update cycle failed: " + e.Message);
            }
            finally
            {
                Interlocked.Exchange(ref _updating, 0);
            }
        }

        public void Dispose()
        {
            if (_disposed)
                return;

            _disposed = true;

            if (_timer != null)
            {
                using (ManualResetEvent done = new ManualResetEvent(false))
                {
                    _timer.Dispose(done);
                    done.WaitOne(5000);
                }

                _timer = null;
            }

            if (_wmiProvider != null)
            {
                _wmiProvider.Dispose();
                _wmiProvider = null;
            }

            try
            {
                _computer.Close();
            }
            catch (Exception e)
            {
                Log.Debug("Computer.Close failed: " + e.Message);
            }
        }
    }
}
