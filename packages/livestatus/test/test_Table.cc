// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <initializer_list>
#include <iterator>
#include <memory>
#include <ostream>
#include <string>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logger.h"
#include "livestatus/Metric.h"
#include "livestatus/Table.h"
#include "livestatus/TableColumns.h"
#include "livestatus/TableCommands.h"
#include "livestatus/TableComments.h"
#include "livestatus/TableContactGroups.h"
#include "livestatus/TableContacts.h"
#include "livestatus/TableCrashReports.h"
#include "livestatus/TableDowntimes.h"
#include "livestatus/TableEventConsoleEvents.h"
#include "livestatus/TableEventConsoleHistory.h"
#include "livestatus/TableEventConsoleRules.h"
#include "livestatus/TableEventConsoleStatus.h"
#include "livestatus/TableHostGroups.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TableHostsByGroup.h"
#include "livestatus/TableLabels.h"
#include "livestatus/TableLog.h"
#include "livestatus/TableServiceGroups.h"
#include "livestatus/TableServices.h"
#include "livestatus/TableServicesByGroup.h"
#include "livestatus/TableServicesByHostGroup.h"
#include "livestatus/TableStateHistory.h"
#include "livestatus/TableStatus.h"
#include "livestatus/TableTimeperiods.h"
#include "livestatus/Triggers.h"

class DummyMonitoringCore : public ICore {
    [[nodiscard]] const IHost *find_host(
        const std::string & /*name*/) const override {
        return nullptr;
    }
    [[nodiscard]] const IHostGroup *find_hostgroup(
        const std::string & /* name */) const override {
        return nullptr;
    }
    [[nodiscard]] const IHost *getHostByDesignation(
        const std::string & /*designation*/) const override {
        return {};
    }
    bool all_of_hosts(
        const std::function<bool(const IHost &)> & /*pred*/) const override {
        return true;
    }
    bool all_of_services(
        const std::function<bool(const IService &)> & /*pred*/) const override {
        return true;
    }
    [[nodiscard]] const IService *find_service(
        const std::string & /*host_name*/,
        const std::string & /*service_description*/) const override {
        return {};
    }
    [[nodiscard]] const IContactGroup *find_contactgroup(
        const std::string & /*name*/) const override {
        return {};
    }

    [[nodiscard]] const IServiceGroup *find_servicegroup(
        const std::string & /*name*/) const override {
        return nullptr;
    }

    [[nodiscard]] const IContact *find_contact(
        const std::string & /*name*/) const override {
        return {};
    }
    bool all_of_contacts(
        const std::function<bool(const IContact &)> & /*pred*/) const override {
        return true;
    }
    [[nodiscard]] std::unique_ptr<const User> find_user(
        const std::string & /*name*/) const override {
        return {};
    }

    [[nodiscard]] std::chrono::system_clock::time_point last_logfile_rotation()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point last_config_change()
        const override {
        return {};
    }
    [[nodiscard]] size_t maxLinesPerLogFile() const override { return {}; }

