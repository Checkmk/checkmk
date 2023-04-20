// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHost_h
#define NebHost_h

#include <algorithm>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>

#include "CustomAttributeMap.h"
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
        return findCustomAttributeValue(host_.custom_variables,
                                        AttributeKind::custom_variables,
                                        "SERVICE_PERIOD")
            .value_or("");
    }

    bool all_of_services(
        std::function<bool(const IService &)> pred) const override;

    bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const override {
        // TODO(sp) Avoid construction of temporary map
        auto labels = CustomAttributeMap{AttributeKind::labels}(host_);
        return std::all_of(
            labels.cbegin(), labels.cend(),
            [&pred](const std::pair<std::string, std::string> &label) {
                return pred(Attribute{label.first, label.second});
            });
    }

private:
    const ::host &host_;
};

#endif  // NebHost_h
