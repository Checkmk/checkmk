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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef pnp4nagios_h
#define pnp4nagios_h

#include "config.h"  // IWYU pragma: keep
#include <string>
class MonitoringCore;

#ifdef CMC
#include "FileSystem.h"
class Object;
#endif

inline std::string dummy_service_description() { return "_HOST_"; }

std::string pnp_cleanup(const std::string& name);

#ifndef CMC
int pnpgraph_present(MonitoringCore* mc, const std::string& host,
                     const std::string& service);
#endif

#ifdef CMC
// Determines if a RRD database exists and returns its path name. Returns an
// empty string otherwise. This assumes paths created in the PNP4Nagios style
// with storage type MULTIPLE.
fs::path rrd_path(MonitoringCore* mc, const Object* object,
                  const std::string& varname);
#endif

#endif  // pnp4nagios_h
