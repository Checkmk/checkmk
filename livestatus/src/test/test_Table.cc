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
#include "TableComments.h"
#include "TableContactGroups.h"
#include "TableContacts.h"
#include "TableCrashReports.h"
#include "TableDowntimes.h"
#include "TableEventConsoleEvents.h"
#include "TableEventConsoleHistory.h"
#include "TableEventConsoleRules.h"
#include "TableEventConsoleStatus.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "TableHostsByGroup.h"
#include "TableLog.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "TableServicesByGroup.h"
#include "TableServicesByHostGroup.h"
#include "TableStateHistory.h"
#include "TableStatus.h"
#include "TableTimeperiods.h"
#include "gtest/gtest.h"

#ifdef CMC
#include "TableCachedStatehist.h"
#endif

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

// Our basic "building blocks"
static ColumnDefinitions columns_columns();
static ColumnDefinitions commands_columns();
static ColumnDefinitions comments_columns();
static ColumnDefinitions contact_groups_columns();
static ColumnDefinitions contacts_columns();
static ColumnDefinitions crash_reports_columns();
static ColumnDefinitions downtimes_columns();
static ColumnDefinitions event_console_events_columns();
static ColumnDefinitions event_console_history_columns();
static ColumnDefinitions event_console_rules_columns();
static ColumnDefinitions event_console_status_columns();
static ColumnDefinitions service_groups_columns();
static ColumnDefinitions host_groups_columns();
static ColumnDefinitions hosts_and_services_columns();
static ColumnDefinitions hosts_columns();
static ColumnDefinitions log_columns();
static ColumnDefinitions services_columns();
static ColumnDefinitions state_history_columns();
static ColumnDefinitions status_columns();
static ColumnDefinitions timeperiods_columns();

static ColumnDefinitions all_hosts_columns() {
    return hosts_columns() +  //
           hosts_and_services_columns();
}

static ColumnDefinitions all_services_columns() {
    return services_columns() +  //
           hosts_and_services_columns();
}

// Let's enforce the fact that TableCachedStatehist must be a drop-in
// replacement for TableStateHistory.
static ColumnDefinitions all_state_history_columns() {
    return state_history_columns() +  //
           "current_host_" / all_hosts_columns() +
           "current_service_" / all_services_columns();
}

#ifdef CMC
TEST(TableCachedStatehist, ColumnNamesAndTypes) {
    EXPECT_EQ(all_state_history_columns(),
              ColumnDefinitions(TableCachedStatehist{nullptr}));
}
#endif

static ColumnDefinitions columns_columns() {
    return {
        {"description", ColumnType::string},
        {"name", ColumnType::string},
        {"table", ColumnType::string},
        {"type", ColumnType::string},
    };
}

TEST(TableColumns, ColumnNamesAndTypes) {
    EXPECT_EQ(columns_columns(),  //
              ColumnDefinitions(TableColumns{nullptr}));
}

static ColumnDefinitions commands_columns() {
    return {
        {"line", ColumnType::string},
        {"name", ColumnType::string},
    };
}

TEST(TableCommands, ColumnNamesAndTypes) {
    EXPECT_EQ(commands_columns(),  //
              ColumnDefinitions(TableCommands{nullptr}));
}

static ColumnDefinitions comments_columns() {
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

TEST(TableComments, ColumnNamesAndTypes) {
    EXPECT_EQ(comments_columns() +                 //
                  "host_" / all_hosts_columns() +  //
                  "service_" / all_services_columns(),
              ColumnDefinitions(TableComments{nullptr}));
}

static ColumnDefinitions contact_groups_columns() {
    return {
        {"alias", ColumnType::string},
        {"members", ColumnType::list},
        {"name", ColumnType::string},
    };
}

TEST(TableContactGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(contact_groups_columns(),
              ColumnDefinitions(TableContactGroups{nullptr}));
}

static ColumnDefinitions contacts_columns() {
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
    };
}

TEST(TableContacts, ColumnNamesAndTypes) {
    EXPECT_EQ(contacts_columns(),  //
              ColumnDefinitions(TableContacts{nullptr}));
}

static ColumnDefinitions crash_reports_columns() {
    return {
        {"component", ColumnType::string},
        {"id", ColumnType::string},
    };
}

TEST(TableCrashReports, ColumnNamesAndTypes) {
    EXPECT_EQ(crash_reports_columns(),
              ColumnDefinitions(TableCrashReports{nullptr}));
}

