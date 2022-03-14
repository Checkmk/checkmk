// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "Configuration.h"

#include <inttypes.h>
#include <ws2spi.h>

#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <regex>

#include "Configurable.h"
#include "Logger.h"
#define memmove MemMove
void MemMove(void *dst, const void *src, size_t count);
#include "SimpleIni.h"
#undef memmove

#include "cfg.h"
#include "cvt.h"
#include "stringutil.h"
#include "types.h"

#define __STDC_FORMAT_MACROS
namespace fs = std::filesystem;

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
            cfg->changed();
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
                                            const CSimpleIniA &ini) {
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

bool feedSection(const std::string &hostname, ConfigurableMap &configurables,
                 const Entry &section, const CSimpleIniA &ini) {
    for (const auto &kvPair : collectKeyValuePairs(section, ini)) {
        std::string variable{kvPair.first.pItem};  // intentional copy
        std::transform(variable.cbegin(), variable.cend(), variable.begin(),
                       tolower);
        const std::string value{kvPair.second.pItem};

        // we do not check for special VALUE

        const auto tokens = tokenize(variable, "\\s+");
        std::string sectionName{section.pItem};
        auto mapIt = configurables.find(ConfigKey(sectionName, tokens[0]));

        if (mapIt == configurables.end() ||
            !assignVariable(variable, value, mapIt->second)) {
            XLOG::l("Invalid entry (" + sectionName + ":" + variable + ")");
            continue;
        }
    }

    return true;
}

}  // namespace

bool Configuration::ReadSettings(const std::filesystem::path &Path,
                                 bool Local) noexcept {
    try {
        for (const auto &cfg : _configurables) {
            for (auto &entry : cfg.second) {
                entry->startFile();
            }
        }
        const auto filename = Path.u8string();
        std::ifstream ifs(filename);
        return readConfigFile(ifs, cma::cfg::GetHostName(), _configurables);
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + "Smart exception '{}'", e.what());
    } catch (...) {
        XLOG::l(XLOG_FLINE + "Stupid exception");
    }

    return false;
}

