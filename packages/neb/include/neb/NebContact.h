// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContact_h
#define NebContact_h

#include <ranges>

#include "livestatus/Interface.h"
#include "neb/NebCore.h"
#include "neb/TimeperiodsCache.h"
#include "neb/nagios.h"

class NebContact : public IContact {
public:
    explicit NebContact(const ::contact &contact) : contact_{contact} {}

    [[nodiscard]] const ::contact &handle() const { return contact_; };

    [[nodiscard]] std::string name() const override {
        return contact_.name == nullptr ? "" : contact_.name;
    }
    [[nodiscard]] std::string alias() const override {
        return contact_.alias == nullptr ? "" : contact_.alias;
    }
    [[nodiscard]] std::string email() const override {
        return contact_.email == nullptr ? "" : contact_.email;
    }
    [[nodiscard]] std::string pager() const override {
        return contact_.pager == nullptr ? "" : contact_.pager;
    }
    [[nodiscard]] std::string hostNotificationPeriod() const override {
        return contact_.host_notification_period == nullptr
                   ? ""
                   : contact_.host_notification_period;
    }
    [[nodiscard]] std::string serviceNotificationPeriod() const override {
        return contact_.service_notification_period == nullptr
                   ? ""
                   : contact_.service_notification_period;
    }
    [[nodiscard]] std::string address(int32_t index) const override {
        // NOLINTBEGIN(cppcoreguidelines-pro-bounds-constant-array-index)
        return contact_.address[index] == nullptr ? ""
                                                  : contact_.address[index];
        // NOLINTEND(cppcoreguidelines-pro-bounds-constant-array-index)
    }
    [[nodiscard]] bool canSubmitCommands() const override {
        return contact_.can_submit_commands != 0;
    }
    [[nodiscard]] bool isHostNotificationsEnabled() const override {
        return contact_.host_notifications_enabled != 0;
    }
    [[nodiscard]] bool isServiceNotificationsEnabled() const override {
        return contact_.service_notifications_enabled != 0;
    }
    [[nodiscard]] bool isInHostNotificationPeriod() const override {
        return g_timeperiods_cache->inTimeperiod(
            contact_.host_notification_period_ptr);
    }
    [[nodiscard]] bool isInServiceNotificationPeriod() const override {
        return g_timeperiods_cache->inTimeperiod(
            contact_.service_notification_period_ptr);
    }
    [[nodiscard]] Attributes customVariables() const override {
        return CustomAttributes(contact_.custom_variables,
                                AttributeKind::custom_variables);
    }
    [[nodiscard]] Attributes tags() const override {
        return CustomAttributes(contact_.custom_variables, AttributeKind::tags);
    }
    [[nodiscard]] Attributes labels() const override {
        return CustomAttributes(contact_.custom_variables,
                                AttributeKind::labels);
    }
    [[nodiscard]] Attributes labelSources() const override {
        return CustomAttributes(contact_.custom_variables,
                                AttributeKind::label_sources);
    }

    [[nodiscard]] uint32_t modifiedAttributes() const override {
        return contact_.modified_attributes;
    }

    bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const override {
        // TODO(sp) Avoid construction of temporary map
        auto labels =
            CustomAttributes(contact_.custom_variables, AttributeKind::labels);
        return std::ranges::all_of(
            labels, [&pred](const std::pair<std::string, std::string> &label) {
                return pred(
                    Attribute{.name = label.first, .value = label.second});
            });
    }

private:
    const ::contact &contact_;
};

#endif  // NebContact_h
