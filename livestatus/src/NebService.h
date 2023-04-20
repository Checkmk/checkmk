// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebService_h
#define NebService_h

#include <algorithm>
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
    explicit NebService(const ::service &svc) : service_{svc} {}

    [[nodiscard]] const void *handle() const override { return &service_; }

    // Older Nagios headers are not const-correct... :-P
    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        auto *s = const_cast<::service *>(&service_);
        auto *c = const_cast<::contact *>(
            static_cast<const ::contact *>(contact.handle()));
        return is_contact_for_service(s, c) != 0 ||
               is_escalated_contact_for_service(s, c) != 0;
    }

    [[nodiscard]] bool hasHostContact(const IContact &contact) const override {
        return NebHost{*service_.host_ptr}.hasContact(contact);
    }

    [[nodiscard]] std::string notificationPeriodName() const override {
        const auto *np = service_.notification_period;
        return np == nullptr ? "" : np;
    }

    [[nodiscard]] std::string servicePeriodName() const override {
        return findCustomAttributeValue(service_.custom_variables,
                                        AttributeKind::custom_variables,
                                        "SERVICE_PERIOD")
            .value_or("");
    }

    bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const override {
        // TODO(sp) Avoid construction of temporary map
        auto labels = CustomAttributeMap{AttributeKind::labels}(service_);
        return std::all_of(
            labels.cbegin(), labels.cend(),
            [&pred](const std::pair<std::string, std::string> &label) {
                return pred(Attribute{label.first, label.second});
            });
    }

private:
    const ::service &service_;
};

// TODO(sp) Fix cruel workaround for circular header includes.
inline bool NebHost::all_of_services(
    std::function<bool(const IService &)> pred) const {
    for (servicesmember *mem = host_.services; mem != nullptr;
         mem = mem->next) {
        if (!pred(NebService{*mem->service_ptr})) {
            return false;
        }
    }
    return true;
}

#endif  // NebService_h
