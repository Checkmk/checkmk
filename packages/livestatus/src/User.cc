// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/User.h"

#include <algorithm>
#include <utility>

#include "livestatus/Interface.h"
#include "livestatus/StringUtils.h"

AuthUser::AuthUser(const IContact &auth_user, ServiceAuthorization service_auth,
                   GroupAuthorization group_auth,
                   std::function<const IContactGroup *(const std::string &)>
                       find_contact_group)
    : auth_user_{auth_user}
    , service_auth_{service_auth}
    , group_auth_{group_auth}
    , find_contact_group_{std::move(find_contact_group)} {}

bool AuthUser::is_authorized_for_object(const IHost *hst, const IService *svc,
                                        bool authorized_if_no_host) const {
    return hst == nullptr   ? authorized_if_no_host
           : svc == nullptr ? is_authorized_for_host(*hst)
                            : is_authorized_for_service(*svc);
}

bool AuthUser::is_authorized_for_host(const IHost &hst) const {
    return hst.hasContact(auth_user_);
}

bool AuthUser::is_authorized_for_service(const IService &svc) const {
    return svc.hasContact(auth_user_) ||
           (service_auth_ == ServiceAuthorization::loose &&
            svc.host().hasContact(auth_user_));
}

bool AuthUser::is_authorized_for_host_group(const IHostGroup &hg) const {
    return group_auth_ == GroupAuthorization::loose
               ? !hg.all([this](const IHost &hst) {  // any, De Morgan's law
                     return !is_authorized_for_host(hst);
                 })
               : hg.all([this](const IHost &hst) {
                     return is_authorized_for_host(hst);
                 });
}

bool AuthUser::is_authorized_for_service_group(const IServiceGroup &sg) const {
    return group_auth_ == GroupAuthorization::loose
               ? !sg.all([this](const IService &hst) {  // any, De Morgan's law
                     return !is_authorized_for_service(hst);
                 })
               : sg.all([this](const IService &hst) {
                     return is_authorized_for_service(hst);
                 });
}

bool AuthUser::is_authorized_for_event(const std::string &precedence,
                                       const std::string &contact_groups,
                                       const IHost *hst) const {
    auto is_authorized_via_contactgroups = [this, &contact_groups]() {
        auto groups{mk::ec::split_list(contact_groups)};
        return std::ranges::any_of(groups, [this](const auto &group) {
            const auto *cg = find_contact_group_(group);
            return cg && cg->isMember(auth_user_);
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
