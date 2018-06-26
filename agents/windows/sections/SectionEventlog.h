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

#include "Configurable.h"
#include "EventLog.h"
#include "Section.h"

class WinApiInterface;

namespace eventlog {

enum class Level { Off = -1, All, Warn, Crit };

std::ostream &operator<<(std::ostream &os, const Level &l);

// Configuration entries from [logwatch] for individual logfiles
struct config {
    config(const std::string &name, Level level, bool hide_context)
        : name(name)
        , level(level)
        , hide_context(hide_context) {}

    std::string name;
    Level level;
    bool hide_context;
};

std::ostream &operator<<(std::ostream &out, const config &val);

// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far.
struct state {
    state(const std::string &name_, uint64_t record_no_ = 0,
          bool newly_discovered_ = true)
        : name(name_)
        , record_no(record_no_)
        , newly_discovered(newly_discovered_) {}
    std::string name;
    uint64_t record_no;
    bool newly_discovered;
};

using Configs = std::vector<config>;
using States = std::vector<state>;

class Configurable : public ListConfigurable<Configs, BlockMode::Nop<Configs>,
                                             AddMode::PriorityAppend<Configs>> {
    using SuperT = ListConfigurable<Configs, BlockMode::Nop<Configs>,
                                    AddMode::PriorityAppend<Configs>>;

public:
    Configurable(Configuration &config, const char *section, const char *key,
                 const WinApiInterface &winapi)
        : SuperT(config, section, key, winapi) {}

    virtual void feed(const std::string &var,
                      const std::string &value) override;
};

}  // namespace eventlog

eventlog::state parseStateLine(const std::string &line);

std::optional<std::string> getIPSpecificStatefileName(
    const Environment &env, const std::optional<std::string> &remoteIP);

using FindResult = std::pair<DWORD, std::string>;

class SectionEventlog : public Section {
public:
    SectionEventlog(Configuration &config, Logger *logger,
                    const WinApiInterface &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &remoteIP) override;

private:
    uint64_t outputEventlog(std::ostream &out, EventLogBase &log,
                            uint64_t previouslyReadId, eventlog::Level level,
                            bool hideContext);
    FindResult findLog(const HKeyHandle &hKey, DWORD index) const;
    void registerAdditionalEventlogs(eventlog::States &states);
    bool find_eventlogs(std::ostream &out, eventlog::States &states);
    void saveEventlogOffsets(const std::string &statefile,
                             const eventlog::States &states);
    std::pair<eventlog::Level, bool> readConfig(
        const eventlog::state &state) const;
    std::unique_ptr<EventLogBase> openEventlog(const std::string &logname,
                                               std::ostream &out) const;
    void handleExistingLog(std::ostream &out, eventlog::state &state);

    Configurable<bool> _sendall;
    Configurable<bool> _vista_api;
    eventlog::Configurable _config;
};

#endif  // SectionEventlog_h
