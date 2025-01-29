// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebService_h
#define NebService_h

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <utility>
#include <vector>

#include "livestatus/Interface.h"
#include "neb/MacroExpander.h"
#include "neb/NebContact.h"
#include "neb/NebCore.h"
#include "neb/TimeperiodsCache.h"
#include "neb/nagios.h"

class NebService : public IService {
public:
    NebService(const ::service &svc, const NebCore &core)
        : service_{svc}, core_{core} {}

    [[nodiscard]] const ::service &handle() const { return service_; }

    [[nodiscard]] const void *handleForStateHistory() const override {
        return &service_;
    }

    [[nodiscard]] const IHost &host() const override;

    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-static-cast-downcast)
        const auto &ctc = static_cast<const NebContact &>(contact).handle();
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        auto *s = const_cast<::service *>(&service_);
        // Older Nagios headers are not const-correct... :-P
        // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
        auto *c = const_cast<::contact *>(static_cast<const ::contact *>(&ctc));
        return ::is_contact_for_service(s, c) != 0 ||
               ::is_escalated_contact_for_service(s, c) != 0;
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
    [[nodiscard]] std::string description() const override {
        return service_.description == nullptr ? "" : service_.description;
    }
    [[nodiscard]] std::string host_name() const override {
        return service_.host_name == nullptr ? "" : service_.host_name;
    }
    [[nodiscard]] std::string display_name() const override {
        return service_.display_name == nullptr ? "" : service_.display_name;
    }

    [[nodiscard]] std::string check_command() const override {
        auto *cc = nagios_compat_service_check_command(service_);
        return cc == nullptr ? "" : cc;
    }
    [[nodiscard]] std::string check_command_expanded() const override {
        return ServiceMacroExpander::make(service_)->expandMacros(
            nagios_compat_service_check_command(service_));
    }
    [[nodiscard]] std::filesystem::path robotmk_dir() const override {
        return std::filesystem::path{service_.host_ptr->name} /
               service_.description;
    }
    [[nodiscard]] std::string event_handler() const override {
        return service_.event_handler == nullptr ? "" : service_.event_handler;
    }
    [[nodiscard]] std::string plugin_output() const override {
        return service_.plugin_output == nullptr ? "" : service_.plugin_output;
    }
    [[nodiscard]] std::string long_plugin_output() const override {
        return service_.long_plugin_output == nullptr
                   ? ""
                   : service_.long_plugin_output;
    }
    [[nodiscard]] std::string perf_data() const override {
        return service_.perf_data == nullptr ? "" : service_.perf_data;
    }
    [[nodiscard]] std::string notificationPeriodName() const override {
        const auto *np = service_.notification_period;
        return np == nullptr ? "" : np;
    }
    [[nodiscard]] std::string check_period() const override {
        return service_.check_period == nullptr ? "" : service_.check_period;
    }
    [[nodiscard]] std::string notes() const override {
        return service_.notes == nullptr ? "" : service_.notes;
    }
    [[nodiscard]] std::string notes_expanded() const override {
        return ServiceMacroExpander::make(service_)->expandMacros(
            service_.notes);
    }
    [[nodiscard]] std::string notes_url() const override {
        return service_.notes_url == nullptr ? "" : service_.notes_url;
    }
    [[nodiscard]] std::string notes_url_expanded() const override {
        return ServiceMacroExpander::make(service_)->expandMacros(
            service_.notes_url);
    }
    [[nodiscard]] std::string action_url() const override {
        return service_.action_url == nullptr ? "" : service_.action_url;
    }
    [[nodiscard]] std::string action_url_expanded() const override {
        return ServiceMacroExpander::make(service_)->expandMacros(
            service_.action_url);
    }
    [[nodiscard]] std::string icon_image() const override {
        return service_.icon_image == nullptr ? "" : service_.icon_image;
    }
    [[nodiscard]] std::string icon_image_expanded() const override {
        return ServiceMacroExpander::make(service_)->expandMacros(
            service_.icon_image);
    }
    [[nodiscard]] std::string icon_image_alt() const override {
        return service_.icon_image_alt == nullptr ? ""
                                                  : service_.icon_image_alt;
    }
    [[nodiscard]] int32_t initial_state() const override {
        return service_.initial_state;
    }
    [[nodiscard]] int32_t max_check_attempts() const override {
        return service_.max_attempts;
    }
    [[nodiscard]] int32_t current_attempt() const override {
        return service_.current_attempt;
    }
    [[nodiscard]] int32_t current_state() const override {
        return service_.current_state;
    }
    [[nodiscard]] bool has_been_checked() const override {
        return service_.has_been_checked != 0;
    }
    [[nodiscard]] int32_t last_state() const override {
        return service_.last_state;
    }
    [[nodiscard]] int32_t last_hard_state() const override {
        return service_.last_hard_state;
    }
    [[nodiscard]] int32_t state_type() const override {
        return service_.state_type;
    }
    [[nodiscard]] int32_t check_type() const override {
        return service_.check_type;
    }
    [[nodiscard]] bool problem_has_been_acknowledged() const override {
        return service_.problem_has_been_acknowledged != 0;
    }
    [[nodiscard]] int32_t acknowledgement_type() const override {
        return service_.acknowledgement_type;
    }
    [[nodiscard]] bool no_more_notifications() const override {
        return service_.no_more_notifications != 0;
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_ok()
        const override {
        return std::chrono::system_clock::from_time_t(service_.last_time_ok);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_warning()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_time_warning);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_critical()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_time_critical);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_unknown()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_time_unknown);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_check()
        const override {
        return std::chrono::system_clock::from_time_t(service_.last_check);
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_check()
        const override {
        return std::chrono::system_clock::from_time_t(service_.next_check);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_notification()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_notification);
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_notification()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.next_notification);
    }
    [[nodiscard]] int32_t current_notification_number() const override {
        return service_.current_notification_number;
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_state_change()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_state_change);
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_hard_state_change()
        const override {
        return std::chrono::system_clock::from_time_t(
            service_.last_hard_state_change);
    }
    [[nodiscard]] int32_t scheduled_downtime_depth() const override {
        return service_.scheduled_downtime_depth;
    }
    [[nodiscard]] bool is_flapping() const override {
        return service_.is_flapping != 0;
    }
    [[nodiscard]] bool checks_enabled() const override {
        return service_.checks_enabled != 0;
    }
    [[nodiscard]] bool accept_passive_checks() const override {
        return nagios_compat_accept_passive_service_checks(service_) != 0;
    }
    [[nodiscard]] bool event_handler_enabled() const override {
        return service_.event_handler_enabled != 0;
    }
    [[nodiscard]] bool notifications_enabled() const override {
        return service_.notifications_enabled != 0;
    }
    [[nodiscard]] bool process_performance_data() const override {
        return service_.process_performance_data != 0;
    }
    [[nodiscard]] bool is_executing() const override {
        return service_.is_executing != 0;
    }
    [[nodiscard]] bool active_checks_enabled() const override {
        return service_.checks_enabled != 0;
    }
    [[nodiscard]] int32_t check_options() const override {
        return service_.check_options;
    }
    [[nodiscard]] bool flap_detection_enabled() const override {
        return service_.flap_detection_enabled != 0;
    }
    [[nodiscard]] bool check_freshness() const override {
        return service_.check_freshness != 0;
    }
    [[nodiscard]] bool obsess_over_service() const override {
        return nagios_compat_obsess_over_service(service_) != 0;
    }
    [[nodiscard]] uint32_t modified_attributes() const override {
        return service_.modified_attributes;
    }
    [[nodiscard]] int32_t hard_state() const override {
        if (service_.current_state == STATE_OK) {
            return 0;
        }
        return service_.state_type == HARD_STATE ? service_.current_state
                                                 : service_.last_hard_state;
    }
    [[nodiscard]] double staleness() const override {
        auto now = std::chrono::system_clock::to_time_t(
            std::chrono::system_clock::now());
        auto check_result_age = static_cast<double>(now - service_.last_check);
        if (service_.check_interval != 0) {
            return check_result_age /
                   (service_.check_interval * interval_length);
        }

        // check_mk PASSIVE CHECK without check interval uses the check
        // interval of its check-mk service
        auto is_cmk_passive = [](const ::service &svc) {
            return std::string_view{svc.check_command_ptr->name}.starts_with(
                "check_mk-");
        };
        if (is_cmk_passive(service_)) {
            const auto *host = service_.host_ptr;
            for (const auto *svc_member = host->services; svc_member != nullptr;
                 svc_member = svc_member->next) {
                const auto &tmp_svc = *svc_member->service_ptr;
                if (is_cmk_passive(tmp_svc)) {
                    auto safe_interval = tmp_svc.check_interval == 0
                                             ? 1
                                             : tmp_svc.check_interval;
                    return check_result_age / (safe_interval * interval_length);
                }
            }
            // Shouldn't happen! We always expect a check-mk service
            return 1;
        }
        // Other non-cmk passive and active checks without check_interval
        return check_result_age / interval_length;
    }
    [[nodiscard]] double check_interval() const override {
        return service_.check_interval;
    }
    [[nodiscard]] double retry_interval() const override {
        return service_.retry_interval;
    }
    [[nodiscard]] double notification_interval() const override {
        return service_.notification_interval;
    }
    [[nodiscard]] double first_notification_delay() const override {
        return service_.first_notification_delay;
    }
    [[nodiscard]] double low_flap_threshold() const override {
        return service_.low_flap_threshold;
    }
    [[nodiscard]] double high_flap_threshold() const override {
        return service_.high_flap_threshold;
    }
    [[nodiscard]] double latency() const override { return service_.latency; }
    [[nodiscard]] double execution_time() const override {
        return service_.execution_time;
    }
    [[nodiscard]] double percent_state_change() const override {
        return service_.percent_state_change;
    }
    [[nodiscard]] bool in_check_period() const override {
        return g_timeperiods_cache->inTimeperiod(service_.check_period_ptr);
    }
    [[nodiscard]] bool in_service_period() const override {
        if (auto tpname = findCustomAttributeValue(
                service_.custom_variables, AttributeKind::custom_variables,
                "SERVICE_PERIOD")) {
            return g_timeperiods_cache->inTimeperiod(*tpname);
        }
        return true;  // assume 24X7
    }
    [[nodiscard]] bool in_notification_period() const override {
        return g_timeperiods_cache->inTimeperiod(notificationPeriodName());
    }
    [[nodiscard]] std::vector<std::string> contacts() const override {
        std::unordered_set<std::string> names;
        for (auto *cm = service_.contacts; cm != nullptr; cm = cm->next) {
            names.insert(cm->contact_ptr->name);
        }
        for (auto *cgm = service_.contact_groups; cgm != nullptr;
             cgm = cgm->next) {
            for (auto *cm = cgm->group_ptr->members; cm != nullptr;
                 cm = cm->next) {
                names.insert(cm->contact_ptr->name);
            }
        }
        return {names.begin(), names.end()};
    }
    [[nodiscard]] Attributes attributes(AttributeKind kind) const override {
        return CustomAttributes(service_.custom_variables, kind);
    }

    bool all_of_service_groups(
        std::function<bool(const IServiceGroup &)> pred) const override;
    bool all_of_contact_groups(
        std::function<bool(const IContactGroup &)> pred) const override;

    [[nodiscard]] std::chrono::system_clock::time_point cached_at()
        const override {
        return {};
    }
    [[nodiscard]] int32_t cache_interval() const override { return 0; }
    [[nodiscard]] bool in_passive_check_period() const override { return true; }
    [[nodiscard]] std::string passive_check_period() const override {
        return "24x7";
    }
    [[nodiscard]] double flappiness() const override {
        return service_.percent_state_change;
    }
    [[nodiscard]] std::string notification_postponement_reason()
        const override {
        return "";
    }
    [[nodiscard]] int32_t previous_hard_state() const override { return -1; }
    [[nodiscard]] int32_t pending_flex_downtime() const override {
        return service_.pending_flex_downtime;
    }
    [[nodiscard]] bool check_flapping_recovery_notification() const override {
        return service_.check_flapping_recovery_notification != 0;
    }
    bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const override {
        // TODO(sp) Avoid construction of temporary map
        auto labels =
            CustomAttributes(service_.custom_variables, AttributeKind::labels);
        return std::ranges::all_of(
            labels, [&pred](const std::pair<std::string, std::string> &label) {
                return pred(
                    Attribute{.name = label.first, .value = label.second});
            });
    }

private:
    const ::service &service_;
    const NebCore &core_;
};

#endif  // NebService_h