    [[nodiscard]] Command find_command(
        const std::string & /*name*/) const override {
        return {};
    }
    [[nodiscard]] std::vector<Command> commands() const override { return {}; }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IService & /*service*/) const override {
        return {};
    }
    [[nodiscard]] std::vector<std::unique_ptr<const IComment>> comments(
        const IService & /*service*/) const override {
        return {};
    }

    bool all_of_comments(
        const std::function<bool(const IComment &)> & /*pred*/) const override {
        return true;
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IHost & /*host*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IService & /*service*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::unique_ptr<const IDowntime>> downtimes(
        const IService & /*service*/) const override {
        return {};
    }

    bool all_of_downtimes(const std::function<bool(const IDowntime &)>
                              & /*pred*/) const override {
        return true;
    }

    bool all_of_timeperiods(const std::function<bool(const ITimeperiod &)>
                                & /*pred*/) const override {
        return true;
    }

    bool all_of_contact_groups(const std::function<bool(const IContactGroup &)>
                                   & /* f */) const override {
        return {};
    }

    bool all_of_host_groups(const std::function<bool(const IHostGroup &)>
                                & /* f */) const override {
        return {};
    }

    bool all_of_service_groups(const std::function<bool(const IServiceGroup &)>
                                   & /* f */) const override {
        return {};
    }

    [[nodiscard]] bool mkeventdEnabled() const override { return {}; }

    [[nodiscard]] std::unique_ptr<const IPaths> paths() const override {
        return {};
    }
    [[nodiscard]] int32_t pid() const override { return {}; }
    [[nodiscard]] std::unique_ptr<const IGlobalFlags> globalFlags()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point programStartTime()
        const override {
        return {};
    }
    [[nodiscard]] std::chrono::system_clock::time_point lastCommandCheckTime()
        const override {
        return {};
    }
    [[nodiscard]] int32_t intervalLength() const override { return {}; }
    [[nodiscard]] int32_t maxLongOutputSize() const override { return {}; }
    [[nodiscard]] int32_t numHosts() const override { return {}; }
    [[nodiscard]] int32_t numServices() const override { return {}; }
    [[nodiscard]] std::string programVersion() const override { return {}; }
    [[nodiscard]] std::string edition() const override { return {}; }

    [[nodiscard]] int32_t externalCommandBufferSlots() const override {
        return {};
    }
    [[nodiscard]] int32_t externalCommandBufferUsage() const override {
        return {};
    }
    [[nodiscard]] int32_t externalCommandBufferMax() const override {
        return {};
    }

    [[nodiscard]] int32_t livestatusActiveConnectionsNum() const override {
        return {};
    }
    [[nodiscard]] std::string livestatusVersion() const override { return {}; }
    [[nodiscard]] int32_t livestatusQueuedConnectionsNum() const override {
        return {};
    }
    [[nodiscard]] int32_t livestatusThreadsNum() const override { return {}; }
    [[nodiscard]] double livestatusUsage() const override { return {}; }

    [[nodiscard]] double averageLatencyGeneric() const override { return {}; }
    [[nodiscard]] double averageLatencyChecker() const override { return {}; }
    [[nodiscard]] double averageLatencyFetcher() const override { return {}; }
    [[nodiscard]] double averageLatencyRealTime() const override { return {}; }

    [[nodiscard]] double helperUsageGeneric() const override { return {}; }
    [[nodiscard]] double helperUsageChecker() const override { return {}; }
    [[nodiscard]] double helperUsageFetcher() const override { return {}; }
    [[nodiscard]] double helperUsageRealTime() const override { return {}; }

    [[nodiscard]] bool hasEventHandlers() const override { return {}; }

    [[nodiscard]] double averageRunnableJobsFetcher() const override {
        return {};
    }
    [[nodiscard]] double averageRunnableJobsChecker() const override {
        return {};
    }

    [[nodiscard]] std::chrono::system_clock::time_point stateFileCreatedTime()
        const override {
        return {};
    }

    [[nodiscard]] std::vector<std::string> metrics(
        const IHost & /*h*/) const override {
        return {};
    }

    [[nodiscard]] std::vector<std::string> metrics(
        const IService & /*s*/) const override {
        return {};
    }

    [[nodiscard]] bool isPnpGraphPresent(const IHost & /* h */) const override {
        return {};
    }

    [[nodiscard]] bool isPnpGraphPresent(
        const IService & /* s */) const override {
        return {};
    }

    [[nodiscard]] Encoding dataEncoding() const override { return {}; }
    [[nodiscard]] size_t maxResponseSize() const override { return {}; }
    [[nodiscard]] size_t maxCachedMessages() const override { return {}; }

    [[nodiscard]] Logger *loggerCore() const override {
        return Logger::getLogger("test");
    }
    [[nodiscard]] Logger *loggerLivestatus() const override { return {}; }
    [[nodiscard]] Logger *loggerRRD() const override { return {}; }

    Triggers &triggers() override { return triggers_; }

    [[nodiscard]] size_t numQueuedNotifications() const override { return {}; }
    [[nodiscard]] size_t numQueuedAlerts() const override { return {}; }
    [[nodiscard]] size_t numCachedLogMessages() override { return {}; }

    [[nodiscard]] MetricLocation metricLocation(
        const std::string & /*host_name*/,
        const std::string & /*service_description*/,
        const Metric::Name & /*var*/) const override {
        return {};
    }
    [[nodiscard]] bool pnp4nagiosEnabled() const override { return {}; }

private:
    Triggers triggers_;

    [[nodiscard]] void *implInternal() const override { return {}; }
};

struct ColumnNamesAndTypesTest : public ::testing::Test {
protected:
    DummyMonitoringCore mc_;
    LogCache log_cache_{&mc_};
};

using ColumnDefinition = std::pair<std::string, ColumnType>;

class ColumnDefinitions {
public:
    ColumnDefinitions(std::initializer_list<ColumnDefinition> defs)
        : defs_{defs} {
        sort();
    }

    explicit ColumnDefinitions(const Table &table) {
        table.any_column([this](const auto &c) {
            defs_.emplace_back(c->name(), c->type());
            return false;
        });
        sort();
    }

    bool operator==(const ColumnDefinitions &rhs) const {
        return defs_ == rhs.defs_;
    }

    bool operator!=(const ColumnDefinitions &rhs) const {
        return !(*this == rhs);
    }

    ColumnDefinitions &operator+=(const ColumnDefinitions &rhs) {
        defs_.insert(defs_.end(), rhs.defs_.begin(), rhs.defs_.end());
        sort();
        return *this;
    }

    ColumnDefinitions operator+(const ColumnDefinitions &other) const {
        return ColumnDefinitions{*this} += other;
    }

private:
    std::vector<ColumnDefinition> defs_;

    void sort() { std::ranges::sort(defs_); }

