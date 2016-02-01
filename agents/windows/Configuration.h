// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Configuration_h
#define Configuration_h

#include "Environment.h"
#include "SettingsCollector.h"
#include "types.h"

/* Example configuration file:

   [global]
# Process this logfile only on the following hosts
only_on = zhamzr12

# Restrict access to certain IP addresses
only_from = 127.0.0.1 192.168.56.0/24

# Enable crash debugging
crash_debug = on


[winperf]
# Select counters to extract. The following counters
# are needed by checks shipped with check_mk.
counters = 10332:msx_queues

[logwatch]
# Select which messages are to be sent in which
# event log
logfile system      = off
logfile application = info
logfile *           = off

[mrpe]
check = DISK_C: mrpe/check_disk -w C:
check = MEM mrpe/check_mem -w 10 -c 20
 */
class Configuration {
public:
    Configuration(const Environment &env);

    unsigned long enabledSections() const;
    unsigned long realtimeSections() const;

    void disableSection(unsigned long section);

    int port() const { return _port; }
    int realtimePort() const { return _realtime_port; }

    bool crashDebug() const { return _crash_debug; }
    bool sectionFlush() const { return _section_flush; }
    bool logwatchSendInitialEntries() const {
        return _logwatch_send_initial_entries;
    }

    bool supportIPV6() const { return _support_ipv6; }

    int realtimeTimeout() const { return _realtime_timeout; }
    std::string passphrase() const { return _passphrase; }

    bool useRealtimeMonitoring() const {
        return !_passphrase.empty() && (_realtime_sections != 0);
    }

    // return true if any section requires wmi functionality
    bool useWMI() const { return _ps_use_wmi; }

    bool psUseWMI() const { return _ps_use_wmi; }
    bool psFullCommandLine() const { return _ps_full_path; }

    script_execution_mode defaultScriptExecutionMode() const {
        return _default_script_execution_mode;
    }
    script_async_execution defaultScriptAsyncExecution() const {
        return _default_script_async_execution;
    }

    std::string configFileName(bool local) const;

    logwatch_textfile *getLogwatchTextfile(const char *filename);
    logwatch_globlines_t &logwatchGloblines() { return *_logwatch_globlines; }
    mrpe_entries_t &mrpeEntries() { return *_mrpe_entries; }
    mrpe_include_t &mrpeIncludes() { return *_mrpe_includes; }

    eventlog_config_t &eventlogConfig() { return *_eventlog_config; }

    fileinfo_paths_t &fileinfoPaths() { return *_fileinfo_paths; }
    script_include_t &scriptIncludes() { return *_script_includes; }

    timeout_configs_t &timeoutConfigs(script_type type) {
        return type == LOCAL ? *_timeout_configs_local
                             : *_timeout_configs_plugin;
    }
    cache_configs_t &cacheConfigs(script_type type) {
        return type == LOCAL ? *_cache_configs_local : *_cache_configs_plugin;
    }
    retry_count_configs_t &retryConfigs(script_type type) {
        return type == LOCAL ? *_retry_configs_local : *_retry_configs_plugin;
    }
    execution_mode_configs_t &executionModeConfigs(script_type type) {
        return type == LOCAL ? *_execution_mode_configs_local
                             : *_execution_mode_configs_plugin;
    }

    winperf_counters_t &winperfCounters() { return *_winperf_counters; }
    only_from_t &onlyFrom() { return *_only_from; }
    execute_suffixes_t &executeSuffixes() { return *_execute_suffixes; }
    logwatch_textfiles_t &logwatchTextfiles() { return *_logwatch_textfiles; }

    void revalidateLogwatchTextfiles();

private:
    void readConfigFile(const std::string &filename);

    bool handleGlobalConfigVariable(char *var, char *value);
    bool handleWinperfConfigVariable(char *var, char *value);
    bool handleLogfilesConfigVariable(char *var, char *value);
    bool handleLogwatchConfigVariable(char *var, char *value);
    bool handleMrpeConfigVariable(char *var, char *value);
    bool handleFileinfoConfigVariable(char *var, char *value);
    bool handlePSConfigVariable(char *var, char *value);

    bool handlePluginConfigVariable(char *var, char *value);
    bool handleLocalConfigVariable(char *var, char *value);
    bool handleScriptConfigVariable(char *var, char *value, script_type type);

    bool parseBoolean(char *value, bool &parameter);
    void parseLogwatchStateLine(char *line);
    void parseExecute(char *value);
    void parseEventlogStateLine(char *line);

    void loadEventlogOffsets();
    void loadLogwatchOffsets();
    bool addNewLogwatchTextfile(const char *full_filename, glob_token *token,
                                condition_patterns_t &patterns);
    void updateOrCreateLogwatchTextfile(const char *full_filename,
                                        glob_token *token,
                                        condition_patterns_t &patterns);
    void processGlobExpression(glob_token *glob_token,
                               condition_patterns_t &patterns);
    void addGlobline(char *value);
    bool checkHostRestriction(char *patterns);

