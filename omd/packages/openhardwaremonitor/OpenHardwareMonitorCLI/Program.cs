/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System;
using System.Timers;
using OpenHardwareMonitor.Hardware;
using OpenHardwareMonitor.WMI;
using System.Runtime.InteropServices;
using System.Threading;


namespace OpenHardwareMonitor.CLI
{
  class CLI
  {
    static DataProvider _provider;

    static void ExitHandler(object o, EventArgs args)
    {
      _provider.stop ();
    }

    public static void Main (string[] args)
    {
      _provider = new DataProvider ();
      AppDomain.CurrentDomain.ProcessExit += ExitHandler;
      Console.CancelKeyPress += ExitHandler;

      // wait until terminated
      while (true) {
        Thread.Sleep (500);
      }

    }
  }
}
