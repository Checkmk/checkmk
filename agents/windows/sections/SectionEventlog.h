// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

#ifndef SectionEventlog_h
#define SectionEventlog_h

#include "../Configurable.h"
#include "../Configuration.h"
#include "../EventLog.h"
#include "../Section.h"
#include "../types.h"

class WinApiAdaptor;

class EventlogConfigurable
    : public ListConfigurable<eventlog_config_t,
                              BlockMode::Nop<eventlog_config_t>,
                              AddMode::PriorityAppend<eventlog_config_t>> {
    typedef ListConfigurable<eventlog_config_t,
                             BlockMode::Nop<eventlog_config_t>,
                             AddMode::PriorityAppend<eventlog_config_t>>
        SuperT;

public:
    EventlogConfigurable(Configuration &config, const char *section,
                         const char *key, const WinApiAdaptor &winapi)
        : SuperT(config, section, key, winapi) {}
    virtual void feed(const std::string &var,
                      const std::string &value) override {
        eventlog_config_entry entry =
            from_string<eventlog_config_entry>(_winapi, value);
        std::istringstream str(var);
        std::string key;
        getline(str, key, ' ');
        getline(str, entry.name, ' ');
        entry.vista_api = (key == "logname");
        add(entry);
    }
};

class SectionEventlog : public Section {
    Configurable<bool> _send_initial;
    Configurable<bool> _vista_api;

    EventlogConfigurable _config;

    eventlog_hints_t _hints;
    eventlog_state_t _state;
    bool _records_loaded = false;
    bool _first_run = true;

public:
    SectionEventlog(Configuration &config, Logger *logger,
                    const WinApiAdaptor &winapi);
    virtual ~SectionEventlog();

    virtual void postprocessConfig() override;

protected:
    virtual bool produceOutputInner(std::ostream &out) override;

private:
    void outputEventlog(std::ostream &out, const char *logname,
                        uint64_t &first_record, int level, int hide_context);
    void registerEventlog(const char *logname);
    bool find_eventlogs(std::ostream &out);
    void parseStateLine(char *line);
    void loadEventlogOffsets(const std::string &statefile);
    void saveEventlogOffsets(const std::string &statefile);
    void process_eventlog_entry(std::ostream &out, const IEventLog &event_log,
                                const IEventLogRecord &event, int level,
                                int hide_context);
};

#endif  // SectionEventlog_h
