// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

#include "IEventLog.h"
#include "EventLog.h"
#include "EventLogVista.h"
#include "Logger.h"

std::unique_ptr<IEventLog> open_eventlog(const std::wstring &name_or_path,
                                         bool try_vista_api, Logger *logger,
                                         const WinApiAdaptor &winapi) {
    if (try_vista_api) {
        try {
            return std::unique_ptr<IEventLog>(
                new EventLogVista(name_or_path, winapi));
        } catch (const UnsupportedException &) {
            Alert(logger) << "vista-style event-log api not available";
        }
    }
    return std::unique_ptr<IEventLog>(
        new EventLog(name_or_path, logger, winapi));
}
