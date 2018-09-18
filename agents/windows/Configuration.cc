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

#include "Configuration.h"
#include <inttypes.h>
#include <simpleini/SimpleIni.h>
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <regex>
#include "Configurable.h"
#include "Logger.h"
#include "PerfCounter.h"
#include "stringutil.h"

#define __STDC_FORMAT_MACROS

namespace {

using Entry = CSimpleIniA::Entry;
using EntryPair = std::pair<Entry, Entry>;

bool checkHostRestriction(const std::string &hostname,
                          const std::string &input) {
    const auto patterns = tokenize(input, "\\s+");
    return std::any_of(
        patterns.cbegin(), patterns.cend(),
        [&hostname](const auto &p) { return globmatch(p, hostname); });
}

enum class CheckResult { Nop, Continue, Return };

inline CheckResult checkSpecialVariables(const std::string &variable,
                                         const std::string &hostname,
                                         const std::string &value) {
    if (variable == "host") {
        if (checkHostRestriction(hostname, value)) {
            return CheckResult::Continue;
        } else {
            return CheckResult::Return;
        }
    } else if (variable == "print") {
        std::cout << value << std::endl;
        return CheckResult::Continue;
    }

    return CheckResult::Nop;
}

bool assignVariable(const std::string &variable, const std::string &value,
                    ConfigurableVector &configurables) {
    bool found = false;

    for (auto &cfg : configurables) {
        try {
            cfg->feed(variable, value);
            found = true;
        } catch (const std::exception &e) {
            std::cerr << "Failed to interpret: " << e.what() << std::endl;
        }
    }

    return found;
}

bool valueLoadOrder(const EntryPair &e1, const EntryPair &e2) {
    return Entry::LoadOrder()(e1.second, e2.second);
};

std::vector<EntryPair> collectKeyValuePairs(const Entry &section,
                                            const CSimpleIni &ini) {
    CSimpleIniA::TNamesDepend keys;
    ini.GetAllKeys(section.pItem, keys);
    keys.sort(Entry::LoadOrder());
    std::vector<EntryPair> kvPairs;

    for (const auto &key : keys) {
        CSimpleIniA::TNamesDepend values;
        ini.GetAllValues(section.pItem, key.pItem, values);
        kvPairs.reserve(kvPairs.size() + values.size());
        std::transform(
            values.cbegin(), values.cend(), std::back_inserter(kvPairs),
            [&key](const Entry &value) { return std::make_pair(key, value); });
    }

    std::sort(kvPairs.begin(), kvPairs.end(), valueLoadOrder);

    return kvPairs;
}

void feedSection(const std::string &hostname, ConfigurableMap &configurables,
                 const Entry &section, const CSimpleIni &ini) {
    for (const auto &kvPair : collectKeyValuePairs(section, ini)) {
        std::string variable{kvPair.first.pItem};  // intentional copy
        std::transform(variable.cbegin(), variable.cend(), variable.begin(),
                       tolower);
        const std::string value{kvPair.second.pItem};

        switch (checkSpecialVariables(variable, hostname, value)) {
            case CheckResult::Continue:
                continue;
            case CheckResult::Return:
                return;
            default:;
        }

        const auto tokens = tokenize(variable, "\\s+");
        std::string sectionName{section.pItem};
        auto mapIt = configurables.find(ConfigKey(sectionName, tokens[0]));

        if (mapIt == configurables.end() ||
            !assignVariable(variable, value, mapIt->second)) {
            throw ParseError("Invalid entry (" + sectionName + ":" + variable +
                             ")");
        }
    }
}

}  // namespace

void Configuration::readSettings() {
    for (bool local : {false, true}) {
        for (const auto &cfg : _configurables) {
            for (auto &entry : cfg.second) {
                entry->startFile();
            }
        }
        const auto filename = configFileName(local, _environment);
        try {
            std::ifstream ifs(filename);
            readConfigFile(ifs, _environment.hostname(), _configurables);
        } catch (const ParseError &e) {
            std::cerr << e.what() << " in " << filename << std::endl;
            exit(1);
        }
    }
}

void Configuration::reg(const char *section, const char *key,
                        ConfigurableBase *cfg) {
    _configurables[std::pair<std::string, std::string>(section, key)].push_back(
        std::unique_ptr<ConfigurableBase>(cfg));
}

void Configuration::outputConfigurables(std::ostream &out) {
    using ConfigMap =
        std::map<std::string, std::reference_wrapper<ConfigurableBase>>;
    std::map<std::string, ConfigMap> config_map;

    for (const auto &kv : _configurables) {
        const auto &[section, key] = kv.first;
        if (config_map.find(section) == config_map.end()) {
            config_map[section] = {};
        }
        // this serializes only the first configurable registered under that
        // name,
        // if there are multiple with different mechanisms, this may be
        // confusing
        config_map[section].emplace(key, *kv.second[0]);
    }

    for (const auto &[section, keymap] : config_map) {
        out << "[" << section << "]\n";
        for (const auto &[key, config] : keymap) {
            config.get().output(key, out);
        }
    }
}

void readConfigFile(std::istream &is, const std::string &hostname,
                    ConfigurableMap &configurables) {
    if (!is) {
        return;
    }

    CSimpleIni ini(false, true);  // No UTF-8, multikey support
    auto res = ini.LoadData(is);

    if (res < 0) {
        switch (res) {
            case SI_Error::SI_FAIL:
                throw ParseError("Generic error");
            case SI_Error::SI_NOMEM:
                throw ParseError("Out of memory");
            case SI_Error::SI_FILE:
                throw ParseError(generic_error().what());
            default:;
        }
    }

    CSimpleIniA::TNamesDepend sections;
    ini.GetAllSections(sections);
    // Currently there is no need to sort the returned sections as section
    // configurations are handled independently and can be fed in any order.
    for (const auto &section : sections) {
        feedSection(hostname, configurables, section, ini);
    }
}
