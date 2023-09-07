/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/


using System;
using System.Collections.Generic;
using OpenHardwareMonitor.Hardware;


namespace OpenHardwareMonitor.CLI
{
  public class UpdateVisitor : IVisitor
  {

    #region IVisitor implementation

    public void VisitComputer (IComputer computer)
    {
      computer.Traverse (this);
    }

    public void VisitHardware (IHardware hardware)
    {
      hardware.Update();
      foreach (IHardware sub in hardware.SubHardware) {
        sub.Accept (this);
      }
    }

    public void VisitSensor (ISensor sensor)
    {
      // nop
    }

    public void VisitParameter (IParameter parameter)
    {
      // nop
    }

    #endregion
  }
}
 
