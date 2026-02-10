// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <cstdint>
#include <functional>
#include <string>
#include <unordered_set>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Interface.h"
#include "livestatus/User.h"

namespace {

class StubHost : public IHost {
public:
    explicit StubHost(std::unordered_set<const IContact *> contacts)
        : contacts_{std::move(contacts)} {}
    [[nodiscard]] const void *handleForStateHistory() const override {
        return nullptr;
    }
    [[nodiscard]] bool hasContact(const IContact &contact) const override {
        return contacts_.contains(&contact);
    }
    [[nodiscard]] std::string notificationPeriodName() const override {
        return {};
    }
    [[nodiscard]] std::string servicePeriodName() const override { return {}; }
    [[nodiscard]] std::string name() const override { return {}; }
    [[nodiscard]] std::string display_name() const override { return {}; }
    [[nodiscard]] std::string alias() const override { return {}; }
    [[nodiscard]] std::string ip_address() const override { return {}; }
    [[nodiscard]] std::string check_command() const override { return {}; }
    [[nodiscard]] std::string check_command_expanded() const override {
        return {};
    }
    [[nodiscard]] std::string event_handler() const override { return {}; }
    [[nodiscard]] std::string notification_period() const override {
        return {};
    }
    [[nodiscard]] std::string check_period() const override { return {}; }
    [[nodiscard]] std::string notes() const override { return {}; }
    [[nodiscard]] std::string notes_expanded() const override { return {}; }
    [[nodiscard]] std::string notes_url() const override { return {}; }
    [[nodiscard]] std::string notes_url_expanded() const override { return {}; }
    [[nodiscard]] std::string action_url() const override { return {}; }
    [[nodiscard]] std::string action_url_expanded() const override {
        return {};
    }
    [[nodiscard]] std::string plugin_output() const override { return {}; }
    [[nodiscard]] std::string perf_data() const override { return {}; }
    [[nodiscard]] std::string icon_image() const override { return {}; }
    [[nodiscard]] std::string icon_image_expanded() const override {
        return {};
    }
    [[nodiscard]] std::string icon_image_alt() const override { return {}; }
    [[nodiscard]] std::string status_map_image() const override { return {}; }
    [[nodiscard]] std::string long_plugin_output() const override { return {}; }
    [[nodiscard]] int32_t initial_state() const override { return 0; }
    [[nodiscard]] int32_t max_check_attempts() const override { return 0; }
    [[nodiscard]] bool flap_detection_enabled() const override { return false; }
    [[nodiscard]] bool check_freshness() const override { return false; }
    [[nodiscard]] bool process_performance_data() const override {
        return false;
    }
    [[nodiscard]] bool accept_passive_host_checks() const override {
        return false;
    }
    [[nodiscard]] int32_t event_handler_enabled() const override { return 0; }
    [[nodiscard]] int32_t acknowledgement_type() const override { return 0; }
    [[nodiscard]] int32_t check_type() const override { return 0; }
    [[nodiscard]] int32_t last_state() const override { return 0; }
    [[nodiscard]] int32_t last_hard_state() const override { return 0; }
    [[nodiscard]] int32_t current_attempt() const override { return 0; }
    [[nodiscard]] std::chrono::system_clock::time_point last_notification()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_notification()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point next_check()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_hard_state_change()
        const override {
        return {};
    }
    [[nodiscard]] bool has_been_checked() const override { return false; }
    [[nodiscard]] int32_t current_notification_number() const override {
        return 0;
    }
    [[nodiscard]] int32_t pending_flex_downtime() const override { return 0; }
    [[nodiscard]] int32_t total_services() const override { return 0; }
    [[nodiscard]] bool notifications_enabled() const override { return false; }
    [[nodiscard]] bool problem_has_been_acknowledged() const override {
        return false;
    }
    [[nodiscard]] int32_t current_state() const override { return 0; }
    [[nodiscard]] int32_t hard_state() const override { return 0; }
    [[nodiscard]] int32_t state_type() const override { return 0; }
    [[nodiscard]] int32_t no_more_notifications() const override { return 0; }
    [[nodiscard]] int32_t check_flapping_recovery_notification()
        const override {
        return 0;
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_check()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_state_change()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_up()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_down()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_time_unreachable()
        const override {
        return {};
    }
    [[nodiscard]] bool is_flapping() const override { return false; }
    [[nodiscard]] int32_t scheduled_downtime_depth() const override {
        return 0;
    }
    [[nodiscard]] bool is_executing() const override { return false; }
    [[nodiscard]] bool active_checks_enabled() const override { return false; }
    [[nodiscard]] int32_t check_options() const override { return 0; }
    [[nodiscard]] int32_t obsess_over_host() const override { return 0; }
    [[nodiscard]] uint32_t modified_attributes() const override { return 0; }
    [[nodiscard]] double check_interval() const override { return 0.0; }
    [[nodiscard]] double retry_interval() const override { return 0.0; }
    [[nodiscard]] double notification_interval() const override { return 0.0; }
    [[nodiscard]] double first_notification_delay() const override {
        return 0.0;
    }
    [[nodiscard]] double low_flap_threshold() const override { return 0.0; }
    [[nodiscard]] double high_flap_threshold() const override { return 0.0; }
    [[nodiscard]] double x_3d() const override { return 0.0; }
    [[nodiscard]] double y_3d() const override { return 0.0; }
    [[nodiscard]] double z_3d() const override { return 0.0; }
    [[nodiscard]] double latency() const override { return 0.0; }
    [[nodiscard]] double execution_time() const override { return 0.0; }
    [[nodiscard]] double percent_state_change() const override { return 0.0; }
    [[nodiscard]] double staleness() const override { return 0.0; }
    [[nodiscard]] double flappiness() const override { return 0.0; }
    [[nodiscard]] bool in_notification_period() const override { return false; }
    [[nodiscard]] bool in_check_period() const override { return false; }
    [[nodiscard]] bool in_service_period() const override { return false; }
    [[nodiscard]] std::vector<std::string> contacts() const override {
        return {};
    }
    [[nodiscard]] Attributes attributes(AttributeKind /*kind*/) const override {
        return {};
    }
    [[nodiscard]] std::string filename() const override { return {}; }
    [[nodiscard]] std::string notification_postponement_reason()
        const override {
        return {};
    }
    [[nodiscard]] int32_t previous_hard_state() const override { return 0; }
    [[nodiscard]] int32_t smartping_timeout() const override { return 0; }
    bool all_of_services(
        std::function<bool(const IService &)> /*pred*/) const override {
        return true;
    }
    bool all_of_labels(
        const std::function<bool(const Label &)> & /*pred*/) const override {
        return true;
    }
    bool all_of_parents(
        std::function<bool(const IHost &)> /*pred*/) const override {
        return true;
    }
    bool all_of_children(
        std::function<bool(const IHost &)> /*pred*/) const override {
        return true;
    }
    bool all_of_host_groups(
        std::function<bool(const IHostGroup &)> /*pred*/) const override {
        return true;
    }
    bool all_of_contact_groups(
        std::function<bool(const IContactGroup &)> /*pred*/) const override {
        return true;
    }

private:
    std::unordered_set<const IContact *> contacts_;
};

class StubContact : public IContact {
public:
    explicit StubContact(std::string name) : name_{std::move(name)} {}
    [[nodiscard]] std::string name() const override { return name_; }
    [[nodiscard]] std::string alias() const override { return {}; }
    [[nodiscard]] std::string email() const override { return {}; }
    [[nodiscard]] std::string pager() const override { return {}; }
    [[nodiscard]] std::string hostNotificationPeriod() const override {
        return {};
    }
    [[nodiscard]] std::string serviceNotificationPeriod() const override {
        return {};
    }
    [[nodiscard]] std::string address(int32_t /*index*/) const override {
        return {};
    }
    [[nodiscard]] bool canSubmitCommands() const override { return false; }
    [[nodiscard]] bool isHostNotificationsEnabled() const override {
        return false;
    }
    [[nodiscard]] bool isServiceNotificationsEnabled() const override {
        return false;
    }
    [[nodiscard]] bool isInHostNotificationPeriod() const override {
        return false;
    }
    [[nodiscard]] bool isInServiceNotificationPeriod() const override {
        return false;
    }
    [[nodiscard]] Attributes customVariables() const override { return {}; }
    [[nodiscard]] Attributes labels() const override { return {}; }
    [[nodiscard]] Attributes labelSources() const override { return {}; }
    [[nodiscard]] Attributes tags() const override { return {}; }
    [[nodiscard]] uint32_t modifiedAttributes() const override { return 0; }
    bool all_of_labels(
        const std::function<bool(const Label &)> & /*pred*/) const override {
        return true;
    }

private:
    std::string name_;
};
}  // namespace

TEST(UserTest, AuthUserMatchingContactName) {
    StubContact contact{"King Kong"};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_contact_name("King Kong"));
}

