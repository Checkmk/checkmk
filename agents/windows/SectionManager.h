// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

#ifndef SectionManager_h
#define SectionManager_h

#include <set>
#include "Configurable.h"
#include "Configuration.h"
#include "Section.h"

std::ostream &operator<<(std::ostream &out,
                         const std::pair<std::string, std::string> &value);

class SectionManager {
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

    ListConfigurable<std::vector<winperf_counter *>> _winperf_counters;

    void addSection(Section *section);
    void loadStaticSections(Configuration &config, const Environment &env);

public:
    SectionManager(Configuration &config, const Environment &env);
    ~SectionManager() { _sections.clear(); }

    void emitConfigLoaded(const Environment &env);
    void loadDynamicSections();
    const std::vector<std::unique_ptr<Section>> &sections() const {
        return _sections;
    }

    bool sectionEnabled(const std::string &name) const;
    bool realtimeSectionEnabled(const std::string &name) const;
    bool useRealtimeMonitoring() const;
};

#endif  // SectionManager_h