void Configuration::reg(const char *section, const char *key,
                        ConfigurableBase *cfg) {
    _configurables[std::pair<std::string, std::string>(section, key)].push_back(
#if defined(USE_UNIQUE_PTR_WITHOUT_UNDERSTANDING_WHAT_UNIQUE_MEANS)
        std::unique_ptr<ConfigurableBase>(cfg)
#else
        cfg
#endif
    );
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

void Configuration::outputConfigurables(
    std::function<void(const std::string, const std::string, const std::string,
                       const std::string)>
        Sink) {
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

    std::string mrpe_out;
    for (const auto &[section, keymap] : config_map) {
        for (const auto &[key, config] : keymap) {
            auto &v = config.get();
            if (!v.isChanged()) continue;

            if (cma::tools::IsEqual(section, "mrpe")) {
                // we only gathering entries here
                if (cma::tools::IsEqual(key, "include")) {
                    auto arr = v.generateKeys();
                    for (auto &entry : arr) {
                        std::string out;
                        if (entry.first.size())
                            out += "- include " + entry.first + " = " +
                                   entry.second + "\n";
                        else
                            out += "- include = " + entry.second + "\n";
                        cma::cfg::ReplaceInString(
                            out, wtools::ToUtf8(cma::cfg::GetUserDir()),
                            cma::cfg::vars::kProgramDataFolder);
                        mrpe_out += out;
                    }
                } else if (cma::tools::IsEqual(key, "check")) {
                    mrpe_out += v.outputForYaml();
                }
                continue;
            }

            if (cma::tools::IsEqual(section, "logwatch") ||
                cma::tools::IsEqual(section, "logfiles")) {
                Sink(section, key, v.outputForYaml(), v.iniString());
                continue;
            }

            if (cma::tools::IsEqual(section, "global")) {
                if (cma::tools::IsEqual(key, "disabled_sections") ||
                    cma::tools::IsEqual(key, "realtime_sections") ||
                    cma::tools::IsEqual(key, "sections") ||
                    cma::tools::IsEqual(key, "execute") ||
                    cma::tools::IsEqual(key, "only_from")) {
                    auto value = v.outputAsInternalArray();
                    Sink(section, key, "", value);
                    continue;
                }
            }

            if (!v.isKeyed()) {
                Sink(section, key, v.outputForYaml(), v.iniString());
                continue;
            }

            // keyed
            // plugins & local
            auto arr = v.generateKeys();
            for (auto &entry : arr) {
                if (cma::tools::IsEqual(key, "execution"))
                    Sink(section, cma::cfg::vars::kPluginAsync,
                         entry.second == "1" ? "yes" : "no", entry.first);
                else
                    Sink(section, key, entry.second, entry.first);
            }
        }
    }
    if (!mrpe_out.empty())
        Sink(cma::cfg::groups::kMrpe.data(), cma::cfg::vars::kMrpeConfig,
             mrpe_out, "");
}

bool readConfigFile(std::istream &is, const std::string &hostname,
                    ConfigurableMap &configurables) {
    if (!is) {
        return false;
    }

    CSimpleIniA ini(false, true);  // No UTF-8, multikey support
    auto res = ini.LoadData(is);

    if (res < 0) {
        switch (res) {
            case SI_Error::SI_FAIL:
                XLOG::l("Generic error");
            case SI_Error::SI_NOMEM:
                XLOG::l("Out of memory");
            case SI_Error::SI_FILE:
                XLOG::l("generic_error().what()");
            default:;
        }
        return false;
    }

    CSimpleIniA::TNamesDepend sections;
    ini.GetAllSections(sections);
    // Currently there is no need to sort the returned sections as section
    // configurations are handled independently and can be fed in any order.
    for (const auto &section : sections) {
        feedSection(hostname, configurables, section, ini);
    }

    return true;
}

namespace eventlog {

enum class Level { Off = -1, All, Warn, Crit };

std::ostream &operator<<(std::ostream &os, const Level &l);

// Configuration entries from [logwatch] for individual logfiles
struct config {
    config(const std::string &name, Level level, bool hide_context)
        : name(name), level(level), hide_context(hide_context) {}

    std::string name;
    Level level;
    bool hide_context;
};

std::ostream &operator<<(std::ostream &out, const config &val);

// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far.
struct state {
    state(const std::string &name_, uint64_t record_no_ = 0,
          bool newly_discovered_ = true)
        : name(name_)
        , record_no(record_no_)
        , newly_discovered(newly_discovered_) {}
    std::string name;
    uint64_t record_no;
    bool newly_discovered;
};
}  // namespace eventlog

namespace eventlog {

using Configs = std::vector<config>;
using States = std::vector<state>;

class Configurable : public ListConfigurable<Configs, BlockMode::Nop<Configs>,
                                             AddMode::PriorityAppend<Configs>> {
    using SuperT = ListConfigurable<Configs, BlockMode::Nop<Configs>,
                                    AddMode::PriorityAppend<Configs>>;

public:
    Configurable(Configuration &config, const char *section, const char *key)
        : SuperT(config, section, key) {}

    virtual void feed(const std::string &var,
                      const std::string &value) override;
};
}  // namespace eventlog

template <>
eventlog::config from_string<eventlog::config>(const std::string &value) {
    // this parses only what's on the right side of the = in the
    // configuration file
    std::stringstream str(value);

    bool hide_context = false;
    eventlog::Level level{eventlog::Level::All};

    std::string entry;
    while (std::getline(str, entry, ' ')) {
        if (entry == "nocontext")
            hide_context = true;
        else if (entry == "off")
            level = eventlog::Level::Off;
        else if (entry == "all")
            level = eventlog::Level::All;
        else if (entry == "warn")
            level = eventlog::Level::Warn;
        else if (entry == "crit")
            level = eventlog::Level::Crit;
        else {
            XLOG::l() << "Invalid log level '" << entry << "'."
                      << "\n"
                      << "Allowed are off, all, warn and crit.";
        }
    }

    return eventlog::config("", level, hide_context);
}

template <>
std::string ToYamlString(const eventlog::config &Entry, bool) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;

    std::string out = "- '";
    out += Entry.name;
    out += "': ";

    // convert LWA::eventlog::Level to cma:cfg::EventLevels
    auto event_level = EventLevels::kOff;

    switch (Entry.level) {
        case eventlog::Level::All:
            event_level = EventLevels::kAll;
            break;
        case eventlog::Level::Warn:
            event_level = EventLevels::kWarn;
            break;
        case eventlog::Level::Crit:
            event_level = EventLevels::kCrit;
            break;
        case eventlog::Level::Off:
            event_level = EventLevels::kOff;
            break;
    }

    // now we can obtain text representation for YML
    out += ConvertLogWatchLevelToString(event_level);

    out += Entry.hide_context ? " nocontext" : " context";
    return out;
}

