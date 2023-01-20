// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHost_h
#define NebHost_h

#include <memory>
#include <string>
#include <unordered_map>
#include <utility>

#include "NagiosCore.h"
#include "livestatus/Attributes.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebHost : public IHost {
public:
    explicit NebHost(const ::host &host) : host_{host} {}

    [[nodiscard]] const void *handle() const override { return &host_; }

    // Older Nagios headers are not const-correct... :-P
    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        auto *h = const_cast<::host *>(&host_);
        auto *c = const_cast<::contact *>(
            static_cast<const ::contact *>(contact.handle()));
        return ::is_contact_for_host(h, c) != 0 ||
               ::is_escalated_contact_for_host(h, c) != 0;
    }

    [[nodiscard]] std::string notificationPeriodName() const override {
        const auto *np = host_.notification_period;
        return np == nullptr ? "" : np;
    }

    [[nodiscard]] std::string servicePeriodName() const override {
        auto attrs = CustomAttributes(host_.custom_variables,
                                      AttributeKind::custom_variables);
        auto it = attrs.find("SERVICE_PERIOD");
        return it == attrs.end() ? "" : it->second;
    }

private:
    const ::host &host_;
};

inline std::unique_ptr<const IHost> ToIHost(const ::host *h) {
    return h != nullptr ? std::make_unique<NebHost>(*h) : nullptr;
}

#endif  // NebHost_h
