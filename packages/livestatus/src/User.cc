// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/User.h"

#include <algorithm>
#include <vector>

#include "livestatus/Interface.h"

AuthUser::AuthUser(const IContact &auth_user, ServiceAuthorization service_auth,
                   GroupAuthorization group_auth)
    : auth_user_{auth_user}
    , service_auth_{service_auth}
    , group_auth_{group_auth} {}

bool AuthUser::is_authorized_for_object(
    const std::unique_ptr<const IHost> hst,
    const std::unique_ptr<const IService> svc,
    bool authorized_if_no_host) const {
    return !hst   ? authorized_if_no_host
           : !svc ? is_authorized_for_host(*hst)
                  : is_authorized_for_service(*svc);
}

bool AuthUser::is_authorized_for_host(const IHost &hst) const {
    return host_has_contact(hst);
}

bool AuthUser::is_authorized_for_service(const IService &svc) const {
    return service_has_contact(svc) ||
           (service_auth_ == ServiceAuthorization::loose &&
            host_has_contact(svc.host()));
}

bool AuthUser::is_authorized_for_host_group(const IHostGroup &hg) const {
    auto is_authorized_for = [this](const std::unique_ptr<const IHost> &hst) {
        return is_authorized_for_host(*hst);
    };

    return group_auth_ == GroupAuthorization::loose
               ? std::any_of(hg.hosts().begin(), hg.hosts().end(),
                             is_authorized_for)
               : std::all_of(hg.hosts().begin(), hg.hosts().end(),
                             is_authorized_for);
}

bool AuthUser::is_authorized_for_service_group(const IServiceGroup &sg) const {
    auto is_authorized_for =
        [this](const std::unique_ptr<const IService> &svc) {
            return is_authorized_for_service(*svc);
        };

    return group_auth_ == GroupAuthorization::loose
               ? std::any_of(sg.services().begin(), sg.services().end(),
                             is_authorized_for)
               : std::all_of(sg.services().begin(), sg.services().end(),
                             is_authorized_for);
}

bool AuthUser::is_authorized_for_event(
    const std::string &precedence,
    const std::vector<std::unique_ptr<const IContactGroup>> &contact_groups,
    const IHost *hst) const {
    auto is_authorized_via_contactgroups = [this, &contact_groups]() {
        return std::any_of(contact_groups.begin(), contact_groups.end(),
                           [this](const auto &group) {
                               return is_member_of_contactgroup(*group);
                           });
    };
    if (precedence == "rule") {
        if (!contact_groups.empty()) {
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
        if (!contact_groups.empty()) {
            return is_authorized_via_contactgroups();
        }
        return true;
    }
    return false;
}

bool AuthUser::host_has_contact(const IHost &hst) const {
    return hst.hasContact(auth_user_);
}

bool AuthUser::service_has_contact(const IService &svc) const {
    return svc.hasContact(auth_user_);
}

bool AuthUser::is_member_of_contactgroup(
    const IContactGroup &contact_group) const {
    return contact_group.isMember(auth_user_);
}