template <>
std::string ToYamlString(const globline_container &Entry, bool) {
    namespace fs = std::filesystem;

    std::string out = "- glob: '";
    out += Entry.tokens[0].from_start ? "from_start " : "";
    out += Entry.tokens[0].rotated ? "rotated " : "";
    out += Entry.tokens[0].nocontext ? "nocontext " : "";
    out += "= ";

    for (auto &t : Entry.tokens) {
        out += t.pattern;
        out += "|";
    }
    out.pop_back();
    out += "'\n";

    out += "  pattern:";
    for (auto &p : Entry.patterns) {
        out += " ";
        out += p.state;
        out += " = ";
        out += "'";
        out += p.glob_pattern;
        out += "'";
    }
    if (Entry.patterns.size() == 0) out += " ~";

    return out;
}

namespace eventlog {
inline std::ostream &operator<<(std::ostream &os, const Level &l) {
    switch (l) {
        case Level::Off:
            return os << "off";
        case Level::All:
            return os << "all";
        case Level::Warn:
            return os << "warn";
        case Level::Crit:
            return os << "crit";
        default:
            return os << "invalid";
    }
}

std::ostream &operator<<(std::ostream &out, const config &val) {
    out << val.name << " = ";
    if (val.hide_context) {
        out << "nocontext ";
    }
    out << val.level;
    return out;
}

void Configurable::feed(const std::string &var, const std::string &value) {
    config entry = from_string<config>(value);
    const auto tokens = tokenize(var, " ");

    if (tokens.size() < 2) {
        XLOG::l() << "Invalid eventlog logname entry: '" << var << "'";
    }

    entry.name = join(std::next(tokens.cbegin()), tokens.cend(), " ");
    add(entry);
}

}  // namespace eventlog

class GlobListConfigurable
    : public ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                              AddMode::PriorityAppendGrouped<GlobListT>> {
    using SuperT = ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                                    AddMode::PriorityAppendGrouped<GlobListT>>;

public:
    GlobListConfigurable(Configuration &config, const char *section)
        : SuperT(config, section, "textfile") {
        config.reg(section, "warn", this);
        config.reg(section, "crit", this);
        config.reg(section, "ignore", this);
        config.reg(section, "ok", this);
    }

    virtual void feed(const std::string &key,
                      const std::string &value) override {
        if (key == "textfile") {
            SuperT::feed(key, value);
        } else {
            SuperT::feedInner(key, value);
        }
    }
};

