/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System;
using OpenHardwareMonitor.Hardware;
using OpenHardwareMonitor.WMI;
using System.Timers;
using OpenHardwareMonitor.CLI;


namespace OpenHardwareMonitor.CLI
{
  public class DataProvider
  {
    private Computer _computer;
    private WmiProvider _wmiProvider;
    private Timer _timer;
    private UpdateVisitor _visitor;

    public DataProvider ()
    {
      _computer = new Computer ();
      // enable everything except for GPU which we can't monitor in a service anyway (keyword: session 0 isolation)
      _computer.CPUEnabled = _computer.FanControllerEnabled = _computer.HDDEnabled = _computer.RAMEnabled = _computer.MainboardEnabled = true;
      _computer.Open ();

      _wmiProvider = new WmiProvider (_computer);
      _wmiProvider.Update ();
      _visitor = new UpdateVisitor ();
      // tick once per second
      _timer = new Timer (1000.0);
      _timer.Elapsed += updateTick;
      _timer.AutoReset = true;
      _timer.Enabled = true;
    }

    public void start() {
      _timer.Enabled = true;
    }

    public void stop() {
      _timer.Enabled = false;
    }

    private void updateTick(Object source, ElapsedEventArgs args) {
      _computer.Accept (_visitor);
      _wmiProvider.Update ();
    }
  }
}

