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

#include "TableServicesByHostGroup.h"
#include "Query.h"
#include "TableHostgroups.h"
#include "TableServices.h"
#include "WorldNagios.h"
#include "auth.h"
class DowntimesOrComments;

using std::string;

extern hostgroup *hostgroup_list;

namespace {
struct servicebyhostgroup {
    service _service;
    hostgroup *_hostgroup;
};
}  // namespace

TableServicesByHostGroup::TableServicesByHostGroup(
    const DowntimesOrComments &downtimes_holder,
    const DowntimesOrComments &comments_holder, Logger *logger)
    : Table(logger) {
    struct servicebyhostgroup hgref;
    TableServices::addColumns(this, "", -1, true, downtimes_holder,
                              comments_holder);
    TableHostgroups::addColumns(this, "hostgroup_",
                                reinterpret_cast<char *>(&(hgref._hostgroup)) -
                                    reinterpret_cast<char *>(&hgref));
}

string TableServicesByHostGroup::name() const { return "servicesbyhostgroup"; }

string TableServicesByHostGroup::namePrefix() const { return "service_"; }

void TableServicesByHostGroup::answerQuery(Query *query) {
    for (hostgroup *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        for (hostsmember *mem = hg->members; mem != nullptr; mem = mem->next) {
            for (servicesmember *smem = mem->host_ptr->services;
                 smem != nullptr; smem = smem->next) {
                servicebyhostgroup sbhg = {*smem->service_ptr, hg};
                if (!query->processDataset(&sbhg)) {
                    break;
                }
            }
        }
    }
}

bool TableServicesByHostGroup::isAuthorized(contact *ctc, void *data) {
    service *svc = static_cast<service *>(data);
    return is_authorized_for(ctc, svc->host_ptr, svc);
}

void *TableServicesByHostGroup::findObject(const string &objectspec) {
    return getServiceBySpec(objectspec);
}
