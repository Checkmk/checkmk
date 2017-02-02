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

#ifndef TableDowntimes_h
#define TableDowntimes_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Table.h"
class Query;

#ifdef CMC
#include <mutex>
#include "Notes.h"
class Core;
#else
#include "nagios.h"
class DowntimesOrComments;
class MonitoringCore;
#endif

class TableDowntimes : public Table {
public:
#ifdef CMC
    TableDowntimes(const Downtimes &downtimes_holder,
                   const Comments &comments_holder,
                   std::recursive_mutex &holder_lock, Core *core);
#else
    TableDowntimes(const DowntimesOrComments &downtimes_holder,
                   const DowntimesOrComments &comments_holder,
                   MonitoringCore *core);
#endif

    std::string name() const override;
    std::string namePrefix() const override;
    void answerQuery(Query *) override;
    bool isAuthorized(contact *ctc, void *data) override;

private:
#ifdef CMC
    const Downtimes &_holder;
    std::recursive_mutex &_holder_lock;
#else
    const DowntimesOrComments &_holder;
#endif
};

#endif  // TableDowntimes_h
