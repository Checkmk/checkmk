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
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <regex>
#include "Configurable.h"
#include "Environment.h"
#include "PerfCounter.h"
#include "stringutil.h"

#define __STDC_FORMAT_MACROS

Configuration::Configuration(const Environment &env) : _environment(env) {}

Configuration::~Configuration() {}

void Configuration::readSettings() {
    for (const auto &cfg : _configurables) {
        for (auto entry : cfg.second) {
            entry->startFile();
        }
    }

    readConfigFile(configFileName(false, _environment));

    for (const auto &cfg : _configurables) {
        for (auto entry : cfg.second) {
            entry->startFile();
        }
    }

    readConfigFile(configFileName(true, _environment));
}

void Configuration::reg(const char *section, const char *key,
                        ConfigurableBase *cfg) {
    _configurables[std::pair<std::string, std::string>(section, key)].push_back(
        cfg);
}

void Configuration::deregister(const char *section, const char *key,
                               ConfigurableBase *cfg) {
    auto map_iter =
        _configurables.find(std::pair<std::string, std::string>(section, key));
    if (map_iter != _configurables.end()) {
        for (auto iter = map_iter->second.begin();
             iter != map_iter->second.end(); ++iter) {
            if (cfg == *iter) {
                map_iter->second.erase(iter);
                break;
            }
        }
    }
    // if there is nothing to deregister that is actually a usage error
}

std::string Configuration::configFileName(bool local, const Environment &env) {
    return std::string(env.agentDirectory()) + "\\" + "check_mk" +
           (local ? "_local" : "") + ".ini";
}

bool Configuration::checkHostRestriction(char *patterns) {
    char *word;
    std::string hostname = _environment.hostname();
    while ((word = next_word(&patterns))) {
        if (globmatch(word, hostname.c_str())) {
            return true;
        }
    }
    return false;
}

void Configuration::outputConfigurables(std::ostream &out) {
    std::map<std::string, std::map<std::string, ConfigurableBase *>> config_map;

    for (const auto &kv : _configurables) {
        std::string section, key;
        tie(section, key) = kv.first;
        if (config_map.find(section) == config_map.end()) {
            config_map[section] = std::map<std::string, ConfigurableBase *>();
        }
        // this serializes only the first configurable registered under that
        // name,
        // if there are multiple with different mechanisms, this may be
        // confusing
        config_map[section][key] = kv.second[0];
    }

    for (const auto &section : config_map) {
        out << "[" << section.first << "]\n";
        for (const auto &keys : section.second) {
            keys.second->output(keys.first, out);
        }
    }
}

void Configuration::readConfigFile(const std::string &filename) {
    FILE *file = fopen(filename.c_str(), "r");
    if (!file) {
        return;
    }

    char line[512];
    int lineno = 0;

    bool is_active = true;  // false in sections with host restrictions

    std::string section;
    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)) {
            fclose(file);
            return;
        }
        lineno++;
        char *l = strip(line);
        if (l[0] == 0 || l[0] == '#' || l[0] == ';')
            continue;  // skip empty lines and comments
        int len = strlen(l);
        if (l[0] == '[' && l[len - 1] == ']') {
            // found section header
            l[len - 1] = 0;
            section = l + 1;
            // forget host-restrictions if new section begins
            is_active = true;
        } else {
            // split up line at = sign
            char *s = l;
            while (*s && *s != '=') s++;
            if (*s != '=') {
                fprintf(stderr, "Invalid line %d in %s.\r\n", lineno,
                        filename.c_str());
                exit(1);
            }
            *s = 0;
            char *value = s + 1;
            char *variable = l;
            rstrip(variable);
            lowercase(variable);
            value = strip(value);

            // handle host restriction
            if (!strcmp(variable, "host"))
                is_active = checkHostRestriction(value);

            // skip all other variables for non-relevant hosts
            else if (!is_active)
                continue;

            // Useful for debugging host restrictions
            else if (!strcmp(variable, "print"))
                fprintf(stderr, "%s\r\n", value);

            else {
                bool found = false;
                size_t key_len = strcspn(variable, " \n");

                auto map_iter = _configurables.find(
                    config_key(section, std::string(variable, key_len)));
                if (map_iter != _configurables.end()) {
                    for (auto cfg : map_iter->second) {
                        try {
                            cfg->feed(variable, value);
                            found = true;
                        } catch (const std::exception &e) {
                            fprintf(stderr, "Failed to interpret %s: %s\n",
                                    line, e.what());
                        }
                    }
                }
                if (!found) {
                    fprintf(stderr, "Invalid entry (%s:%s) in %s line %d.\r\n",
                            section.c_str(), variable, filename.c_str(),
                            lineno);
                    exit(1);
                }
            }
        }
    }

    fclose(file);
}
