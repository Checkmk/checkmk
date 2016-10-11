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

#include "TableEventConsoleHistory.h"
#include <string>
#include "TableEventConsoleEvents.h"

#ifdef CMC
#include "ContactGroup.h"
#include "Host.h"
#include "World.h"
#else
#include "auth.h"
#endif

using std::string;

#ifdef CMC
TableEventConsoleHistory::TableEventConsoleHistory(
    const Downtimes &downtimes_holder, const Comments &comments_holder,
    std::recursive_mutex &holder_lock, Core *core)
    : TableEventConsole(core)
#else
TableEventConsoleHistory::TableEventConsoleHistory(
    const DowntimesOrComments &downtimes_holder,
    const DowntimesOrComments &comments_holder, Logger *logger)
    : TableEventConsole(logger)
#endif
{
    addColumn(new IntEventConsoleColumn(
        "history_line", "The line number of the event in the history file"));
    addColumn(new TimeEventConsoleColumn("history_time",
                                         "Time when the event was written into "
                                         "the history file (Unix timestamp)"));
    addColumn(new StringEventConsoleColumn(
        "history_what",
        "What happened (one of "
        "ARCHIVED/AUTODELETE/CANCELLED/CHANGESTATE/COUNTFAILED/COUNTREACHED/"
        "DELAYOVER/DELETE/EMAIL/EXPIRED/NEW/NOCOUNT/ORPHANED/SCRIPT/UPDATE)"));
    addColumn(new StringEventConsoleColumn(
        "history_who", "The user who triggered the command"));
    addColumn(new StringEventConsoleColumn(
        "history_addinfo",
        "Additional information, like email recipient/subject or action ID"));
    TableEventConsoleEvents::addColumns(this, downtimes_holder, comments_holder
#ifdef CMC
                                        ,
                                        holder_lock, core
#endif
                                        );
}

string TableEventConsoleHistory::name() const { return "eventconsolehistory"; }

string TableEventConsoleHistory::namePrefix() const {
    return "eventconsolehistory_";
}

// TODO(sp) Move this into some kind of abstraction layer.
namespace {
bool hasContact(host *hst, contact *ctc) {
#ifdef CMC
    return hst != nullptr && hst->hasContact(ctc);
#else
    return is_authorized_for(ctc, hst, nullptr);
#endif
}

bool hasContact(contactgroup *cg, contact *ctc) {
#ifdef CMC
    return cg != nullptr && cg->isMember(ctc);
#else
    return is_contact_member_of_contactgroup(cg, ctc) != 0;
#endif
}

contactgroup *getContactGroup(const string &name) {
#ifdef CMC
    return g_live_world->getContactGroup(name);
#else
    // Older Nagios headers are not const-correct... :-P
    return find_contactgroup(const_cast<char *>(name.c_str()));
#endif
}
}  // namespace

// TODO(sp) This is copy-n-pasted in TableEventConsoleEvents.
bool TableEventConsoleHistory::isAuthorized(contact *ctc, void *data) {
    if (host *hst = static_cast<Row *>(data)->_host) {
        return hasContact(hst, ctc);
    }

    ListEventConsoleColumn *col =
        static_cast<ListEventConsoleColumn *>(column("event_contact_groups"));
    if (col->isNone(data)) {
        return true;
    }

    for (const auto &name : col->getValue(data)) {
        if (hasContact(getContactGroup(name), ctc)) {
            return true;
        }
    }
    return false;
}