namespace cma::cfg::cvt {
bool supportIPv6() {
    INT iNuminfo = 0;
    DWORD bufferSize = 0;
    std::vector<BYTE> protocolInfo;
    INT iErrno = NO_ERROR;
    LPWSAPROTOCOL_INFOW lpProtocolInfo = nullptr;

    // WSCEnumProtocols is broken (nice!). You *must* call it 1st time with
    // null buffer & bufferSize 0. Otherwise it will corrupt your heap in
    // case the necessary buffer size exceeds your allocated buffer. Do
    // never ever trust Microsoft WinAPI documentation!
    while ((iNuminfo = WSCEnumProtocols(nullptr, lpProtocolInfo, &bufferSize,
                                        &iErrno)) == SOCKET_ERROR) {
        if (iErrno == WSAENOBUFS) {
            protocolInfo.resize(bufferSize, 0);
            lpProtocolInfo =
                reinterpret_cast<LPWSAPROTOCOL_INFOW>(protocolInfo.data());
        } else {
            std::cerr << "WSCEnumProtocols failed with error: " << iErrno
                      << std::endl;
            WSACleanup();
            exit(1);
        }
    }

    for (INT i = 0; i < iNuminfo; ++i) {
        if (lpProtocolInfo[i].iAddressFamily == AF_INET6) return true;
    }

    return false;
}

std::string mapSectionName(const std::string &sectionName) {
    const std::unordered_map<std::string, std::string> mappedSectionNames = {
        {"webservices", "wmi_webservices"}, {"ohm", "openhardwaremonitor"}};
    const auto it = mappedSectionNames.find(sectionName);
    return it == mappedSectionNames.end() ? sectionName : it->second;
}

std::string mapDirect(const std::string &name) { return name; }

void addConditionPattern(globline_container &globline, const char *state,
                         const char *value) {
    globline.patterns.emplace_back(std::toupper(state[0]), value);
}

using OnlyFromConfigurable =
    SplittingListConfigurable<only_from_t,
                              BlockMode::FileExclusive<only_from_t>>;

class ParserImplementation {
public:
    ParserImplementation()
        : port(parser, "global", "port", 6556)
        , realtime_port(parser, "global", "realtime_port", 6559)
        , realtime_timeout(parser, "global", "realtime_timeout", 90)
        , crash_debug(parser, "global", "crash_debug", false)
        , logging(parser, "global", "logging", "yes")
        , section_flush(parser, "global", "section_flush", true)
        , encrypted(parser, "global", "encrypted", false)
        , encrypted_rt(parser, "global", "encrypted_rt", true)
        , support_ipv6(parser, "global", "ipv6", supportIPv6())
        , remove_legacy(parser, "global", "remove_legacy", false)
        , passphrase(parser, "global", "passphrase", "")
        , only_from(parser, "global", "only_from")
        , _enabled_sections(parser, "global", "sections", mapSectionName)
        , _disabled_sections(parser, "global", "disabled_sections",
                             mapSectionName)
        , _realtime_sections(parser, "global", "realtime_sections",
                             mapSectionName)
        , _script_local_includes(parser, "local", "include")
        , _script_plugin_includes(parser, "plugin", "include")
        , _winperf_counters(parser, "winperf", "counters")

        // Dynamic sections

        // ps
        , _use_wmi(parser, "ps", "use_wmi", true)
        , _full_commandline(parser, "ps", "full_path", false)
        ,

        // fileinfo
        _fileinfo_paths(parser, "fileinfo", "path")

        // logwatch
        , _sendall(parser, "logwatch", "sendall", false)
        , _vista_api(parser, "logwatch", "vista_api", false)
        , _config(parser, "logwatch", "logname")

        , _globlines(parser, "logfiles")
        ,

        // plugin
        _plugins_default_execution_mode(parser, "global", "caching_method",
                                        script_execution_mode::SYNC)
        ,

        _local_default_execution_mode(parser, "global", "caching_method",
                                      script_execution_mode::SYNC)
        , _plugins_async_execution(parser, "global", "async_script_execution",
                                   script_async_execution::SEQUENTIAL)
        , _local_async_execution(parser, "global", "async_script_execution",
                                 script_async_execution::SEQUENTIAL)
        , _plugins_execute_suffixes(parser, "global", "execute")
        , _local_execute_suffixes(parser, "global", "execute")

        , _plugins_timeout(parser, "plugins", "timeout")
        , _plugins_cache_age(parser, "plugins", "cache_age")
        , _plugins_retry_count(parser, "plugins", "retry_count")
        , _plugins_execution_mode(parser, "plugins", "execution")

