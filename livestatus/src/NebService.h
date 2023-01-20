// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebService_h
#define NebService_h

#include <memory>
#include <string>
#include <unordered_map>
#include <utility>

#include "NagiosCore.h"
#include "NebHost.h"
#include "livestatus/Attributes.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebService : public IService {
public:
    explicit NebService(const ::service &svc)
        : service_{svc}, host_{*svc.host_ptr} {}

    [[nodiscard]] const void *handle() const override { return &service_; }

    [[nodiscard]] const IHost &host() const override { return host_; }

    // Older Nagios headers are not const-correct... :-P
    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        auto *s = const_cast<::service *>(&service_);
        auto *c = const_cast<::contact *>(
            static_cast<const ::contact *>(contact.handle()));
        return is_contact_for_service(s, c) != 0 ||
               is_escalated_contact_for_service(s, c) != 0;
    }

    [[nodiscard]] std::string notificationPeriodName() const override {
        const auto *np = service_.notification_period;
        return np == nullptr ? "" : np;
    }

    [[nodiscard]] std::string servicePeriodName() const override {
        auto attrs = CustomAttributes(service_.custom_variables,
                                      AttributeKind::custom_variables);
        auto it = attrs.find("SERVICE_PERIOD");
        return it == attrs.end() ? "" : it->second;
    }

private:
    const ::service &service_;
    const NebHost host_;
};

inline std::unique_ptr<const IService> ToIService(::service *s) {
    return s != nullptr ? std::make_unique<NebService>(*s) : nullptr;
}

#endif  // NebService_h
