// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef nagios_h
#define nagios_h

#include "config.h"  // IWYU pragma: keep

// IWYU pragma: begin_exports
#ifdef CMC
#include "cmc.h"
#else
#define NSCORE
#ifdef NAGIOS4
#include "nagios4/broker.h"
#include "nagios4/common.h"
#include "nagios4/downtime.h"
#include "nagios4/logging.h"
#include "nagios4/macros.h"
#include "nagios4/nagios.h"
#include "nagios4/nebcallbacks.h"
#include "nagios4/neberrors.h"
#include "nagios4/nebmodules.h"
#include "nagios4/nebstructs.h"
#include "nagios4/objects.h"
#else
#include "nagios/broker.h"
#include "nagios/common.h"
#include "nagios/downtime.h"
#include "nagios/macros.h"
#include "nagios/nagios.h"
#include "nagios/nebcallbacks.h"
#include "nagios/neberrors.h"
#include "nagios/nebmodules.h"
#include "nagios/nebstructs.h"
#include "nagios/objects.h"
#endif  // NAGIOS4
#endif  // CMC
// IWYU pragma: end_exports
#endif  // nagios_h
