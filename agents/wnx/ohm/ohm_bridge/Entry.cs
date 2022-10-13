/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System;
using System.Runtime.InteropServices;
using System.Threading;


namespace OpenHardwareMonitor.Bridge
{
    public class Main
    {
        static DataProvider _provider;
        static bool _started = false;
        static Thread thr;
        public static void Entry()
        {
            if (_started)
            {
                return;
            }
            _started = true;
            Run();
            _started = false;
        }
        static void Run()
        {
            _provider = new DataProvider();
            while (_started)
            {
                Thread.Sleep(50);
            }
            _provider.stop();

        }

        public static void Start()
        {
            if (_started)
            {
                return;
            }
            _started = true;
            thr = new Thread(new ThreadStart(Run));
            thr.Start();
        }
        public static void Stop()
        {
            _started = false;
            thr.Join();
            thr.Join();
        }
    }
}
