#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

normsize = 20.0

import sys
if len(sys.argv) > 1:
   normsize = float(sys.argv[1])

def print_levels(exp):
   sys.stdout.write("f=%3.1f: " % exp)
   for size in [ 5, 10, 20, 50, 100, 300, 800 ]:
        hgb_size = size / normsize
        felt_size = hgb_size ** exp
        scale = felt_size / hgb_size
        new_level = 1 - ((1 - level) * scale)
        freegb = size * (1.0 - new_level)
        sys.stdout.write("%4.0fGB:%4.0f%%(%3.0fG) " % (size, new_level * 100, freegb))
   sys.stdout.write("\n")

for level in [ .80, .85, .90, .95 ]:
  sys.stdout.write("Level for %.0f GB Normpartition: %d%%\n" % (normsize, int(level * 100)))
  for exp in [ 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2 ]:
      print_levels(exp)
  sys.stdout.write("-" * 80)
  sys.stdout.write("\n")