TEST(UserTest, AuthUserNonMatchingContactName) {
    StubContact contact{"King Kong"};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    EXPECT_FALSE(user.is_authorized_for_contact_name("donald"));
}

TEST(UserTest, AuthUserEmptyContactName) {
    StubContact contact{"King Kong"};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    EXPECT_FALSE(user.is_authorized_for_contact_name(""));
}

TEST(UserTest, NoAuthUserAlwaysAuthorized) {
    NoAuthUser user;
    EXPECT_TRUE(user.is_authorized_for_contact_name("anyone"));
    EXPECT_TRUE(user.is_authorized_for_contact_name(""));
}

TEST(UserTest, UnknownUserNeverAuthorized) {
    UnknownUser user;
    EXPECT_FALSE(user.is_authorized_for_contact_name("anyone"));
    EXPECT_FALSE(user.is_authorized_for_contact_name(""));
}

// Tests for is_authorized_for_notification_object:
// Covers remote-site forwarded notifications where the host or service may not
// exist locally.

TEST(UserTest, NotificationObjectHostMissingAuthorizedByContactName) {
    // Host not found (null): fall back to contact name matching.
    StubContact contact{"King Kong"};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        nullptr, nullptr, /*is_service_notification=*/false, "King Kong"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        nullptr, nullptr, /*is_service_notification=*/false, "donald"));
}

