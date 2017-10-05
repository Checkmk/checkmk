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

#include "SectionCheckMK.h"
#include "../Environment.h"
#include "../stringutil.h"
#include <vector>
#include <string>


extern const char *check_mk_version;
extern const char *g_connection_log;
extern const char *g_crash_log;
extern const char *g_success_log;

struct script_statistics_t {
    int pl_count;
    int pl_errors;
    int pl_timeouts;
    int lo_count;
    int lo_errors;
    int lo_timeouts;
} g_script_stat;


SectionCheckMK::SectionCheckMK(Configuration &config, const Environment &env)
    : Section("check_mk", "check_mk")
    , _crash_debug(config, "global", "crash_debug", false)
    , _only_from(config, "global", "only_from")
{
#ifdef ENVIRONMENT32
    const char *arch = "32bit";
#else
    const char *arch = "64bit";
#endif

    // common fields
    _info_fields = {
        KVPair("Version", check_mk_version),                                  //
        KVPair("BuildDate", __DATE__),                                        //
        KVPair("AgentOS", "windows"),                                         //
        KVPair("Hostname", env.hostname()),                                   //
        KVPair("Architecture", arch),                                         //
        KVPair("WorkingDirectory", env.currentDirectory()),                   //
        KVPair("ConfigFile", Configuration::configFileName(false, env)),      //
        KVPair("LocalConfigFile", Configuration::configFileName(true, env)),  //
        KVPair("AgentDirectory", env.agentDirectory()),                       //
        KVPair("PluginsDirectory", env.pluginsDirectory()),                   //
        KVPair("StateDirectory", env.stateDirectory()),                       //
        KVPair("ConfigDirectory", env.configDirectory()),                     //
        KVPair("TempDirectory", env.tempDirectory()),                         //
        KVPair("LogDirectory", env.logDirectory()),                           //
        KVPair("SpoolDirectory", env.spoolDirectory()),                       //
        KVPair("LocalDirectory", env.localDirectory())                        //
    };

    if (*_crash_debug) {
        _info_fields.push_back(KVPair("ConnectionLog", g_connection_log));
        _info_fields.push_back(KVPair("CrashLog", g_crash_log));
        _info_fields.push_back(KVPair("SuccessLog", g_success_log));
    }
}

bool SectionCheckMK::produceOutputInner(std::ostream &out,
                                        const Environment&) {

    // output static fields
    for (const auto &kv : _info_fields) {
        out << kv.first << ": " << kv.second << "\n";
    }

    out << "ScriptStatistics:"
        << " Plugin"
        << " C:" << g_script_stat.pl_count
        << " E:" << g_script_stat.pl_errors
        << " T:" << g_script_stat.pl_timeouts
        << " Local"
        << " C:" << g_script_stat.lo_count
        << " E:" << g_script_stat.lo_errors
        << " T:" << g_script_stat.lo_timeouts
        << "\n";

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
                out << " "
                    << (is->ip.v4.address & 0xff) << "."
                    << (is->ip.v4.address >> 8 & 0xff) << "."
                    << (is->ip.v4.address >> 16 & 0xff) << "."
                    << (is->ip.v4.address >> 24 & 0xff) << "/" << is->bits;
            }
        }
    }
    return true;
}

