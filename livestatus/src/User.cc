// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "User.h"

#include <algorithm>
#include <vector>

#include "StringUtils.h"

#ifdef CMC
#include "ContactGroup.h"
#include "Host.h"         // IWYU pragma: keep
#include "ObjectGroup.h"  // IWYU pragma: keep
#include "Service.h"      // IWYU pragma: keep
#include "World.h"
#include "cmc.h"
#endif

namespace mk::ec {
// The funny encoding of an Optional[Iterable[str]] is done in
// cmk.ec.history.quote_tab().

bool is_none(const std::string &str) { return str == "\002"; }

std::vector<std::string> split_list(const std::string &str) {
    return str.empty() || is_none(str) ? std::vector<std::string>()
                                       : mk::split(str.substr(1), '\001');
}
}  // namespace mk::ec

AuthUser::AuthUser(const contact &auth_user, ServiceAuthorization service_auth,
                   GroupAuthorization group_auth)
    : auth_user_{auth_user}
    , service_auth_{service_auth}
    , group_auth_{group_auth} {}

bool AuthUser::is_authorized_for_object(const host *hst, const service *svc,
                                        bool authorized_if_no_host) const {
    return hst == nullptr   ? authorized_if_no_host
           : svc == nullptr ? is_authorized_for_host(*hst)
                            : is_authorized_for_service(*svc);
}

bool AuthUser::is_authorized_for_host(const host &hst) const {
    return host_has_contact(hst);
}

bool AuthUser::is_authorized_for_service(const service &svc) const {
#ifdef CMC
    const auto *hst = svc.host();
#else
    const auto *hst = svc.host_ptr;
#endif
    return service_has_contact(svc) ||
           (service_auth_ == ServiceAuthorization::loose &&
            host_has_contact(*hst));
}

bool AuthUser::is_authorized_for_host_group(const hostgroup &hg) const {
    auto is_authorized_for = [this](const host *hst) {
        return is_authorized_for_host(*hst);
    };
#ifdef CMC
    return group_auth_ == GroupAuthorization::loose
               ? std::any_of(hg.begin(), hg.end(), is_authorized_for)
               : std::all_of(hg.begin(), hg.end(), is_authorized_for);
#else
    if (group_auth_ == GroupAuthorization::loose) {
        for (hostsmember *mem = hg.members; mem != nullptr; mem = mem->next) {
            if (is_authorized_for(mem->host_ptr)) {
                return true;
            }
        }
        return false;
    }
    for (hostsmember *mem = hg.members; mem != nullptr; mem = mem->next) {
        if (!is_authorized_for(mem->host_ptr)) {
            return false;
        }
    }
    return true;
#endif
}

bool AuthUser::is_authorized_for_service_group(const servicegroup &sg) const {
    auto is_authorized_for = [this](const service *svc) {
        return is_authorized_for_service(*svc);
    };
#ifdef CMC
    return group_auth_ == GroupAuthorization::loose
               ? std::any_of(sg.begin(), sg.end(), is_authorized_for)
               : std::all_of(sg.begin(), sg.end(), is_authorized_for);
#else
    if (group_auth_ == GroupAuthorization::loose) {
        for (const auto *mem = sg.members; mem != nullptr; mem = mem->next) {
            if (is_authorized_for(mem->service_ptr)) {
                return true;
            }
        }
        return false;
    }
    for (const auto *mem = sg.members; mem != nullptr; mem = mem->next) {
        if (!is_authorized_for(mem->service_ptr)) {
            return false;
        }
    }
    return true;
#endif
}

bool AuthUser::is_authorized_for_event(const std::string &precedence,
                                       const std::string &contact_groups,
                                       const host *hst) const {
    auto is_authorized_via_contactgroups = [this, &contact_groups]() {
        auto groups{mk::ec::split_list(contact_groups)};
        return std::any_of(groups.begin(), groups.end(),
                           [this](const auto &group) {
                               return is_member_of_contactgroup(group);
                           });
    };
    if (precedence == "rule") {
        if (!mk::ec::is_none(contact_groups)) {
            return is_authorized_via_contactgroups();
        }
        if (hst != nullptr) {
            return is_authorized_for_host(*hst);
        }
        return true;
    }
    if (precedence == "host") {
        if (hst != nullptr) {
            return is_authorized_for_host(*hst);
        }
        if (!mk::ec::is_none(contact_groups)) {
            return is_authorized_via_contactgroups();
        }
        return true;
    }
    return false;
}

bool AuthUser::host_has_contact(const host &hst) const {
#ifdef CMC
    return hst.hasContact(&auth_user_);
#else
    // Older Nagios headers are not const-correct... :-P
    return is_contact_for_host(const_cast<host *>(&hst),
                               const_cast<contact *>(&auth_user_)) != 0 ||
           is_escalated_contact_for_host(const_cast<host *>(&hst),
                                         const_cast<contact *>(&auth_user_)) !=
               0;
#endif
}

bool AuthUser::service_has_contact(const service &svc) const {
#ifdef CMC
    return svc.hasContact(&auth_user_);
#else
    // Older Nagios headers are not const-correct... :-P
    return is_contact_for_service(const_cast<service *>(&svc),
                                  const_cast<contact *>(&auth_user_)) != 0 ||
           is_escalated_contact_for_service(
               const_cast<service *>(&svc),
               const_cast<contact *>(&auth_user_)) != 0;
#endif
}

bool AuthUser::is_member_of_contactgroup(const std::string &group) const {
#ifdef CMC
    const auto *cg = g_live_world->getContactGroup(group);
    return cg != nullptr && cg->isMember(&auth_user_);
#else
    // Older Nagios headers are not const-correct... :-P
    return ::is_contact_member_of_contactgroup(
               ::find_contactgroup(const_cast<char *>(group.c_str())),
               const_cast< ::contact *>(&auth_user_)) != 0;
#endif
}
