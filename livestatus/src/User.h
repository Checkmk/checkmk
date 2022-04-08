// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef auth_h
#define auth_h

#include "config.h"  // IWYU pragma: keep

#include <string>
#include <vector>

#ifdef CMC
#include "contact_fwd.h"
class Host;  // IWYU pragma: keep
using host = Host;
class Service;  // IWYU pragma: keep
using service = Service;
// IWYU pragma: no_include "ObjectGroup.h"
template <typename T>
class ObjectGroup;  // IWYU pragma: keep
using hostgroup = ObjectGroup<Host>;
using servicegroup = ObjectGroup<Service>;
#else
#include "nagios.h"
#endif

enum class ServiceAuthorization {
    loose = 0,   // contacts for hosts see all services
    strict = 1,  // must be explicit contact of a service
};

enum class GroupAuthorization {
    loose = 0,   // sufficient to be contact for one member
    strict = 1,  // must be contact of all members

};

namespace mk::ec {
// The funny encoding of an Optional[Iterable[str]] is done in
// cmk.ec.history.quote_tab().
bool is_none(const std::string &str);
std::vector<std::string> split_list(const std::string &str);
}  // namespace mk::ec

class User {
public:
    virtual ~User() = default;

    [[nodiscard]] virtual bool is_authorized_for_object(
        const host *hst, const service *svc,
        bool authorized_if_no_host) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_host(
        const host &hst) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_service(
        const service &svc) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_host_group(
        const hostgroup &hg) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_service_group(
        const servicegroup &sg) const = 0;
    [[nodiscard]] virtual bool is_authorized_for_event(
        const std::string &precedence, const std::string &contact_groups,
        const host *hst) const = 0;
};

class AuthUser : public User {
public:
    AuthUser(const contact &auth_user, ServiceAuthorization service_auth,
             GroupAuthorization group_auth);

    [[nodiscard]] bool is_authorized_for_object(
        const host *hst, const service *svc,
        bool authorized_if_no_host) const override;
    [[nodiscard]] bool is_authorized_for_host(const host &hst) const override;
    [[nodiscard]] bool is_authorized_for_service(
        const service &svc) const override;
    [[nodiscard]] bool is_authorized_for_host_group(
        const hostgroup &hg) const override;
    [[nodiscard]] bool is_authorized_for_service_group(
        const servicegroup &sg) const override;
    [[nodiscard]] bool is_authorized_for_event(
        const std::string &precedence, const std::string &contact_groups,
        const host *hst) const override;

private:
    const contact &auth_user_;
    ServiceAuthorization service_auth_;
    GroupAuthorization group_auth_;

    [[nodiscard]] bool host_has_contact(const host &hst) const;
    [[nodiscard]] bool service_has_contact(const service &svc) const;
    [[nodiscard]] bool is_member_of_contactgroup(
        const std::string &group) const;
};

class NoAuthUser : public User {
public:
    [[nodiscard]] bool is_authorized_for_object(
        const host * /*hst*/, const service * /*svc*/,
        bool /*authorized_if_no_host*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_host(
        const host & /*hst*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_service(
        const service & /*svc*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_host_group(
        const hostgroup & /*hg*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_service_group(
        const servicegroup & /*sg*/) const override {
        return true;
    }
    [[nodiscard]] bool is_authorized_for_event(
        const std::string & /*precedence*/,
        const std::string & /*contact_groups*/,
        const host * /*hst*/) const override {
        return true;
    }
};

class UnknownUser : public User {
public:
    [[nodiscard]] bool is_authorized_for_object(
        const host *hst, const service * /*svc*/,
        bool authorized_if_no_host) const override {
        return hst == nullptr && authorized_if_no_host;
    }
    [[nodiscard]] bool is_authorized_for_host(
        const host & /*hst*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_service(
        const service & /*svc*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_host_group(
        const hostgroup & /*hg*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_service_group(
        const servicegroup & /*sg*/) const override {
        return false;
    }
    [[nodiscard]] bool is_authorized_for_event(
        const std::string & /*precedence*/,
        const std::string & /*contact_groups*/,
        const host * /*hst*/) const override {
        return false;
    }
};

#endif  // auth_h