static ColumnDefinitions downtimes_columns() {
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

TEST(TableDowntimes, ColumnNamesAndTypes) {
    EXPECT_EQ(downtimes_columns() +                //
                  "host_" / all_hosts_columns() +  //
                  "service_" / all_services_columns(),
              ColumnDefinitions(TableDowntimes{nullptr}));
}

static ColumnDefinitions event_console_events_columns() {
    return {
        {"event_application", ColumnType::string},
        {"event_comment", ColumnType::string},
        {"event_contact", ColumnType::string},
        {"event_contact_groups", ColumnType::list},
        {"event_contact_groups_precedence", ColumnType::string},
        {"event_count", ColumnType::int_},
        {"event_facility", ColumnType::int_},
        {"event_first", ColumnType::time},
        {"event_host", ColumnType::string},
        {"event_host_in_downtime", ColumnType::int_},
        {"event_id", ColumnType::int_},
        {"event_ipaddress", ColumnType::string},
        {"event_last", ColumnType::time},
        {"event_match_groups", ColumnType::list},
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

TEST(TableEventConsoleEvents, ColumnNamesAndTypes) {
    EXPECT_EQ(event_console_events_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableEventConsoleEvents{nullptr}));
}

static ColumnDefinitions event_console_history_columns() {
    return {
        {"history_addinfo", ColumnType::string},
        {"history_line", ColumnType::int_},
        {"history_time", ColumnType::time},
        {"history_what", ColumnType::string},
        {"history_who", ColumnType::string},
    };
}

TEST(TableEventConsoleHistory, ColumnNamesAndTypes) {
    EXPECT_EQ(event_console_history_columns() +     //
                  event_console_events_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableEventConsoleHistory{nullptr}));
}

static ColumnDefinitions event_console_rules_columns() {
    return {
        {"rule_hits", ColumnType::int_},
        {"rule_id", ColumnType::string},
    };
}

TEST(TableEventConsoleRules, ColumnNamesAndTypes) {
    EXPECT_EQ(event_console_rules_columns(),
              ColumnDefinitions(TableEventConsoleRules{nullptr}));
}

// Why on earth do all column names have a "status_" prefix here?
static ColumnDefinitions event_console_status_columns() {
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

TEST(TableEventConsoleStatus, ColumnNamesAndTypes) {
    EXPECT_EQ(event_console_status_columns(),
              ColumnDefinitions(TableEventConsoleStatus{nullptr}));
}

static ColumnDefinitions service_groups_columns() {
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

static ColumnDefinitions host_groups_columns() {
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

TEST(TableHostGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(host_groups_columns() +  //
                  service_groups_columns(),
              ColumnDefinitions(TableHostGroups{nullptr}));
}

static ColumnDefinitions hosts_and_services_columns() {
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
        {"custom_variables", ColumnType::dict},
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
        {"label_sources", ColumnType::dict},
        {"label_values", ColumnType::list},
        {"labels", ColumnType::dict},
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
        {"tags", ColumnType::dict},
    };
}

static ColumnDefinitions hosts_columns() {
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

TEST(TableHosts, ColumnNamesAndTypes) {
    EXPECT_EQ(all_hosts_columns(),  //
              ColumnDefinitions(TableHosts{nullptr}));
}

TEST(TableHostsByGroup, ColumnNamesAndTypes) {
    EXPECT_EQ(all_hosts_columns() +  //
                  "hostgroup_" / host_groups_columns() +
                  "hostgroup_" / service_groups_columns(),
              ColumnDefinitions(TableHostsByGroup{nullptr}));
}

static ColumnDefinitions log_columns() {
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

TEST(TableLog, ColumnNamesAndTypes) {
    EXPECT_EQ(log_columns() +  //
                  "current_host_" / all_hosts_columns() +
                  "current_service_" / all_services_columns() +
                  "current_contact_" / contacts_columns() +
                  "current_command_" / commands_columns(),
              ColumnDefinitions(TableLog{nullptr, nullptr}));
}

TEST(TableServiceGroups, ColumnNamesAndTypes) {
    EXPECT_EQ(service_groups_columns(),
              ColumnDefinitions(TableServiceGroups{nullptr}));
}

static ColumnDefinitions services_columns() {
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
    };
}

TEST(TableServices, ColumnNamesAndTypes) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns(),
              ColumnDefinitions(TableServices{nullptr}));
}

TEST(TableServicesByGroup, ColumnNamesAndTypes) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns() +
                  "servicegroup_" / service_groups_columns(),
              ColumnDefinitions(TableServicesByGroup{nullptr}));
}

TEST(TableServicesByHostGroup, ColumnNamesAndTypes) {
    EXPECT_EQ(all_services_columns() +  //
                  "host_" / all_hosts_columns() +
                  "hostgroup_" / host_groups_columns() +
                  "hostgroup_" / service_groups_columns(),
              ColumnDefinitions(TableServicesByHostGroup{nullptr}));
}

static ColumnDefinitions state_history_columns() {
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

TEST(TableStateHistory, ColumnNamesAndTypes) {
    EXPECT_EQ(all_state_history_columns(),
              ColumnDefinitions(TableStateHistory{nullptr, nullptr}));
}

static ColumnDefinitions status_columns() {
    return {
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
    };
}

TEST(TableStatus, ColumnNamesAndTypes) {
    EXPECT_EQ(status_columns(),  //
              ColumnDefinitions(TableStatus{nullptr}));
}

static ColumnDefinitions timeperiods_columns() {
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

TEST(TableTimeperiods, ColumnNamesAndTypes) {
    EXPECT_EQ(timeperiods_columns(),
              ColumnDefinitions(TableTimeperiods{nullptr}));
}