    int getCounterIdFromLang(const char *language, const char *counter_name);
    int getPerfCounterId(const char *counter_name);

    static void addConditionPattern(globline_container *&globline,
                                    const char *state, const char *value);

    // only-from needs to be initialised in two phases because it depends on
    // whether ipv6 is
    // supported
    void postProcessOnlyFrom();
    void addOnlyFrom(const char *value);
    void stringToIPv6(const char *value, uint16_t *address);
    void stringToIPv4(const char *value, uint32_t &address);
    void netmaskFromPrefixIPv6(int bits, uint16_t *netmask);
    void netmaskFromPrefixIPv4(int bits, uint32_t &netmask);

private:
    unsigned long _enabled_sections;
    unsigned long _realtime_sections;

    int _port;
    int _realtime_port;

    script_execution_mode _default_script_execution_mode;
    script_async_execution _default_script_async_execution;

    std::string _passphrase;
    int _realtime_timeout;

    bool _crash_debug;
    bool _section_flush;
    bool _logwatch_send_initial_entries;

    bool _support_ipv6;

    Environment _environment;

    bool _ps_use_wmi;
    bool _ps_full_path;

    // fileinfo
    ListCollector<fileinfo_paths_t, BlockMode::Nop<fileinfo_paths_t>,
                  AddMode::PriorityAppend<fileinfo_paths_t> >
        _fileinfo_paths;

    // plugins
    ListCollector<timeout_configs_t, BlockMode::Nop<timeout_configs_t>,
                  AddMode::PriorityAppend<timeout_configs_t> >
        _timeout_configs_local;
    ListCollector<timeout_configs_t, BlockMode::Nop<timeout_configs_t>,
                  AddMode::PriorityAppend<timeout_configs_t> >
        _timeout_configs_plugin;
    ListCollector<cache_configs_t, BlockMode::Nop<cache_configs_t>,
                  AddMode::PriorityAppend<cache_configs_t> >
        _cache_configs_local;
    ListCollector<cache_configs_t, BlockMode::Nop<cache_configs_t>,
                  AddMode::PriorityAppend<cache_configs_t> >
        _cache_configs_plugin;
    ListCollector<retry_count_configs_t, BlockMode::Nop<retry_count_configs_t>,
                  AddMode::PriorityAppend<retry_count_configs_t> >
        _retry_configs_local;
    ListCollector<retry_count_configs_t, BlockMode::Nop<retry_count_configs_t>,
                  AddMode::PriorityAppend<retry_count_configs_t> >
        _retry_configs_plugin;
    ListCollector<execution_mode_configs_t,
                  BlockMode::Nop<execution_mode_configs_t>,
                  AddMode::PriorityAppend<execution_mode_configs_t> >
        _execution_mode_configs_local;
    ListCollector<execution_mode_configs_t,
                  BlockMode::Nop<execution_mode_configs_t>,
                  AddMode::PriorityAppend<execution_mode_configs_t> >
        _execution_mode_configs_plugin;

    ListCollector<script_include_t> _script_includes;

    // mrpe
    ListCollector<mrpe_entries_t> _mrpe_entries;
    ListCollector<mrpe_include_t> _mrpe_includes;

    // global
    ListCollector<only_from_t, BlockMode::FileExclusive<only_from_t> >
        _only_from;
    ListCollector<execute_suffixes_t,
                  BlockMode::BlockExclusive<execute_suffixes_t> >
        _execute_suffixes;

    // winperf
    ListCollector<winperf_counters_t> _winperf_counters;

    // logfiles
    ListCollector<logwatch_textfiles_t> _logwatch_textfiles;
    // TODO: this is actually state, but it's only used during interpretation of
    // the configuration
    // files
    logwatch_textfiles_t _logwatch_hints;
    ListCollector<logwatch_globlines_t, BlockMode::Nop<logwatch_globlines_t>,
                  AddMode::PriorityAppendGrouped<logwatch_globlines_t> >
        _logwatch_globlines;

    // logwatch (eventlog = logwatch and logwatch = logfiles...)
    // Configuration of eventlog monitoring (see config parser).
    // Note: logwatch doesn't support real globbing, only * is supported as a
    // catch-all. The way
    // this is implemented now, a * in the second configuration file will
    // effectively replace everything from
    // the first configuration file
    ListCollector<eventlog_config_t, BlockMode::Nop<eventlog_config_t>,
                  AddMode::PriorityAppend<eventlog_config_t> >
        _eventlog_config;
};

#endif  // Configuration_h
