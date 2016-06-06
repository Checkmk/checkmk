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

#ifndef TableEventConsoleHistory_h
#define TableEventConsoleHistory_h

#include "config.h"  // IWYU pragma: keep
#include "TableEventConsole.h"
#ifdef CMC
#include <mutex>
class Core;
class Notes;
#else
class DowntimesOrComments;
#endif

class TableEventConsoleHistory : public TableEventConsole {
public:
#ifdef CMC
    TableEventConsoleHistory(const Notes &downtimes_holder,
                             const Notes &comments_holder,
                             std::recursive_mutex &holder_lock, Core *core);
#else
    TableEventConsoleHistory(const DowntimesOrComments &downtimes_holder,
                             const DowntimesOrComments &comments_holder);
#endif
    const char *name() const override;
    const char *namePrefix() const override;
};

#endif  // TableEventConsoleHistory_h
