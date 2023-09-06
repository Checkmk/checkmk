/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System.Threading;


namespace Bridge
{
    public class Main
    {
        static DataProvider _provider;
        static bool _started = false;
        static bool _work = false;
        static Thread thr;
        static ThreadStart threadStart;
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
            _work = true;
            while (_started)
            {
                Thread.Sleep(50);
            }
            _provider.stop();
            _work = false;

        }

        public static void Start()
        {
            if (_started)
            {
                return;
            }
            _started = true;
            threadStart = new ThreadStart(Run);
            thr = new Thread(threadStart);
            thr.Start();
            int count = 0;
            while (!_work && count++ < 1000)
            {
                Thread.Sleep(50);
            }
        }
        public static void Stop()
        {
            _started = false;
            thr.Join();
        }
    }
}
