// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionCheckMK.h"

#include <cstring>
#include <iterator>
#include <string>
#include <vector>

#include "Environment.h"
#include "Logger.h"
#include "SectionHeader.h"
#include "stringutil.h"

namespace {

std::vector<KVPair> createInfoFields(const Environment &env) {
#ifdef ENVIRONMENT32
    const char *arch = "32bit";
#else
    const char *arch = "64bit";
#endif

    // common fields
    std::vector<KVPair> info_fields = {
        {"Version", CHECK_MK_VERSION},
        {"BuildDate", __DATE__},
        {"AgentOS", "windows"},
        {"Hostname", env.hostname()},
        {"Architecture", arch},
        {"WorkingDirectory", env.currentDirectory()},
        {"ConfigFile", configFileName(false, env)},
        {"LocalConfigFile", configFileName(true, env)},
        {"AgentDirectory", env.agentDirectory()},
        {"PluginsDirectory", env.pluginsDirectory()},
        {"StateDirectory", env.stateDirectory()},
        {"ConfigDirectory", env.configDirectory()},
        {"TempDirectory", env.tempDirectory()},
        {"LogDirectory", env.logDirectory()},
        {"SpoolDirectory", env.spoolDirectory()},
        {"LocalDirectory", env.localDirectory()}};

    return info_fields;
}

}  // namespace

SectionCheckMK::SectionCheckMK(Configuration &config,
                               OnlyFromConfigurable &only_from,
                               script_statistics_t &script_statistics,
                               Logger *logger, const WinApiInterface &winapi)
    : Section("check_mk", config.getEnvironment(), logger, winapi,
              std::make_unique<DefaultHeader>("check_mk", logger))
    , _crash_debug(config, "global", "crash_debug", false, winapi)
    , _only_from(only_from)
    , _info_fields(createInfoFields(_env))
    , _script_statistics(script_statistics) {}

extern std::string g_only_from_as_text;

bool SectionCheckMK::produceOutputInner(std::ostream &out,
                                        const std::optional<std::string> &) {
    Debug(_logger) << "SectionCheckMK::produceOutputInner";
    // output static fields
    for (const auto &[label, value] : _info_fields) {
        out << label << ": " << value << "\n";
    }

    out << "ScriptStatistics:"
        << " Plugin"
        << " C:" << _script_statistics["plugin_count"]
        << " E:" << _script_statistics["plugin_errors"]
        << " T:" << _script_statistics["plugin_timeouts"] << " Local"
        << " C:" << _script_statistics["local_count"]
        << " E:" << _script_statistics["local_errors"]
        << " T:" << _script_statistics["local_timeouts"] << "\n";

    // reset script statistics for next round
    _script_statistics.reset();

    out << "OnlyFrom: " << g_only_from_as_text << "\n";
    // only from, isn't this static too?
#if 0
    // code no more good for the Check MK
    if (_only_from->empty()) {
        out << " 0.0.0.0/0\n";
    } else {
        for (const auto &is : *_only_from) {
            out << " " << is;
        }
    }
#endif
    return true;
}
