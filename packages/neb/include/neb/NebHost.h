// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHost_h
#define NebHost_h

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <unordered_set>
#include <vector>

#include "livestatus/Interface.h"
#include "neb/MacroExpander.h"
#include "neb/NebContact.h"
#include "neb/NebCore.h"
#include "neb/TimeperiodsCache.h"
#include "neb/nagios.h"

class NebHost : public IHost {
public:
    NebHost(const ::host &host, const NebCore &core)
        : host_{host}, core_{core} {}

    [[nodiscard]] const ::host &handle() const { return host_; }

    [[nodiscard]] const void *handleForStateHistory() const override {
        return &host_;
    }

    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
        const auto &ctc = static_cast<const NebContact &>(contact).handle();
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        auto *h = const_cast<::host *>(&host_);
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        auto *c = const_cast<::contact *>(&ctc);
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

    [[nodiscard]] std::string name() const override {
        return host_.name == nullptr ? "" : host_.name;
    }
    [[nodiscard]] std::string display_name() const override {
        return host_.display_name == nullptr ? "" : host_.display_name;
    }
    [[nodiscard]] std::string alias() const override {
        return host_.alias == nullptr ? "" : host_.alias;
    }
    [[nodiscard]] std::string ip_address() const override {
        return host_.address == nullptr ? "" : host_.address;
    }
    [[nodiscard]] std::string check_command() const override {
        const auto *cc = nagios_compat_host_check_command(host_);
        return cc == nullptr ? "" : cc;
    }
    [[nodiscard]] std::string check_command_expanded() const override {
        return HostMacroExpander::make(host_)->expandMacros(
            nagios_compat_host_check_command(host_));
    }
    [[nodiscard]] std::string event_handler() const override {
        return host_.event_handler == nullptr ? "" : host_.event_handler;
    }
    [[nodiscard]] std::string notification_period() const override {
        return host_.notification_period == nullptr ? ""
                                                    : host_.notification_period;
    }
    [[nodiscard]] std::string check_period() const override {
        return host_.check_period == nullptr ? "" : host_.check_period;
    }
    [[nodiscard]] std::string notes() const override {
        return host_.notes == nullptr ? "" : host_.notes;
    }
    [[nodiscard]] std::string notes_expanded() const override {
        return HostMacroExpander::make(host_)->expandMacros(host_.notes);
    }
    [[nodiscard]] std::string notes_url() const override {
        return host_.notes_url == nullptr ? "" : host_.notes_url;
    }
    [[nodiscard]] std::string notes_url_expanded() const override {
        return HostMacroExpander::make(host_)->expandMacros(host_.notes_url);
    }
    [[nodiscard]] std::string action_url() const override {
        return host_.action_url == nullptr ? "" : host_.action_url;
    }
    [[nodiscard]] std::string action_url_expanded() const override {
        return HostMacroExpander::make(host_)->expandMacros(host_.action_url);
    }
    [[nodiscard]] std::string plugin_output() const override {
        return host_.plugin_output == nullptr ? "" : host_.plugin_output;
    }
    [[nodiscard]] std::string perf_data() const override {
        return host_.perf_data == nullptr ? "" : host_.perf_data;
    }
    [[nodiscard]] std::string icon_image() const override {
        return host_.icon_image == nullptr ? "" : host_.icon_image;
    }
    [[nodiscard]] std::string icon_image_expanded() const override {
        return HostMacroExpander::make(host_)->expandMacros(host_.icon_image);
    }
    [[nodiscard]] std::string icon_image_alt() const override {
        return host_.icon_image_alt == nullptr ? "" : host_.icon_image_alt;
    }
    [[nodiscard]] std::string status_map_image() const override {
        return host_.statusmap_image == nullptr ? "" : host_.statusmap_image;
    }
    [[nodiscard]] std::string long_plugin_output() const override {
        return host_.long_plugin_output == nullptr ? ""
                                                   : host_.long_plugin_output;
    }
    [[nodiscard]] int32_t initial_state() const override {
        return host_.initial_state;
    }
    [[nodiscard]] int32_t max_check_attempts() const override {
        return host_.max_attempts;
    }
    [[nodiscard]] bool flap_detection_enabled() const override {
        return host_.flap_detection_enabled != 0;
    }
    [[nodiscard]] bool check_freshness() const override {
        return host_.check_freshness != 0;
    }
    [[nodiscard]] bool process_performance_data() const override {
        return host_.process_performance_data != 0;
    }
    [[nodiscard]] bool accept_passive_host_checks() const override {
        return nagios_compat_accept_passive_host_checks(host_) != 0;
    }
    [[nodiscard]] int32_t event_handler_enabled() const override {
        return host_.event_handler_enabled;
    }
    [[nodiscard]] int32_t acknowledgement_type() const override {
        return host_.acknowledgement_type;
    }
    [[nodiscard]] int32_t check_type() const override {
        return host_.check_type;
    }
    [[nodiscard]] int32_t last_state() const override {
        return host_.last_state;
    }
    [[nodiscard]] int32_t last_hard_state() const override {
        return host_.last_hard_state;
    }
    [[nodiscard]] int32_t current_attempt() const override {
        return host_.current_attempt;
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_notification()
        const override {
        return std::chrono::system_clock::from_time_t(
            nagios_compat_last_host_notification(host_));
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_notification()
        const override {
        return std::chrono::system_clock::from_time_t(
            nagios_compat_next_host_notification(host_));
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_check()
        const override {
        return std::chrono::system_clock::from_time_t(host_.next_check);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_hard_state_change()
        const override {
        return std::chrono::system_clock::from_time_t(
            host_.last_hard_state_change);
    }
    [[nodiscard]] bool has_been_checked() const override {
        return host_.has_been_checked != 0;
    }
    [[nodiscard]] int32_t current_notification_number() const override {
        return host_.current_notification_number;
    }
    [[nodiscard]] int32_t pending_flex_downtime() const override {
        return host_.pending_flex_downtime;
    }
    [[nodiscard]] int32_t total_services() const override {
        return host_.total_services;
    }
    [[nodiscard]] bool notifications_enabled() const override {
        return host_.notifications_enabled != 0;
    }
    [[nodiscard]] bool problem_has_been_acknowledged() const override {
        return host_.problem_has_been_acknowledged != 0;
    }
    [[nodiscard]] int32_t current_state() const override {
        return host_.current_state;
    }
    [[nodiscard]] int32_t hard_state() const override {
        if (current_state() == HOST_UP) {
            return 0;
        }
        return state_type() == HARD_STATE ? current_state() : last_hard_state();
    }
    [[nodiscard]] int32_t state_type() const override {
        return host_.state_type;
    }
    [[nodiscard]] int32_t no_more_notifications() const override {
        return host_.no_more_notifications;
    }
    [[nodiscard]] int32_t check_flapping_recovery_notification()
        const override {
        return host_.check_flapping_recovery_notification;
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_check()
        const override {
        return std::chrono::system_clock::from_time_t(host_.last_check);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_state_change()
        const override {
        return std::chrono::system_clock::from_time_t(host_.last_state_change);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_up()
        const override {
        return std::chrono::system_clock::from_time_t(host_.last_time_up);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_down()
        const override {
        return std::chrono::system_clock::from_time_t(host_.last_time_down);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_unreachable()
        const override {
        return std::chrono::system_clock::from_time_t(
            host_.last_time_unreachable);
    }

    [[nodiscard]] bool is_flapping() const override {
        return host_.is_flapping != 0;
    }
    [[nodiscard]] int32_t scheduled_downtime_depth() const override {
        return host_.scheduled_downtime_depth;
    }
    [[nodiscard]] bool is_executing() const override {
        return host_.is_executing != 0;
    }
    [[nodiscard]] bool active_checks_enabled() const override {
        return host_.checks_enabled != 0;
    }
    [[nodiscard]] int32_t check_options() const override {
        return host_.check_options;
    }
    [[nodiscard]] int32_t obsess_over_host() const override {
        return nagios_compat_obsess_over_host(host_);
    }
    [[nodiscard]] uint32_t modified_attributes() const override {
        return host_.modified_attributes;
    }
    [[nodiscard]] double check_interval() const override {
        return host_.check_interval;
    }
    [[nodiscard]] double retry_interval() const override {
        return host_.retry_interval;
    }
    [[nodiscard]] double notification_interval() const override {
        return host_.notification_interval;
    }
    [[nodiscard]] double first_notification_delay() const override {
        return host_.first_notification_delay;
    }
    [[nodiscard]] double low_flap_threshold() const override {
        return host_.low_flap_threshold;
    }
    [[nodiscard]] double high_flap_threshold() const override {
        return host_.high_flap_threshold;
    }
    [[nodiscard]] double x_3d() const override { return host_.x_3d; }
    [[nodiscard]] double y_3d() const override { return host_.y_3d; }
    [[nodiscard]] double z_3d() const override { return host_.z_3d; }
    [[nodiscard]] double latency() const override { return host_.latency; }
    [[nodiscard]] double execution_time() const override {
        return host_.execution_time;
    }
    [[nodiscard]] double percent_state_change() const override {
        return host_.percent_state_change;
    }
    [[nodiscard]] double staleness() const override {
        auto now = std::chrono::system_clock::to_time_t(
            std::chrono::system_clock::now());
        return static_cast<double>(
                   now - std::chrono::system_clock::to_time_t(last_check())) /
               ((check_interval() == 0 ? 1 : check_interval()) *
                interval_length);
    }
    [[nodiscard]] double flappiness() const override {
        return percent_state_change();
    }
    [[nodiscard]] bool in_notification_period() const override {
        return g_timeperiods_cache->inTimeperiod(host_.notification_period_ptr);
    }
    [[nodiscard]] bool in_check_period() const override {
        return g_timeperiods_cache->inTimeperiod(host_.check_period_ptr);
    }
    [[nodiscard]] bool in_service_period() const override {
        const auto tp = servicePeriodName();
        // for empty assume 24X7;
        return tp.empty() || g_timeperiods_cache->inTimeperiod(tp);
    }
    [[nodiscard]] std::vector<std::string> contacts() const override {
        std::unordered_set<std::string> names;
        for (auto *cm = host_.contacts; cm != nullptr; cm = cm->next) {
            names.insert(cm->contact_ptr->name);
        }
        for (auto *cgm = host_.contact_groups; cgm != nullptr;
             cgm = cgm->next) {
            for (auto *cm = cgm->group_ptr->members; cm != nullptr;
                 cm = cm->next) {
                names.insert(cm->contact_ptr->name);
            }
        }
        return {names.begin(), names.end()};
    }

    [[nodiscard]] Attributes attributes(AttributeKind kind) const override {
        return CustomAttributes(host_.custom_variables, kind);
    }

    [[nodiscard]] std::string filename() const override {
        return findCustomAttributeValue(host_.custom_variables,
                                        AttributeKind::custom_variables,
                                        "FILENAME")
            .value_or(std::string{});
        ;
    }
    [[nodiscard]] std::string notification_postponement_reason()
        const override {
        return {};
    }
    [[nodiscard]] int32_t previous_hard_state() const override { return -1; }
    [[nodiscard]] int32_t smartping_timeout() const override {
        // Let's pretend the default. Or should we simply use 0?
        return static_cast<int32_t>(check_interval() * 60000 * 2.5);
    }

    bool all_of_parents(std::function<bool(const IHost &)> pred) const override;
    bool all_of_children(
        std::function<bool(const IHost &)> pred) const override;
    bool all_of_host_groups(
        std::function<bool(const IHostGroup &)> pred) const override;
    bool all_of_contact_groups(
        std::function<bool(const IContactGroup &)> pred) const override;

    bool all_of_services(
        std::function<bool(const IService &)> pred) const override;

    bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const override;

private:
    const ::host &host_;
    const NebCore &core_;
};

#endif  // NebHost_h
