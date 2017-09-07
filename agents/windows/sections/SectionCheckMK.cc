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

#include "SectionCheckMK.h"
#include <cstring>
#include <iterator>
#include <string>
#include <vector>
#include "../Environment.h"
#include "../Logger.h"
#include "../stringutil.h"

extern const char *check_mk_version;

struct script_statistics_t {
    int pl_count;
    int pl_errors;
    int pl_timeouts;
    int lo_count;
    int lo_errors;
    int lo_timeouts;
} g_script_stat;

SectionCheckMK::SectionCheckMK(Configuration &config, Logger *logger,
                               const WinApiAdaptor &winapi)
    : Section("check_mk", config.getEnvironment(), logger, winapi)
    , _crash_debug(config, "global", "crash_debug", false, winapi)
    , _only_from(config, "global", "only_from", winapi)
    , _info_fields(createInfoFields()) {}

std::vector<KVPair> SectionCheckMK::createInfoFields() const {
#ifdef ENVIRONMENT32
    const char *arch = "32bit";
#else
    const char *arch = "64bit";
#endif

    // common fields
    std::vector<KVPair> info_fields = {
        {"Version", check_mk_version},
        {"BuildDate", __DATE__},
        {"AgentOS", "windows"},
        {"Hostname", _env.hostname()},
        {"Architecture", arch},
        {"WorkingDirectory", _env.currentDirectory()},
        {"ConfigFile", Configuration::configFileName(false, _env)},
        {"LocalConfigFile", Configuration::configFileName(true, _env)},
        {"AgentDirectory", _env.agentDirectory()},
        {"PluginsDirectory", _env.pluginsDirectory()},
        {"StateDirectory", _env.stateDirectory()},
        {"ConfigDirectory", _env.configDirectory()},
        {"TempDirectory", _env.tempDirectory()},
        {"LogDirectory", _env.logDirectory()},
        {"SpoolDirectory", _env.spoolDirectory()},
        {"LocalDirectory", _env.localDirectory()}};

    return info_fields;
}

bool SectionCheckMK::produceOutputInner(std::ostream &out) {
    // output static fields
    for (const auto &kv : _info_fields) {
        out << kv.first << ": " << kv.second << "\n";
    }

    out << "ScriptStatistics:"
        << " Plugin"
        << " C:" << g_script_stat.pl_count << " E:" << g_script_stat.pl_errors
        << " T:" << g_script_stat.pl_timeouts << " Local"
        << " C:" << g_script_stat.lo_count << " E:" << g_script_stat.lo_errors
        << " T:" << g_script_stat.lo_timeouts << "\n";

    // reset script statistics for next round
    memset(&g_script_stat, 0, sizeof(g_script_stat));

    out << "OnlyFrom:";
    // only from, isn't this static too?
    if (_only_from->size() == 0) {
        out << " 0.0.0.0/0\n";
    } else {
        for (const ipspec *is : *_only_from) {
            if (is->ipv6) {
                out << " "
                    << join(is->ip.v6.address, is->ip.v6.address + 7, ":")
                    << "/" << is->bits;
            } else {
                out << " " << (is->ip.v4.address & 0xff) << "."
                    << (is->ip.v4.address >> 8 & 0xff) << "."
                    << (is->ip.v4.address >> 16 & 0xff) << "."
                    << (is->ip.v4.address >> 24 & 0xff) << "/" << is->bits;
            }
        }
    }
    return true;
}
