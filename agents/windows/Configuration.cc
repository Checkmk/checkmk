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
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <regex>
#include "Configurable.h"
#include "PerfCounter.h"
#include "stringutil.h"

#define __STDC_FORMAT_MACROS

namespace {

bool checkHostRestriction(const std::string &hostname,
                          const std::string &input) {
    const auto patterns = tokenize(input, "\\s+");
    return std::any_of(patterns.cbegin(), patterns.cend(),
                       [&hostname](const auto &p) {
                           return globmatch(p.c_str(), hostname.c_str());
                       });
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
            std::cerr << e.what() << " line " << e.getLineNo() << " in "
                      << filename << std::endl;
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
        std::string section, key;
        tie(section, key) = kv.first;
        if (config_map.find(section) == config_map.end()) {
            config_map[section] = {};
        }
        // this serializes only the first configurable registered under that
        // name,
        // if there are multiple with different mechanisms, this may be
        // confusing
        config_map[section].emplace(key, *kv.second[0]);
    }

    for (const auto &section : config_map) {
        out << "[" << section.first << "]\n";
        for (const auto &keys : section.second) {
            keys.second.get().output(keys.first, out);
        }
    }
}

void readConfigFile(std::istream &is, const std::string &hostname,
                    ConfigurableMap &configurables) {
    if (!is) {
        return;
    }

    std::string line;
    bool is_active = true;  // false in sections with host restrictions
    std::string section;

    for (unsigned lineno = 1; std::getline(is, line); ++lineno) {
        ltrim(line);
        rtrim(line);
        if (line.empty() || line.front() == '#' || line.front() == ';')
            continue;  // skip empty lines and comments

        if (line.front() == '[' && line.back() == ']') {
            // found section header
            section = std::move(line.substr(1, line.size() - 2));
            // forget host-restrictions if new section begins
            is_active = true;
        } else {
            // split up line at = sign
            const auto tokens = tokenize(line, "=");
            if (tokens.size() != 2) {
                throw ParseError("Invalid", lineno);
            }
            std::string variable{tokens[0]};
            rtrim(variable);
            std::transform(variable.cbegin(), variable.cend(), variable.begin(),
                           tolower);
            std::string value{tokens[1]};
            ltrim(value);
            rtrim(value);

            // handle host restriction
            if (variable == "host")
                is_active = checkHostRestriction(hostname, value);

            // skip all other variables for non-relevant hosts
            else if (!is_active)
                continue;

            // Useful for debugging host restrictions
            else if (variable == "print")
                std::cerr << value << std::endl;

            else {
                bool found = false;
                size_t key_len = strcspn(variable.c_str(), " \n");
                auto map_iter = configurables.find(
                    ConfigKey(section, std::string(variable, 0, key_len)));
                if (map_iter != configurables.end()) {
                    for (auto &cfg : map_iter->second) {
                        try {
                            cfg->feed(variable, value);
                            found = true;
                        } catch (const std::exception &e) {
                            std::cerr << "Failed to interpret " << line << ": "
                                      << e.what() << std::endl;
                        }
                    }
                }
                if (!found) {
                    throw ParseError(
                        "Invalid entry (" + section + ":" + variable + ")",
                        lineno);
                }
            }
        }
    }
}