TEST(UserTest,
     NotificationObjectHostKnownServiceMissingAuthorizedByContactName) {
    // Host exists but service not found: fall back to contact name matching for
    // service notifications. This handles the case where a service existed in
    // the past or only exists on a remote site.
    StubContact contact{"King Kong"};
    StubHost host{{}};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        &host, nullptr, /*is_service_notification=*/true, "King Kong"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        &host, nullptr, /*is_service_notification=*/true, "donald"));
}

TEST(UserTest, NotificationObjectHostKnownNoServiceDescriptionUsesHostContact) {
    // Host exists, no service description (host notification): delegate to
    // host contact check, not contact name fallback.
    StubContact contact{"King Kong"};
    StubHost host_with_contact{{&contact}};
    StubHost host_without_contact{{}};
    AuthUser user{contact, ServiceAuthorization::loose,
                  GroupAuthorization::loose,
                  [](const std::string &) { return nullptr; }};
    // contact_name does NOT matter here — authorization is via hasContact()
    EXPECT_TRUE(user.is_authorized_for_notification_object(
        &host_with_contact, nullptr, /*is_service_notification=*/false,
        "donald"));
    EXPECT_FALSE(user.is_authorized_for_notification_object(
        &host_without_contact, nullptr, /*is_service_notification=*/false,
        "King Kong"));
}