    friend std::ostream &operator<<(std::ostream &os,
                                    const ColumnDefinitions &rhs) {
        for (const auto &[name, type] : rhs.defs_) {
            os << "{" << name << ", " << static_cast<int>(type) << "}, ";
        }
        return os;
    }

    friend ColumnDefinitions operator/(const std::string &prefix,
                                       ColumnDefinitions rhs) {
        for (auto &[name, type] : rhs.defs_) {
            name.insert(0, prefix);
        }
        return rhs;
    }
};

namespace {
// Our basic "building blocks"
ColumnDefinitions columns_columns();
ColumnDefinitions commands_columns();
ColumnDefinitions comments_columns();
ColumnDefinitions contact_groups_columns();
ColumnDefinitions contacts_columns();
ColumnDefinitions crash_reports_columns();
ColumnDefinitions downtimes_columns();
ColumnDefinitions event_console_events_columns();
ColumnDefinitions event_console_history_columns();
ColumnDefinitions event_console_rules_columns();
ColumnDefinitions event_console_status_columns();
ColumnDefinitions service_groups_columns();
ColumnDefinitions host_groups_columns();
ColumnDefinitions hosts_and_services_columns();
ColumnDefinitions hosts_columns();
ColumnDefinitions log_columns();
ColumnDefinitions services_columns();
ColumnDefinitions state_history_columns();
ColumnDefinitions status_columns();
ColumnDefinitions timeperiods_columns();

ColumnDefinitions all_hosts_columns() {
    return hosts_columns() +  //
           hosts_and_services_columns();
}

ColumnDefinitions all_services_columns() {
    return services_columns() +  //
           hosts_and_services_columns();
}

ColumnDefinitions all_state_history_columns() {
    return state_history_columns() +  //
           "current_host_" / all_hosts_columns() +
           "current_service_" / all_services_columns();
}

ColumnDefinitions columns_columns() {
    return {
        {"description", ColumnType::string},
        {"name", ColumnType::string},
        {"table", ColumnType::string},
        {"type", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableColumns) {
    EXPECT_EQ(columns_columns(),  //
              ColumnDefinitions(TableColumns{}));
}

namespace {
ColumnDefinitions commands_columns() {
    return {
        {"line", ColumnType::string},
        {"name", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableCommands) {
    EXPECT_EQ(commands_columns(),  //
              ColumnDefinitions(TableCommands{}));
}

namespace {
ColumnDefinitions comments_columns() {
    return {
        {"author", ColumnType::string},     //
        {"comment", ColumnType::string},    //
        {"entry_time", ColumnType::time},   //
        {"entry_type", ColumnType::int_},   //
        {"expire_time", ColumnType::time},  //
        {"expires", ColumnType::int_},      //
        {"id", ColumnType::int_},           //
        {"is_service", ColumnType::int_},   //
        {"persistent", ColumnType::int_},   //
        {"source", ColumnType::int_},       //
        {"type", ColumnType::int_},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableComments) {
    EXPECT_EQ(comments_columns() +                 //
                  "host_" / all_hosts_columns() +  //
                  "service_" / all_services_columns(),
              ColumnDefinitions(TableComments{&mc_}));
}

namespace {
ColumnDefinitions contact_groups_columns() {
    return {
        {"alias", ColumnType::string},
        {"members", ColumnType::list},
        {"name", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableContactGroups) {
    EXPECT_EQ(contact_groups_columns(),
              ColumnDefinitions(TableContactGroups{}));
}

namespace {
ColumnDefinitions contacts_columns() {
    return {
        {"address1", ColumnType::string},
        {"address2", ColumnType::string},
        {"address3", ColumnType::string},
        {"address4", ColumnType::string},
        {"address5", ColumnType::string},
        {"address6", ColumnType::string},
        {"alias", ColumnType::string},
        {"can_submit_commands", ColumnType::int_},
        {"custom_variable_names", ColumnType::list},
        {"custom_variable_values", ColumnType::list},
        {"custom_variables", ColumnType::dictstr},
        {"email", ColumnType::string},
        {"host_notification_period", ColumnType::string},
        {"host_notifications_enabled", ColumnType::int_},
        {"in_host_notification_period", ColumnType::int_},
        {"in_service_notification_period", ColumnType::int_},
        {"label_names", ColumnType::list},
        {"label_source_names", ColumnType::list},
        {"label_source_values", ColumnType::list},
        {"label_sources", ColumnType::dictstr},
        {"label_values", ColumnType::list},
        {"labels", ColumnType::dictstr},
        {"modified_attributes", ColumnType::int_},
        {"modified_attributes_list", ColumnType::list},
        {"name", ColumnType::string},
        {"pager", ColumnType::string},
        {"service_notification_period", ColumnType::string},
        {"service_notifications_enabled", ColumnType::int_},
        {"tag_names", ColumnType::list},
        {"tag_values", ColumnType::list},
        {"tags", ColumnType::dictstr},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableContacts) {
    EXPECT_EQ(contacts_columns(),  //
              ColumnDefinitions(TableContacts{}));
}

namespace {
ColumnDefinitions crash_reports_columns() {
    return {
        {"component", ColumnType::string},
        {"id", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableCrashReports) {
    EXPECT_EQ(crash_reports_columns(),
              ColumnDefinitions(TableCrashReports{&mc_}));
}

namespace {
ColumnDefinitions downtimes_columns() {
    return {
        {"author", ColumnType::string},    //
        {"comment", ColumnType::string},   //
        {"duration", ColumnType::int_},    //
        {"end_time", ColumnType::time},    //
        {"entry_time", ColumnType::time},  //
        {"fixed", ColumnType::int_},       //
        {"id", ColumnType::int_},
        {"is_pending", ColumnType::int_},
        {"is_service", ColumnType::int_},
        {"origin", ColumnType::int_},
        {"recurring", ColumnType::int_},
        {"start_time", ColumnType::time},  //
        {"triggered_by", ColumnType::int_},
        {"type", ColumnType::int_},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableDowntimes) {
    EXPECT_EQ(downtimes_columns() +                //
                  "host_" / all_hosts_columns() +  //
                  "service_" / all_services_columns(),
              ColumnDefinitions(TableDowntimes{&mc_}));
}

namespace {
ColumnDefinitions event_console_events_columns() {
    return {
        {"event_application", ColumnType::string},
        {"event_comment", ColumnType::string},
        {"event_contact", ColumnType::string},
        {"event_contact_groups", ColumnType::list},
        {"event_contact_groups_precedence", ColumnType::string},
        {"event_core_host", ColumnType::string},
        {"event_count", ColumnType::int_},
        {"event_facility", ColumnType::int_},
        {"event_first", ColumnType::time},
        {"event_host", ColumnType::string},
        {"event_host_in_downtime", ColumnType::int_},
        {"event_id", ColumnType::int_},
        {"event_ipaddress", ColumnType::string},
        {"event_last", ColumnType::time},
        {"event_match_groups", ColumnType::list},
        {"event_match_groups_syslog_application", ColumnType::list},
        {"event_orig_host", ColumnType::string},
        {"event_owner", ColumnType::string},
        {"event_phase", ColumnType::string},
        {"event_pid", ColumnType::int_},
        {"event_priority", ColumnType::int_},
        {"event_rule_id", ColumnType::string},
        {"event_sl", ColumnType::int_},
        {"event_state", ColumnType::int_},
        {"event_text", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableEventConsoleEvents) {
    EXPECT_EQ(event_console_events_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableEventConsoleEvents{&mc_}));
}

namespace {
ColumnDefinitions event_console_history_columns() {
    return {
        {"history_addinfo", ColumnType::string},
        {"history_line", ColumnType::int_},
        {"history_time", ColumnType::time},
        {"history_what", ColumnType::string},
        {"history_who", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableEventConsoleHistory) {
    EXPECT_EQ(event_console_history_columns() +     //
                  event_console_events_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableEventConsoleHistory{&mc_}));
}

namespace {
ColumnDefinitions event_console_rules_columns() {
    return {
        {"rule_hits", ColumnType::int_},
        {"rule_id", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableEventConsoleRules) {
    EXPECT_EQ(event_console_rules_columns(),
              ColumnDefinitions(TableEventConsoleRules{}));
}

namespace {
// Why on earth do all column names have a "status_" prefix here?
ColumnDefinitions event_console_status_columns() {
    return {
        {"status_average_connect_rate", ColumnType::double_},
        {"status_average_drop_rate", ColumnType::double_},
        {"status_average_event_rate", ColumnType::double_},
        {"status_average_message_rate", ColumnType::double_},
        {"status_average_overflow_rate", ColumnType::double_},
        {"status_average_processing_time", ColumnType::double_},
        {"status_average_request_time", ColumnType::double_},
        {"status_average_rule_hit_rate", ColumnType::double_},
        {"status_average_rule_trie_rate", ColumnType::double_},
        {"status_average_sync_time", ColumnType::double_},
        {"status_config_load_time", ColumnType::int_},
        {"status_connect_rate", ColumnType::double_},
        {"status_connects", ColumnType::int_},
        {"status_drop_rate", ColumnType::double_},
        {"status_drops", ColumnType::int_},
        {"status_event_limit_active_hosts", ColumnType::list},
        {"status_event_limit_active_overall", ColumnType::int_},
        {"status_event_limit_active_rules", ColumnType::list},
        {"status_event_limit_host", ColumnType::int_},
        {"status_event_limit_overall", ColumnType::int_},
        {"status_event_limit_rule", ColumnType::int_},
        {"status_event_rate", ColumnType::double_},
        {"status_events", ColumnType::int_},
        {"status_message_rate", ColumnType::double_},
        {"status_messages", ColumnType::int_},
        {"status_num_open_events", ColumnType::int_},
        {"status_overflow_rate", ColumnType::double_},
        {"status_overflows", ColumnType::int_},
        {"status_replication_last_sync", ColumnType::time},
        {"status_replication_slavemode", ColumnType::string},
        {"status_replication_success", ColumnType::int_},
        {"status_rule_hit_rate", ColumnType::double_},
        {"status_rule_hits", ColumnType::int_},
        {"status_rule_trie_rate", ColumnType::double_},
        {"status_rule_tries", ColumnType::int_},
        {"status_virtual_memory_size", ColumnType::int_},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableEventConsoleStatus) {
    EXPECT_EQ(event_console_status_columns(),
              ColumnDefinitions(TableEventConsoleStatus{}));
}

namespace {
ColumnDefinitions service_groups_columns() {
    return {
        {"action_url", ColumnType::string},
        {"alias", ColumnType::string},
        {"members", ColumnType::list},
        {"members_with_state", ColumnType::list},
        {"name", ColumnType::string},
        {"notes", ColumnType::string},
        {"notes_url", ColumnType::string},
        {"num_services", ColumnType::int_},
        {"num_services_crit", ColumnType::int_},
        {"num_services_handled_problems", ColumnType::int_},
        {"num_services_hard_crit", ColumnType::int_},
        {"num_services_hard_ok", ColumnType::int_},
        {"num_services_hard_unknown", ColumnType::int_},
        {"num_services_hard_warn", ColumnType::int_},
        {"num_services_ok", ColumnType::int_},
        {"num_services_pending", ColumnType::int_},
        {"num_services_unhandled_problems", ColumnType::int_},
        {"num_services_unknown", ColumnType::int_},
        {"num_services_warn", ColumnType::int_},
        {"worst_service_state", ColumnType::int_},
    };
}

ColumnDefinitions host_groups_columns() {
    return {
        {"num_hosts", ColumnType::int_},
        {"num_hosts_down", ColumnType::int_},
        {"num_hosts_handled_problems", ColumnType::int_},
        {"num_hosts_pending", ColumnType::int_},
        {"num_hosts_unhandled_problems", ColumnType::int_},
        {"num_hosts_unreach", ColumnType::int_},
        {"num_hosts_up", ColumnType::int_},
        {"worst_host_state", ColumnType::int_},
        // TODO(sp) HUH??? Why is this not in service_groups_columns?
        {"worst_service_hard_state", ColumnType::int_},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableHostGroups) {
    EXPECT_EQ(host_groups_columns() +  //
                  service_groups_columns(),
              ColumnDefinitions(TableHostGroups{}));
}

namespace {
ColumnDefinitions hosts_and_services_columns() {
    return {
        {"accept_passive_checks", ColumnType::int_},
        {"acknowledged", ColumnType::int_},
        {"acknowledgement_type", ColumnType::int_},
        {"action_url", ColumnType::string},
        {"action_url_expanded", ColumnType::string},
        {"active_checks_enabled", ColumnType::int_},
        {"check_command", ColumnType::string},
        {"check_command_expanded", ColumnType::string},
        {"check_flapping_recovery_notification", ColumnType::int_},
        {"check_freshness", ColumnType::int_},
        {"check_interval", ColumnType::double_},
        {"check_options", ColumnType::int_},
        {"check_period", ColumnType::string},
        {"check_type", ColumnType::int_},
        {"checks_enabled", ColumnType::int_},
        {"comments", ColumnType::list},
        {"comments_with_extra_info", ColumnType::list},
        {"comments_with_info", ColumnType::list},
        {"contact_groups", ColumnType::list},
        {"contacts", ColumnType::list},
        {"current_attempt", ColumnType::int_},
        {"current_notification_number", ColumnType::int_},
        {"custom_variable_names", ColumnType::list},
        {"custom_variable_values", ColumnType::list},
        {"custom_variables", ColumnType::dictstr},
        {"display_name", ColumnType::string},
        {"downtimes", ColumnType::list},
        {"downtimes_with_extra_info", ColumnType::list},
        {"downtimes_with_info", ColumnType::list},
        {"event_handler", ColumnType::string},
        {"event_handler_enabled", ColumnType::int_},
        {"execution_time", ColumnType::double_},
        {"first_notification_delay", ColumnType::double_},
        {"flap_detection_enabled", ColumnType::int_},
        {"flappiness", ColumnType::double_},
        {"hard_state", ColumnType::int_},
        {"has_been_checked", ColumnType::int_},
        {"high_flap_threshold", ColumnType::double_},
        {"icon_image", ColumnType::string},
        {"icon_image_alt", ColumnType::string},
        {"icon_image_expanded", ColumnType::string},
        {"in_check_period", ColumnType::int_},
        {"in_notification_period", ColumnType::int_},
        {"in_service_period", ColumnType::int_},
        {"initial_state", ColumnType::int_},
        {"is_executing", ColumnType::int_},
        {"is_flapping", ColumnType::int_},
        {"label_names", ColumnType::list},
        {"label_source_names", ColumnType::list},
        {"label_source_values", ColumnType::list},
        {"label_sources", ColumnType::dictstr},
        {"label_values", ColumnType::list},
        {"labels", ColumnType::dictstr},
        {"last_check", ColumnType::time},
        {"last_hard_state", ColumnType::int_},
        {"last_hard_state_change", ColumnType::time},
        {"last_notification", ColumnType::time},
        {"last_state", ColumnType::int_},
        {"last_state_change", ColumnType::time},
        {"latency", ColumnType::double_},
        {"long_plugin_output", ColumnType::string},
        {"low_flap_threshold", ColumnType::double_},
        {"max_check_attempts", ColumnType::int_},
        {"metrics", ColumnType::list},
        {"modified_attributes", ColumnType::int_},
        {"modified_attributes_list", ColumnType::list},
        {"next_check", ColumnType::time},
        {"next_notification", ColumnType::time},
        {"no_more_notifications", ColumnType::int_},
        {"notes", ColumnType::string},
        {"notes_expanded", ColumnType::string},
        {"notes_url", ColumnType::string},
        {"notes_url_expanded", ColumnType::string},
        {"notification_interval", ColumnType::double_},
        {"notification_period", ColumnType::string},
        {"notification_postponement_reason", ColumnType::string},
        {"notifications_enabled", ColumnType::int_},
        {"pending_flex_downtime", ColumnType::int_},
        {"percent_state_change", ColumnType::double_},
        {"perf_data", ColumnType::string},
        {"performance_data", ColumnType::dictdouble},
        {"plugin_output", ColumnType::string},
        {"pnpgraph_present", ColumnType::int_},
        {"previous_hard_state", ColumnType::int_},
        {"process_performance_data", ColumnType::int_},
        {"retry_interval", ColumnType::double_},
        {"scheduled_downtime_depth", ColumnType::int_},
        {"service_period", ColumnType::string},
        {"staleness", ColumnType::double_},
        {"state", ColumnType::int_},
        {"state_type", ColumnType::int_},
        {"tag_names", ColumnType::list},
        {"tag_values", ColumnType::list},
        {"tags", ColumnType::dictstr},
    };
}

ColumnDefinitions hosts_columns() {
    return {
        {"address", ColumnType::string},
        {"alias", ColumnType::string},
        {"childs", ColumnType::list},
        {"filename", ColumnType::string},
        {"groups", ColumnType::list},
        {"last_time_down", ColumnType::time},
        {"last_time_unreachable", ColumnType::time},
        {"last_time_up", ColumnType::time},
        {"mk_inventory", ColumnType::blob},
        {"mk_inventory_gz", ColumnType::blob},
        {"mk_inventory_last", ColumnType::time},
        {"mk_logwatch_files", ColumnType::list},
        {"name", ColumnType::string},
        {"num_services", ColumnType::int_},
        {"num_services_crit", ColumnType::int_},
        {"num_services_handled_problems", ColumnType::int_},
        {"num_services_hard_crit", ColumnType::int_},
        {"num_services_hard_ok", ColumnType::int_},
        {"num_services_hard_unknown", ColumnType::int_},
        {"num_services_hard_warn", ColumnType::int_},
        {"num_services_ok", ColumnType::int_},
        {"num_services_pending", ColumnType::int_},
        {"num_services_unhandled_problems", ColumnType::int_},
        {"num_services_unknown", ColumnType::int_},
        {"num_services_warn", ColumnType::int_},
        {"obsess_over_host", ColumnType::int_},
        {"parents", ColumnType::list},
        {"services", ColumnType::list},
        {"services_with_fullstate", ColumnType::list},
        {"services_with_info", ColumnType::list},
        {"services_with_state", ColumnType::list},
        {"smartping_timeout", ColumnType::int_},
        {"statusmap_image", ColumnType::string},
        {"structured_status", ColumnType::blob},
        {"total_services", ColumnType::int_},
        {"worst_service_hard_state", ColumnType::int_},
        {"worst_service_state", ColumnType::int_},
        {"x_3d", ColumnType::double_},
        {"y_3d", ColumnType::double_},
        {"z_3d", ColumnType::double_},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableHosts) {
    EXPECT_EQ(all_hosts_columns(),  //
              ColumnDefinitions(TableHosts{&mc_}));
}

TEST_F(ColumnNamesAndTypesTest, TableHostsByGroup) {
    EXPECT_EQ(all_hosts_columns() +  //
                  "hostgroup_" / host_groups_columns() +
                  "hostgroup_" / service_groups_columns(),
              ColumnDefinitions(TableHostsByGroup{&mc_}));
}

namespace {
ColumnDefinitions labels_columns() {
    return {
        {"name", ColumnType::string},
        {"value", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableLabels) {
    EXPECT_EQ(labels_columns(),  //
              ColumnDefinitions(TableLabels{}));
}

namespace {
ColumnDefinitions log_columns() {
    return {
        {"attempt", ColumnType::int_},
        {"class", ColumnType::int_},
        {"command_name", ColumnType::string},
        {"comment", ColumnType::string},
        {"contact_name", ColumnType::string},
        {"host_name", ColumnType::string},
        {"lineno", ColumnType::int_},
        {"long_plugin_output", ColumnType::string},
        {"message", ColumnType::string},
        {"options", ColumnType::string},
        {"plugin_output", ColumnType::string},
        {"service_description", ColumnType::string},
        {"state", ColumnType::int_},
        {"state_info", ColumnType::string},
        {"state_type", ColumnType::string},
        {"time", ColumnType::time},
        {"type", ColumnType::string},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableLog) {
    EXPECT_EQ(log_columns() +  //
                  "current_host_" / all_hosts_columns() +
                  "current_service_" / all_services_columns() +
                  "current_contact_" / contacts_columns() +
                  "current_command_" / commands_columns(),
              ColumnDefinitions(TableLog{&mc_, &log_cache_}));
}

TEST_F(ColumnNamesAndTypesTest, TableServiceGroups) {
    EXPECT_EQ(service_groups_columns(),
              ColumnDefinitions(TableServiceGroups{}));
}

namespace {
ColumnDefinitions services_columns() {
    return {
        {"cache_interval", ColumnType::int_},
        {"cached_at", ColumnType::time},
        {"description", ColumnType::string},
        {"groups", ColumnType::list},
        {"in_passive_check_period", ColumnType::int_},
        {"last_time_critical", ColumnType::time},
        {"last_time_ok", ColumnType::time},
        {"last_time_unknown", ColumnType::time},
        {"last_time_warning", ColumnType::time},
        {"obsess_over_service", ColumnType::int_},
        {"passive_check_period", ColumnType::string},
        {"robotmk_last_error_log", ColumnType::blob},
        {"robotmk_last_error_log_gz", ColumnType::blob},
        {"robotmk_last_log", ColumnType::blob},
        {"robotmk_last_log_gz", ColumnType::blob},
        {"prediction_files", ColumnType::list},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableServices) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableServices{&mc_}));
}

TEST_F(ColumnNamesAndTypesTest, TableServicesByGroup) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns() +
                  "servicegroup_" / service_groups_columns(),
              ColumnDefinitions(TableServicesByGroup{&mc_}));
}

TEST_F(ColumnNamesAndTypesTest, TableServicesByHostGroup) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns() +
                  "hostgroup_" / host_groups_columns() +
                  "hostgroup_" / service_groups_columns(),
              ColumnDefinitions(TableServicesByHostGroup{&mc_}));
}

namespace {
ColumnDefinitions state_history_columns() {
    return {
        {"debug_info", ColumnType::string},
        {"duration", ColumnType::int_},
        {"duration_critical", ColumnType::int_},
        {"duration_ok", ColumnType::int_},
        {"duration_part", ColumnType::double_},
        {"duration_part_critical", ColumnType::double_},
        {"duration_part_ok", ColumnType::double_},
        {"duration_part_unknown", ColumnType::double_},
        {"duration_part_unmonitored", ColumnType::double_},
        {"duration_part_warning", ColumnType::double_},
        {"duration_unknown", ColumnType::int_},
        {"duration_unmonitored", ColumnType::int_},
        {"duration_warning", ColumnType::int_},
        {"from", ColumnType::time},
        {"host_down", ColumnType::int_},
        {"host_name", ColumnType::string},
        {"in_downtime", ColumnType::int_},
        {"in_host_downtime", ColumnType::int_},
        {"in_notification_period", ColumnType::int_},
        {"in_service_period", ColumnType::int_},
        {"is_flapping", ColumnType::int_},
        {"lineno", ColumnType::int_},
        {"log_output", ColumnType::string},
        {"long_log_output", ColumnType::string},
        {"notification_period", ColumnType::string},
        {"service_description", ColumnType::string},
        {"service_period", ColumnType::string},
        {"state", ColumnType::int_},
        {"time", ColumnType::time},
        {"until", ColumnType::time},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableStateHistory) {
    EXPECT_EQ(all_state_history_columns(),
              ColumnDefinitions(TableStateHistory{&mc_, &log_cache_}));
}

namespace {
ColumnDefinitions status_columns() {
    return {
        {"accept_passive_host_checks", ColumnType::int_},
        {"accept_passive_service_checks", ColumnType::int_},
        {"average_latency_checker", ColumnType::double_},
        {"average_latency_fetcher", ColumnType::double_},
        {"average_latency_generic", ColumnType::double_},
        {"average_latency_real_time", ColumnType::double_},
        {"average_runnable_jobs_checker", ColumnType::double_},
        {"average_runnable_jobs_fetcher", ColumnType::double_},
        {"cached_log_messages", ColumnType::int_},
        {"carbon_bytes_sent", ColumnType::double_},
        {"carbon_bytes_sent_rate", ColumnType::double_},
        {"carbon_overflows", ColumnType::double_},
        {"carbon_overflows_rate", ColumnType::double_},
        {"carbon_queue_usage", ColumnType::double_},
        {"carbon_queue_usage_rate", ColumnType::double_},
        {"check_external_commands", ColumnType::int_},
        {"check_host_freshness", ColumnType::int_},
        {"check_service_freshness", ColumnType::int_},
        {"connections", ColumnType::double_},
        {"connections_rate", ColumnType::double_},
        {"core_pid", ColumnType::int_},
        {"edition", ColumnType::string},
        {"enable_event_handlers", ColumnType::int_},
        {"enable_flap_detection", ColumnType::int_},
        {"enable_notifications", ColumnType::int_},
        {"execute_host_checks", ColumnType::int_},
        {"execute_service_checks", ColumnType::int_},
        {"external_command_buffer_max", ColumnType::int_},
        {"external_command_buffer_slots", ColumnType::int_},
        {"external_command_buffer_usage", ColumnType::int_},
        {"external_commands", ColumnType::double_},
        {"external_commands_rate", ColumnType::double_},
        {"forks", ColumnType::double_},
        {"forks_rate", ColumnType::double_},
        {"has_event_handlers", ColumnType::int_},
        {"helper_usage_checker", ColumnType::double_},
        {"helper_usage_fetcher", ColumnType::double_},
        {"helper_usage_generic", ColumnType::double_},
        {"helper_usage_real_time", ColumnType::double_},
        {"host_checks", ColumnType::double_},
        {"host_checks_rate", ColumnType::double_},
        {"influxdb_bytes_sent", ColumnType::double_},
        {"influxdb_bytes_sent_rate", ColumnType::double_},
        {"influxdb_overflows", ColumnType::double_},
        {"influxdb_overflows_rate", ColumnType::double_},
        {"influxdb_queue_usage", ColumnType::double_},
        {"influxdb_queue_usage_rate", ColumnType::double_},
        {"interval_length", ColumnType::int_},
        {"max_long_output_size", ColumnType::int_},
        {"last_command_check", ColumnType::time},
        {"last_log_rotation", ColumnType::time},
        {"license_usage_history", ColumnType::blob},
        {"livechecks", ColumnType::double_},
        {"livechecks_rate", ColumnType::double_},
        {"livestatus_active_connections", ColumnType::int_},
        {"livestatus_overflows", ColumnType::double_},
        {"livestatus_overflows_rate", ColumnType::double_},
        {"livestatus_queued_connections", ColumnType::int_},
        {"livestatus_threads", ColumnType::int_},
        {"livestatus_usage", ColumnType::double_},
        {"livestatus_version", ColumnType::string},
        {"log_messages", ColumnType::double_},
        {"log_messages_rate", ColumnType::double_},
        {"metrics_count", ColumnType::double_},
        {"metrics_count_rate", ColumnType::double_},
        {"mk_inventory_last", ColumnType::time},
        {"nagios_pid", ColumnType::int_},
        {"neb_callbacks", ColumnType::double_},
        {"neb_callbacks_rate", ColumnType::double_},
        {"num_hosts", ColumnType::int_},
        {"num_queued_alerts", ColumnType::int_},
        {"num_queued_notifications", ColumnType::int_},
        {"num_services", ColumnType::int_},
        {"obsess_over_hosts", ColumnType::int_},
        {"obsess_over_services", ColumnType::int_},
        {"perf_data_count", ColumnType::double_},
        {"perf_data_count_rate", ColumnType::double_},
        {"process_performance_data", ColumnType::int_},
        {"program_start", ColumnType::time},
        {"program_version", ColumnType::string},
        {"requests", ColumnType::double_},
        {"requests_rate", ColumnType::double_},
        {"rrdcached_bytes_sent", ColumnType::double_},
        {"rrdcached_bytes_sent_rate", ColumnType::double_},
        {"rrdcached_overflows", ColumnType::double_},
        {"rrdcached_overflows_rate", ColumnType::double_},
        {"rrdcached_queue_usage", ColumnType::double_},
        {"rrdcached_queue_usage_rate", ColumnType::double_},
        {"service_checks", ColumnType::double_},
        {"service_checks_rate", ColumnType::double_},
        {"state_file_created", ColumnType::time},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableStatus) {
    EXPECT_EQ(status_columns(),  //
              ColumnDefinitions(TableStatus{&mc_}));
}

namespace {
ColumnDefinitions timeperiods_columns() {
    return {
        {"alias", ColumnType::string},
        {"in", ColumnType::int_},
        {"name", ColumnType::string},
        {"next_transition", ColumnType::time},
        {"next_transition_id", ColumnType::int_},
        {"num_transitions", ColumnType::int_},
        {"transitions", ColumnType::list},
    };
}
}  // namespace

TEST_F(ColumnNamesAndTypesTest, TableTimeperiods) {
    EXPECT_EQ(timeperiods_columns(), ColumnDefinitions(TableTimeperiods{}));
}