        , _local_timeout(parser, "local", "timeout")
        , _local_cache_age(parser, "local", "cache_age")
        , _local_retry_count(parser, "local", "retry_count")
        , _local_execution_mode(parser, "local", "execution")
        ,

        _entries(parser, "mrpe", "check")
        ,

        _includes(parser, "mrpe", "include") {
        parser.reg("logwatch", "logfile", &_config);
        _globlines.setGroupFunction(&addConditionPattern);
    }

    Configuration parser;

    Configurable<int> port;
    Configurable<int> realtime_port;
    Configurable<int> realtime_timeout;
    Configurable<bool> crash_debug;
    Configurable<std::string> logging;
    Configurable<bool> section_flush;
    Configurable<bool> encrypted;
    Configurable<bool> encrypted_rt;
    Configurable<bool> support_ipv6;
    Configurable<bool> remove_legacy;
    Configurable<std::string> passphrase;
    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::FileExclusive<std::vector<std::string>>,
        AddMode::Append<std::vector<std::string>>>
        only_from;
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

    // Dynamic sections

    // ps
    Configurable<bool> _use_wmi;
    Configurable<bool> _full_commandline;

    // fileinfo
    ListConfigurable<std::vector<fs::path>,
                     BlockMode::Nop<std::vector<fs::path>>,
                     AddMode::PriorityAppend<std::vector<fs::path>>>
        _fileinfo_paths;

    // logwatch
    Configurable<bool> _sendall;
    Configurable<bool> _vista_api;
    eventlog::Configurable _config;

    GlobListConfigurable _globlines;

    // plugin
    Configurable<script_execution_mode> _plugins_default_execution_mode;

    Configurable<script_execution_mode> _local_default_execution_mode;

    Configurable<script_async_execution> _plugins_async_execution;

    Configurable<script_async_execution> _local_async_execution;

    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::BlockExclusive<std::vector<std::string>>>
        _plugins_execute_suffixes;

    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::BlockExclusive<std::vector<std::string>>>
        _local_execute_suffixes;

    KeyedListConfigurable<int> _plugins_timeout;
    KeyedListConfigurable<int> _plugins_cache_age;
    KeyedListConfigurable<int> _plugins_retry_count;
    KeyedListConfigurable<script_execution_mode> _plugins_execution_mode;

    KeyedListConfigurable<int> _local_timeout;
    KeyedListConfigurable<int> _local_cache_age;
    KeyedListConfigurable<int> _local_retry_count;
    KeyedListConfigurable<script_execution_mode> _local_execution_mode;

    ListConfigurable<mrpe_entries_t> _entries;

