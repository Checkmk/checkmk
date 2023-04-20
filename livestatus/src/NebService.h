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

#include "CustomAttributeMap.h"
#include "NagiosCore.h"
#include "NebHost.h"
#include "livestatus/Attributes.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebService : public IService {
public:
    explicit NebService(const ::service &svc)
        : service_{svc}, host_{NebHost{*svc.host_ptr}} {}

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
        return findCustomAttributeValue(service_.custom_variables,
                                        AttributeKind::custom_variables,
                                        "SERVICE_PERIOD")
            .value_or("");
    }

    [[nodiscard]] bool in_custom_time_period() const override {
        const auto tp = servicePeriodName();
        // empty assumes 24X7
        return tp.empty() || g_timeperiods_cache->inTimeperiod(tp);
    }

    [[nodiscard]] std::string name() const override {
        return service_.description;
    }

    [[nodiscard]] std::string description() const override {
        return service_.description;
    }
    [[nodiscard]] std::string plugin_output() const override {
        return service_.plugin_output == nullptr ? "" : service_.plugin_output;
    }
    [[nodiscard]] int32_t current_attempt() const override {
        return service_.current_attempt;
    }
    [[nodiscard]] int32_t max_check_attempts() const override {
        return service_.max_attempts;
    }

    [[nodiscard]] int32_t current_state() const override {
        return service_.current_state;
    }
    [[nodiscard]] int32_t last_hard_state() const override {
        return service_.last_hard_state;
    }
    [[nodiscard]] bool has_been_checked() const override {
        return service_.has_been_checked != 0;
    }
    [[nodiscard]] bool problem_has_been_acknowledged() const override {
        return service_.problem_has_been_acknowledged != 0;
    }
    [[nodiscard]] int32_t scheduled_downtime_depth() const override {
        return service_.scheduled_downtime_depth;
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
    const NebHost host_;
};

#endif  // NebService_h
