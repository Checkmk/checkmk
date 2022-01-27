// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <initializer_list>
#include <map>
#include <ostream>
#include <string>
#include <utility>
#include <vector>

#include "Column.h"
#include "Table.h"
#include "TableColumns.h"
#include "TableCommands.h"
#include "TableContactGroups.h"
#include "TableContacts.h"
#include "TableCrashReports.h"
#include "TableEventConsoleRules.h"
#include "TableEventConsoleStatus.h"
#include "TableHostGroups.h"
#include "TableServiceGroups.h"
#include "TableStatus.h"
#include "TableTimeperiods.h"
#include "gtest/gtest.h"

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

    void sort() { std::sort(defs_.begin(), defs_.end()); }

    friend std::ostream &operator<<(std::ostream &os,
                                    const ColumnDefinitions &foo) {
        for (const auto &[name, type] : foo.defs_) {
            os << "{" << name << ", " << static_cast<int>(type) << "}, ";
        }
        return os;
    }
};

TEST(TableColumns, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"description", ColumnType::string},
                  {"name", ColumnType::string},
                  {"table", ColumnType::string},
                  {"type", ColumnType::string},
              }),
              ColumnDefinitions(TableColumns{nullptr}));
}

TEST(TableCommands, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"line", ColumnType::string},
                  {"name", ColumnType::string},
              }),
              ColumnDefinitions(TableCommands{nullptr}));
}

TEST(TableComments, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableContactGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"alias", ColumnType::string},
                  {"members", ColumnType::list},
                  {"name", ColumnType::string},
              }),
              ColumnDefinitions(TableContactGroups{nullptr}));
}

TEST(TableContacts, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
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
                  {"custom_variables", ColumnType::dict},
                  {"email", ColumnType::string},
                  {"host_notification_period", ColumnType::string},
                  {"host_notifications_enabled", ColumnType::int_},
                  {"in_host_notification_period", ColumnType::int_},
                  {"in_service_notification_period", ColumnType::int_},
                  {"label_names", ColumnType::list},
                  {"label_source_names", ColumnType::list},
                  {"label_source_values", ColumnType::list},
                  {"label_sources", ColumnType::dict},
                  {"label_values", ColumnType::list},
                  {"labels", ColumnType::dict},
                  {"modified_attributes", ColumnType::int_},
                  {"modified_attributes_list", ColumnType::list},
                  {"name", ColumnType::string},
                  {"pager", ColumnType::string},
                  {"service_notification_period", ColumnType::string},
                  {"service_notifications_enabled", ColumnType::int_},
                  {"tag_names", ColumnType::list},
                  {"tag_values", ColumnType::list},
                  {"tags", ColumnType::dict},
              }),
              ColumnDefinitions(TableContacts{nullptr}));
}

TEST(TableCrashReports, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"component", ColumnType::string},
                  {"id", ColumnType::string},

              }),
              ColumnDefinitions(TableCrashReports{nullptr}));
}

TEST(TableDowntimes, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableEventConsoleEvents, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableEventConsoleHistory, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableEventConsoleRules, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"rule_hits", ColumnType::int_},
                  {"rule_id", ColumnType::string},
              }),
              ColumnDefinitions(TableEventConsoleRules{nullptr}));
}

TEST(TableEventConsoleStatus, ColumnNamesAndTypes) {
    // Why on earth do all column names have a "status_" prefix here?
    EXPECT_EQ(ColumnDefinitions({
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
              }),
              ColumnDefinitions(TableEventConsoleStatus{nullptr}));
}

static ColumnDefinitions common_host_and_service_groups_columns() {
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

TEST(TableHostGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions(
                  {{"num_hosts", ColumnType::int_},
                   {"num_hosts_down", ColumnType::int_},
                   {"num_hosts_handled_problems", ColumnType::int_},
                   {"num_hosts_pending", ColumnType::int_},
                   {"num_hosts_unhandled_problems", ColumnType::int_},
                   {"num_hosts_unreach", ColumnType::int_},
                   {"num_hosts_up", ColumnType::int_},
                   {"worst_host_state", ColumnType::int_},
                   // TODO(sp) HUH??? Why is this not in the common columns?
                   {"worst_service_hard_state", ColumnType::int_}}) +
                  common_host_and_service_groups_columns(),
              ColumnDefinitions(TableHostGroups{nullptr}));
}

TEST(TableHosts, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableHostsByGroup, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableLog, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableServiceGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(common_host_and_service_groups_columns(),
              ColumnDefinitions(TableServiceGroups{nullptr}));
}

TEST(TableServices, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableServicesByGroup, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableServicesByHostGroup, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableStateHistory, ColumnNamesAndTypes) {
    // TODO(sp)
}

TEST(TableStatus, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"accept_passive_host_checks", ColumnType::int_},
                  {"accept_passive_service_checks", ColumnType::int_},
                  {"average_latency_cmk", ColumnType::double_},
                  {"average_latency_fetcher", ColumnType::double_},
                  {"average_latency_generic", ColumnType::double_},
                  {"average_latency_real_time", ColumnType::double_},
                  {"average_runnable_jobs_checker", ColumnType::double_},
                  {"average_runnable_jobs_fetcher", ColumnType::double_},
                  {"cached_log_messages", ColumnType::int_},
                  {"check_external_commands", ColumnType::int_},
                  {"check_host_freshness", ColumnType::int_},
                  {"check_service_freshness", ColumnType::int_},
                  {"connections", ColumnType::double_},
                  {"connections_rate", ColumnType::double_},
                  {"core_pid", ColumnType::int_},
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
                  {"helper_usage_cmk", ColumnType::double_},
                  {"helper_usage_fetcher", ColumnType::double_},
                  {"helper_usage_generic", ColumnType::double_},
                  {"helper_usage_real_time", ColumnType::double_},
                  {"host_checks", ColumnType::double_},
                  {"host_checks_rate", ColumnType::double_},
                  {"interval_length", ColumnType::int_},
                  {"is_trial_expired", ColumnType::int_},
#ifdef CMC
                  {"last_command_check", ColumnType::int_},
#else
                  {"last_command_check", ColumnType::time},
#endif
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
                  {"process_performance_data", ColumnType::int_},
                  {"program_start", ColumnType::time},
                  {"program_version", ColumnType::string},
                  {"requests", ColumnType::double_},
                  {"requests_rate", ColumnType::double_},
                  {"service_checks", ColumnType::double_},
                  {"service_checks_rate", ColumnType::double_},
                  {"state_file_created", ColumnType::time},
              }),
#ifdef CMC
              ColumnDefinitions(TableStatus{nullptr, nullptr})
#else
              ColumnDefinitions(TableStatus{nullptr})
#endif
    );
}

TEST(TableTimeperiods, ColumnNamesAndTypes) {
    EXPECT_EQ(ColumnDefinitions({
                  {"alias", ColumnType::string},
                  {"in", ColumnType::int_},
                  {"name", ColumnType::string},
#ifdef CMC
                  {"next_transition", ColumnType::time},
                  {"next_transition_id", ColumnType::int_},
                  {"num_transitions", ColumnType::int_},
                  {"transitions", ColumnType::list},
#endif
              }),
              ColumnDefinitions(TableTimeperiods{nullptr}));
}
