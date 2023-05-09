// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "auth.h"

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

bool service_has_contact(AuthorizationKind service_auth, const host *hst,
                         const service *svc, const contact *ctc) {
    // Older Nagios headers are not const-correct... :-P
    return is_contact_for_service(const_cast<service *>(svc),
                                  const_cast<contact *>(ctc)) != 0 ||
           is_escalated_contact_for_service(const_cast<service *>(svc),
                                            const_cast<contact *>(ctc)) != 0 ||
           (service_auth == AuthorizationKind::loose &&
            host_has_contact(hst, ctc));
}
}  // namespace

bool is_authorized_for(AuthorizationKind service_auth, const contact *ctc,
                       const host *hst, const service *svc) {
    return ctc != unknown_auth_user() &&
           (svc == nullptr ? host_has_contact(hst, ctc)
                           : service_has_contact(service_auth, hst, svc, ctc));
}

bool is_authorized_for_host_group(AuthorizationKind group_auth,
                                  AuthorizationKind service_auth,
                                  const hostgroup *hg, const contact *ctc) {
    if (ctc == nullptr) {
        return true;
    }
    // cppcheck false positive!
    // cppcheck-suppress knownConditionTrueFalse
    if (ctc == unknown_auth_user()) {
        return false;
    }

    auto has_contact = [=](hostsmember *mem) {
        return is_authorized_for(service_auth, ctc, mem->host_ptr, nullptr);
    };
    if (group_auth == AuthorizationKind::loose) {
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

bool is_authorized_for_service_group(AuthorizationKind group_auth,
                                     AuthorizationKind service_auth,
                                     const servicegroup *sg,
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
        return is_authorized_for(service_auth, ctc, svc->host_ptr, svc);
    };
    if (group_auth == AuthorizationKind::loose) {
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
