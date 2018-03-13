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

#ifndef SectionMRPE_h
#define SectionMRPE_h

#include "Configurable.h"
#include "Section.h"

// Command definitions for MRPE
struct mrpe_entry {
    mrpe_entry(const std::string run_as_user_, const std::string command_line_,
               const std::string &plugin_name_,
               const std::string &service_description_)
        : run_as_user(run_as_user_)
        , command_line(command_line_)
        , plugin_name(plugin_name_)
        , service_description(service_description_) {}
    std::string run_as_user;
    std::string command_line;
    std::string plugin_name;
    std::string service_description;
};

inline std::ostream &operator<<(std::ostream &os, const mrpe_entry &entry) {
    os << "(" << entry.plugin_name << ") " << entry.service_description;
    return os;
}

using mrpe_entries_t = std::vector<mrpe_entry>;

template <>
mrpe_entry from_string<mrpe_entry>(const WinApiAdaptor &,
                                   const std::string &value);

class SectionMRPE : public Section {
public:
    SectionMRPE(Configuration &config, Logger *logger,
                const WinApiAdaptor &winapi);

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    void updateIncludes();

    ListConfigurable<mrpe_entries_t> _entries;
    KeyedListConfigurable<std::string> _includes;
    mrpe_entries_t _included_entries;
};

#endif  // SectionMRPE_h
