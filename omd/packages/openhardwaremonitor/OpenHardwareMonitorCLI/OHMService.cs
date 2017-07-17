/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System;
using System.ServiceProcess;


namespace OpenHardwareMonitor.CLI
{
  public class OHMService : System.ServiceProcess.ServiceBase
  {
    DataProvider _provider;

    public OHMService ()
    {
      this.ServiceName = "Open Hardware Monitor";
      this.CanStop = true;
      this.CanPauseAndContinue = true;
      this.AutoLog = true;

      _provider = new DataProvider ();
    }

    protected override void OnStart (string[] args)
    {
      base.OnStart (args);
      _provider.start ();
    }

    protected override void OnPause ()
    {
      _provider.stop ();
      base.OnPause ();
    }

    protected override void OnContinue ()
    {
      base.OnContinue ();
      _provider.start ();
    }
  }
}

