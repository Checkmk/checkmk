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

#include "auth.h"
#include "MonitoringCore.h"
#include "contact_fwd.h"

contact *unknown_auth_user() { return reinterpret_cast<contact *>(0xdeadbeaf); }

namespace {
bool host_has_contact(const host *hst, const contact *ctc) {
    // Older Nagios headers are not const-correct... :-P
    return is_contact_for_host(const_cast<host *>(hst),
                               const_cast<contact *>(ctc)) != 0 ||
           is_escalated_contact_for_host(const_cast<host *>(hst),
                                         const_cast<contact *>(ctc)) != 0;
}

bool service_has_contact(MonitoringCore *mc, const host *hst,
                         const service *svc, const contact *ctc) {
    // Older Nagios headers are not const-correct... :-P
    return is_contact_for_service(const_cast<service *>(svc),
                                  const_cast<contact *>(ctc)) != 0 ||
           is_escalated_contact_for_service(const_cast<service *>(svc),
                                            const_cast<contact *>(ctc)) != 0 ||
           (mc->serviceAuthorization() == AuthorizationKind::loose &&
            host_has_contact(hst, ctc));
}
}  // namespace

bool is_authorized_for(MonitoringCore *mc, const contact *ctc, const host *hst,
                       const service *svc) {
    return ctc != unknown_auth_user() &&
           (svc == nullptr ? host_has_contact(hst, ctc)
                           : service_has_contact(mc, hst, svc, ctc));
}

bool is_authorized_for_host_group(MonitoringCore *mc, const hostgroup *hg,
                                  const contact *ctc) {
    if (ctc == nullptr) {
        return true;
    }
    // cppcheck false positive!
    // cppcheck-suppress knownConditionTrueFalse
    if (ctc == unknown_auth_user()) {
        return false;
    }

    auto has_contact = [=](hostsmember *mem) {
        return is_authorized_for(mc, ctc, mem->host_ptr, nullptr);
    };
    if (mc->groupAuthorization() == AuthorizationKind::loose) {
        // TODO(sp) Need an iterator here, "loose" means "any_of"
        for (hostsmember *mem = hg->members; mem != nullptr; mem = mem->next) {
            if (has_contact(mem)) {
                return true;
            }
        }
        return false;
    }
    // TODO(sp) Need an iterator here, "strict" means "all_of"
    for (hostsmember *mem = hg->members; mem != nullptr; mem = mem->next) {
        if (!has_contact(mem)) {
            return false;
        }
    }
    return true;
}

bool is_authorized_for_service_group(MonitoringCore *mc, const servicegroup *sg,
                                     const contact *ctc) {
    if (ctc == nullptr) {
        return true;
    }
    // cppcheck false positive!
    // cppcheck-suppress knownConditionTrueFalse
    if (ctc == unknown_auth_user()) {
        return false;
    }

    auto has_contact = [=](servicesmember *mem) {
        service *svc = mem->service_ptr;
        return is_authorized_for(mc, ctc, svc->host_ptr, svc);
    };
    if (mc->groupAuthorization() == AuthorizationKind::loose) {
        // TODO(sp) Need an iterator here, "loose" means "any_of"
        for (servicesmember *mem = sg->members; mem != nullptr;
             mem = mem->next) {
            if (has_contact(mem)) {
                return true;
            }
        }
        return false;
    }
    // TODO(sp) Need an iterator here, "strict" means "all_of"
    for (servicesmember *mem = sg->members; mem != nullptr; mem = mem->next) {
        if (!has_contact(mem)) {
            return false;
        }
    }
    return true;
}