    KeyedListConfigurable<std::string> _includes;
};

// Used in testing
bool CheckIniFile(const std::filesystem::path &Path) {
    auto p = std::make_unique<Configuration>();
    Configuration &parser(*p);
    Configurable<int> port(parser, "global", "port", 6556);
    Configurable<int> realtime_port(parser, "global", "realtime_port", 6559);
    Configurable<int> realtime_timeout(parser, "global", "realtime_timeout",
                                       90);
    Configurable<bool> crash_debug(parser, "global", "crash_debug", false);
    Configurable<std::string> logging(parser, "global", "logging", "yes");
    Configurable<bool> section_flush(parser, "global", "section_flush", true);
    Configurable<bool> encrypted(parser, "global", "encrypted", false);
    Configurable<bool> encrypted_rt(parser, "global", "encrypted_rt", true);
    Configurable<bool> support_ipv6(parser, "global", "ipv6", supportIPv6());
    Configurable<bool> remove_legacy(parser, "global", "remove_legacy", false);
    Configurable<std::string> passphrase(parser, "global", "passphrase", "");
    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::FileExclusive<std::vector<std::string>>,
        AddMode::Append<std::vector<std::string>>>
        only_from(parser, "global", "only_from", mapDirect);

    Configurable<bool> _ps_use_wmi(parser, "ps", "use_wmi", false);
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _enabled_sections(parser, "global", "sections", mapSectionName);
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _disabled_sections(parser, "global", "disabled_sections",
                           mapSectionName);
    SplittingListConfigurable<std::set<std::string>,
                              BlockMode::BlockExclusive<std::set<std::string>>,
                              AddMode::SetInserter<std::set<std::string>>>
        _realtime_sections(parser, "global", "realtime_sections",
                           mapSectionName);
    KeyedListConfigurable<std::string> _script_local_includes(parser, "local",
                                                              "include");
    KeyedListConfigurable<std::string> _script_plugin_includes(parser, "plugin",
                                                               "include");
    ListConfigurable<std::vector<winperf_counter>> _winperf_counters(
        parser, "winperf", "counters");

    // Dynamic sections

    // ps
    Configurable<bool> _use_wmi(parser, "ps", "use_wmi", true);
    Configurable<bool> _full_commandline(parser, "ps", "full_path", false);

    // fileinfo
    ListConfigurable<std::vector<fs::path>,
                     BlockMode::Nop<std::vector<fs::path>>,
                     AddMode::PriorityAppend<std::vector<fs::path>>>
        _fileinfo_paths(parser, "fileinfo", "path");

    // logwatch
    Configurable<bool> _sendall(parser, "logwatch", "sendall", false);
    Configurable<bool> _vista_api(parser, "logwatch", "vista_api", false);
    eventlog::Configurable _config(parser, "logwatch", "logname");
    parser.reg("logwatch", "logfile", &_config);

    GlobListConfigurable _globlines(parser, "logfiles");
    _globlines.setGroupFunction(&addConditionPattern);
    //
    // plugin
    Configurable<script_execution_mode> _plugins_default_execution_mode(
        parser, "global", "caching_method", script_execution_mode::SYNC);

    Configurable<script_execution_mode> _local_default_execution_mode(
        parser, "global", "caching_method", script_execution_mode::SYNC);

    Configurable<script_async_execution> _plugins_async_execution(
        parser, "global", "async_script_execution",
        script_async_execution::SEQUENTIAL);

    Configurable<script_async_execution> _local_async_execution(
        parser, "global", "async_script_execution",
        script_async_execution::SEQUENTIAL);

    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::BlockExclusive<std::vector<std::string>>>
        _plugins_execute_suffixes(parser, "global", "execute");

    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::BlockExclusive<std::vector<std::string>>>
        _local_execute_suffixes(parser, "global", "execute");

    KeyedListConfigurable<int> _plugins_timeout(parser, "plugins", "timeout");
    KeyedListConfigurable<int> _plugins_cache_age(parser, "plugins",
                                                  "cache_age");
    KeyedListConfigurable<int> _plugins_retry_count(parser, "plugins",
                                                    "retry_count");
    KeyedListConfigurable<script_execution_mode> _plugins_execution_mode(
        parser, "plugins", "execution");

    KeyedListConfigurable<int> _local_timeout(parser, "local", "timeout");
    KeyedListConfigurable<int> _local_cache_age(parser, "local", "cache_age");
    KeyedListConfigurable<int> _local_retry_count(parser, "local",
                                                  "retry_count");
    KeyedListConfigurable<script_execution_mode> _local_execution_mode(
        parser, "local", "execution");

    ListConfigurable<mrpe_entries_t> _entries(parser, "mrpe", "check");

    KeyedListConfigurable<std::string> _includes(parser, "mrpe", "include");

    if (parser.size() != 43) {
        XLOG::l("Failed to have required count of the config variables");
    } else {
        return parser.ReadSettings(Path, false);
    }
    return false;
}

Parser::~Parser() { delete pi_; }

void Parser::prepare() {
    if (pi_) delete pi_;
    pi_ = new ParserImplementation;
}

bool Parser::readIni(const std::filesystem::path &Path, bool) {
    if (!pi_) return false;
    return pi_->parser.ReadSettings(Path, false);
}

void Parser::emitYaml(std::ostream &Out) {
    if (!pi_) return;
    pi_->parser.outputConfigurables(Out);
}

struct YamlOut {
    std::string section_;
    std::string key_;
    std::string value_;
};

// determine how we will convert th ini value into yaml
enum MapMode {
    kMissing,    // end
    kValue,      // int
    kIniString,  // bool and string
    kNode,       // sequences
    kPattern,    // keyed pattern
    kManual,     // trash
    kSkip
};

struct Mapping {
    std::string key_;
    std::string sub_key_;
    MapMode map_mode_;
};

// clang-format off
// we need a good formatted table
const std::unordered_map<std::string, Mapping> G_Mapper = {
    {"global.caching_method",   { "", "", MapMode::kIniString}},// ignored
    {"global.async_script_execution",   { "", "", MapMode::kIniString}},// ignored
    {"global.encrypted",        { "", "", MapMode::kIniString}},// not supported
    {"global.encrypted_rt",     { "realtime", "encrypted", MapMode::kIniString}},
    {"global.ipv6",             { "", "", MapMode::kIniString}},
    {"global.remove_legacy",    { "", "", MapMode::kIniString}},
    {"global.only_from",        { "", "", MapMode::kIniString}},
    {"global.port",             { "", "", MapMode::kValue}},
    {"global.realtime_port",    { "realtime", "port", MapMode::kValue}},
    {"global.realtime_timeout", { "realtime", "timeout", MapMode::kValue}},
    {"global.section_flush",    { "", "", MapMode::kIniString}},//ignored
    {"global.execute",          { "", "", MapMode::kIniString}},
    {"global.passphrase",       { "", "", MapMode::kIniString}},//not supported
    {"global.realtime_sections",{ "realtime", "run", MapMode::kIniString}},
    {"global.crash_debug",      { "logging", "debug", MapMode::kIniString}},
    {"global.logging",          { "logging", "debug", MapMode::kIniString}},
    {"global.disabled_sections",{ "", "", MapMode::kIniString}},
    {"global.sections",         { "", "", MapMode::kIniString}},

    {"winperf.counters",        { "", "", MapMode::kNode}},

    {"ps.full_path",            { "", "", MapMode::kIniString}},
    {"ps.use_wmi",              { "", "", MapMode::kIniString}},

    {"fileinfo.path",           { "", "", MapMode::kNode}},

    {"plugins.cache_age",       { "plugins", "execution", MapMode::kPattern}},
    {"plugins.timeout",         { "plugins", "execution", MapMode::kPattern}},
    {"plugins.retry_count",     { "plugins", "execution", MapMode::kPattern}},
    {"plugins.async",           { "plugins", "execution", MapMode::kPattern}},

    {"local.cache_age",         { "local", "execution", MapMode::kPattern}},
    {"local.timeout",           { "local", "execution", MapMode::kPattern}},
    {"local.retry_count",       { "local", "execution", MapMode::kPattern}},
    {"local.async",             { "local", "execution", MapMode::kPattern}},

    {"mrpe.config",             { "", "", MapMode::kNode}},

    {"logwatch.full_path",      { "", "", MapMode::kIniString}},
    {"logwatch.use_wmi",        { "", "", MapMode::kIniString}},

    {"logwatch.logfile",        { "", "", MapMode::kNode}},
    {"logwatch.logname",        { "", "", MapMode::kSkip}},// don't know what is the hell
    {"logwatch.sendall",        { "", "", MapMode::kIniString}},
    {"logwatch.vista_api",      { "", "", MapMode::kIniString}},

    {"logfiles.crit",           { "config", "", MapMode::kNode}},
    {"logfiles.ignore",         { "", "", MapMode::kSkip}},
    {"logfiles.ok",             { "", "", MapMode::kSkip}},
    {"logfiles.textfile",       { "", "", MapMode::kSkip}},
    {"logfiles.warn",           { "", "", MapMode::kSkip}},

    {"",                        { "", "", MapMode::kMissing}}
};
const Mapping G_MissingMapping{ "", "", MapMode::kMissing };
// clang-format on

std::string MakeMappingKey(std::string Section, std::string Key) {
    auto s = Section + "." + Key;
    std::transform(s.cbegin(), s.cend(), s.begin(), tolower);

    return s;
}

const Mapping &FindMapping(const std::string Section, const std::string Key) {
    auto kk = MakeMappingKey(Section, Key);
    auto found = G_Mapper.find(kk);
    if (found == G_Mapper.end()) {
        XLOG::stdio("UNKNOWN KEY {}.{}", Section, Key);
        return G_MissingMapping;
    } else {
        return found->second;
    }
}

void AddKeyedPattern(YAML::Node Node, const std::string Key,
                     const std::string &Pattern, const std::string &Value) {
    for (YAML::iterator it = Node.begin(); it != Node.end(); ++it) {
        auto entry = *it;
        if (entry["pattern"].as<std::string>() == Pattern) {
            entry[Key] = Value;
            return;
        }
    }

    auto string = ToYamlKeyedString(Key, Pattern, Value);
    auto node = YAML::Load(string);
    Node.push_back(node);
}

YAML::Node Parser::emitYaml() noexcept {
    if (!pi_) return {};

    YAML::Node yaml;
    pi_->parser.outputConfigurables([&yaml](const std::string &Section,
                                            const std::string &Key,
                                            const std::string &Value,
                                            const std::string &IniString) {
        try {
            auto mapping = FindMapping(Section, Key);
            if (mapping.map_mode_ == MapMode::kMissing) {
                XLOG::stdio("UNKNONW KEY {}.{} \t<--- {}", Section, Key, Value);
                return;
            }
            if (mapping.map_mode_ == MapMode::kSkip) return;

            yaml[Section]["enabled"] = true;

            auto &key = mapping.key_.empty() ? Key : mapping.key_;
            auto &sub_key = mapping.sub_key_;
            switch (mapping.map_mode_) {
                case MapMode::kIniString:  // from the in i file
                case MapMode::kValue:      // decoded value
                    if (sub_key.empty())
                        yaml[Section][key] = IniString;
                    else {
                        yaml[Section][key][sub_key] = IniString;
                        if (Key == "realtime_sections") {
                            yaml[Section][key]["enabled"] = true;
                        }
                    }
                    break;

                case MapMode::kNode: {
                    auto node = YAML::Load(Value);
                    if (sub_key.empty())
                        yaml[Section][key] = node;
                    else {
                        yaml[Section][key][sub_key] = node;
                    }
                } break;

                case MapMode::kPattern: {
                    if (sub_key.empty()) {
                        XLOG::l.bp("not possible");
                        break;
                    }
                    yaml[Section][vars::kEnabled] = true;
                    AddKeyedPattern(yaml[Section][sub_key], Key, IniString,
                                    Value);
                } break;
                default: {
                    yaml[Section][key] = Value;
                }
            }

            // XLOG::stdio("assigned {}.{} \t<--- {}", Section, Key,
            // Value);
        } catch (...) {
            std::cout << yaml << std::endl;
            XLOG::l("error {}.{} = {}", Section, Key, Value);
        }
    });

    // post processing yaml
    PatchRelativePath(yaml, groups::kPlugins, vars::kPluginsExecution,
                      vars::kPluginPattern, cma::cfg::vars::kPluginUserFolder);

    return yaml;
}  // namespace cma::cfg::cvt

}  // namespace cma::cfg::cvt

/// \brief - memmove replacer for SimpleIni.h
///
/// asan  gives false positive when MSVC optimizer which replaces memmove with
/// memcpy we don't want either to disable optimization or disable asan
/// Not tested.
void MemMove(void *dst, const void *src, size_t count) {
    if (dst == nullptr || src == nullptr || count == 0) {
        return;
    }
    for (size_t i = 0; i < count; ++i) {
        static_cast<char *>(dst)[i] = static_cast<const char *>(dst)[i];
    }
}
