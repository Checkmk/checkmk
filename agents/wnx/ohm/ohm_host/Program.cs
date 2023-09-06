/*

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Copyright (C) 2016 Mathias Kettner GmbH

*/



using System;
using System.Threading;


namespace Host
{
    class CLI
    {
        static void ExitHandler(object o, EventArgs args)
        {
            Bridge.Main.Stop();
            Console.WriteLine("Exit");
        }

        public static void Main(string[] args)
        {
            AppDomain.CurrentDomain.ProcessExit += ExitHandler;
            Console.CancelKeyPress += ExitHandler;

            Console.WriteLine("Start");

            if (args.Length == 0)
            {
                Bridge.Main.Entry();
            }
            else
            {
                try
                {
                    int number = Int32.Parse(args[0]);
                    Bridge.Main.Start();
                    Thread.Sleep(number);
                    Bridge.Main.Stop();
                }
                catch (FormatException)
                {
                    Console.WriteLine("{0}: Bad Format", args[0]);
                }
                catch (OverflowException)
                {
                    Console.WriteLine("{0}: Overflow", args[0]);
                }
            }
        }
    }
}
