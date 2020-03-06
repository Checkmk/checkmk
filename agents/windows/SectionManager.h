// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionManager_h
#define SectionManager_h

#include <set>
#include "Configurable.h"
#include "Section.h"

class Configuration;
class Environment;
class Logger;
class WinApiInterface;

// Configuration for section [winperf]
struct winperf_counter {
    winperf_counter(int id_, const std::string &name_) : id(id_), name(name_) {}
    int id;
    std::string name;
};

inline std::ostream &operator<<(std::ostream &out, const winperf_counter &wpc) {
    return out << "(id = " << wpc.id << ", name = " << wpc.name << ")";
}

template <>
winperf_counter from_string<winperf_counter>(const WinApiInterface &winapi,
                                             const std::string &value);

std::ostream &operator<<(std::ostream &out,
                         const std::pair<std::string, std::string> &value);

using OnlyFromConfigurable =
    SplittingListConfigurable<only_from_t,
                              BlockMode::FileExclusive<only_from_t>>;

class SectionManager {
public:
    SectionManager(Configuration &config, OnlyFromConfigurable &only_from,
                   Logger *logger, const WinApiInterface &winapi);

    void emitConfigLoaded();
    void loadDynamicSections();
    const std::vector<std::unique_ptr<Section>> &sections() const {
        return _sections;
    }

    bool sectionEnabled(const std::string &name) const;
    bool realtimeSectionEnabled(const std::string &name) const;
    bool useRealtimeMonitoring() const;

private:
    void addSection(Section *section);
    void loadStaticSections(Configuration &config,
                            OnlyFromConfigurable &only_from);

    std::vector<std::unique_ptr<Section>> _sections;
    Configurable<bool> _ps_use_wmi;
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _enabled_sections;
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _disabled_sections;
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _realtime_sections;
    KeyedListConfigurable<std::string> _script_local_includes;
    KeyedListConfigurable<std::string> _script_plugin_includes;
    ListConfigurable<std::vector<winperf_counter>> _winperf_counters;
    script_statistics_t _script_statistics;
    const Environment &_env;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

#endif  // SectionManager_h
