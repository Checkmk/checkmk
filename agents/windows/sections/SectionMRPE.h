// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
mrpe_entry from_string<mrpe_entry>(const WinApiInterface &,
                                   const std::string &value);

class SectionMRPE : public Section {
public:
    SectionMRPE(Configuration &config, Logger *logger,
                const WinApiInterface &winapi);

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
