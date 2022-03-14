// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/plugins.h"

#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "logger.h"
#include "service_processor.h"
#include "tools/_raii.h"

using namespace std::literals;

namespace cma::provider {

bool PluginsProvider::isAllowedByCurrentConfig() const {
    return cfg::groups::global.allowedSection(cfg_name_);
}

static bool IsPluginRequiredType(const PluginEntry& plugin,
                                 PluginMode need_type) {
    switch (need_type) {
        case PluginMode::async:
            return plugin.isRealAsync();

        case PluginMode::sync:
            return !plugin.isRealAsync();

        case PluginMode::all:
            return true;
    }

    XLOG::l(XLOG_FUNC + " input is unknown [{}], return true by default");
    return true;
}

// returns 0 on lack plugin entries
int FindMaxTimeout(const cma::PluginMap& pm, PluginMode need_type) {
    int timeout = 0;
    for (const auto& [path, plugin] : pm) {
        if (IsPluginRequiredType(plugin, need_type)) {
            timeout = std::max(timeout, plugin.timeout());
        }
    }

    return timeout;
}

// Scans for sync plugins max timeout and set this max
// if timeout is too big, than set default from the max_wait
void PluginsProvider::updateTimeout() {
    timeout_ = FindMaxTimeout(pm_, PluginMode::sync);

    auto config_max_wait = cfg::GetVal(cfg_name_, cfg::vars::kPluginMaxWait,
                                       cfg::kDefaultPluginTimeout);

    if (timeout_ > config_max_wait) {
        // too high timeout and bad plugin in config may break agent fully
        XLOG::d("Timeout is corrected from [{}] to [{}]", timeout_,
                config_max_wait);
        timeout_ = config_max_wait;
        return;
    }

    if (timeout_ != 0) {
        XLOG::t("Timeout for '{}' is updated to [{}]", cfg_name_, timeout_);
    }
}

static void LogExecuteExtensions(std::string_view title,
                                 const std::vector<std::string>& arr) {
    std::string formatted_string{"["};
    for (const auto& s : arr) {
        formatted_string += s;
        formatted_string += ",";
    }
    if (!arr.empty()) {
        formatted_string.pop_back();
    }

    formatted_string += "]";

    XLOG::d.i("{} {}", title, formatted_string);
}

void PluginsProvider::updateCommandLine() {
    try {
        if (getHostSp() == nullptr && !local_) {
            XLOG::l("Plugins must have correctly set owner to use modules");
        }

        UpdatePluginMapCmdLine(pm_, getHostSp());
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " unexpected exception '{}'", e.what());
    }
}

void PluginsProvider::UpdatePluginMapCmdLine(PluginMap& pm,
                                             cma::srv::ServiceProcessor* sp) {
    for (auto& [name, entry] : pm) {
        XLOG::t.i("checking entry");
        entry.setCmdLine(L""sv);
        if (entry.path().empty()) continue;
        XLOG::t.i("checking host");

        if (sp == nullptr) continue;

        auto& mc = sp->getModuleCommander();
        auto fname = entry.path().u8string();
        XLOG::t.i("checking our script");

        if (!mc.isModuleScript(fname)) continue;

        XLOG::t.i("building command line");

        auto cmd_line = mc.buildCommandLine(fname);
        if (!cmd_line.empty()) {
            XLOG::t.i("A Module changes command line of the plugin '{}'",
                      wtools::ToUtf8(cmd_line));
            entry.setCmdLine(cmd_line);
        }
    }
}

std::vector<std::string> PluginsProvider::gatherAllowedExtensions() const {
    auto* sp = getHostSp();
    auto global_exts =
        cfg::GetInternalArray(cfg::groups::kGlobal, cfg::vars::kExecute);

    // check that plugin has owner(in the case of local it is not true)
    if (sp == nullptr) {
        return global_exts;
    }

    auto mc = sp->getModuleCommander();

    auto exts = mc.getExtensions();
    for (auto& e : exts) {
        if (e.empty()) continue;

        if (e[0] == '.') e.erase(e.begin(), e.begin() + 1);
    }

    for (auto& ge : global_exts) {
        exts.emplace_back(ge);
    }

    return exts;
}

void PluginsProvider::loadConfig() {
    auto folder_vector = local_ ? cfg::groups::localGroup.folders()
                                : cfg::groups::plugins.folders();

    PathVector pv;
    for (auto& folder : folder_vector) {
        pv.emplace_back(folder);
    }

    // linking all files, execute and extensions
    auto files = cma::GatherAllFiles(pv);
    XLOG::t("Found [{}] files to execute", files.size());
    auto exts = gatherAllowedExtensions();

    LogExecuteExtensions("Allowed Extensions:", exts);
    if (exts.empty()) {
        XLOG::l("There are no allowed extensions in config. This is strange.");
    }

    cma::FilterPathByExtension(files, exts);
    RemoveForbiddenNames(files);

    XLOG::d.t("Left [{}] files to execute", files.size());

    auto yaml_units =
        cfg::GetArray<YAML::Node>(cfg_name_, cfg::vars::kPluginsExecution);

    // linking exe units with all plugins in map
    std::vector<cfg::Plugins::ExeUnit> exe_units;
    cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);
    UpdatePluginMap(pm_, local_, files, exe_units, true);
    XLOG::d.t("Left [{}] files to execute in '{}'", pm_.size(), uniq_name_);

    updateCommandLine();
    updateTimeout();
}

namespace {
std::string ToString(const std::vector<char> &v) {
    return std::string{v.begin(), v.end()};
}
}  // namespace

void PluginsProvider::gatherAllData(std::string& out) {
    int last_count = 0;
    auto data_sync = RunSyncPlugins(pm_, last_count, timeout_);
    last_count_ += last_count;

    auto data_async = RunAsyncPlugins(pm_, last_count, true);
    last_count_ += last_count;

    out += ToString(data_sync);
    out += ToString(data_async);
}

void PluginsProvider::preStart() {
    loadConfig();
    int last_count = 0;
    RunAsyncPlugins(pm_, last_count, true);
}

void PluginsProvider::detachedStart() {
    loadConfig();
    int last_count = 0;
    RunDetachedPlugins(pm_, last_count);
}

void PluginsProvider::updateSectionStatus() {
    auto out = section::MakeEmptyHeader();
    gatherAllData(out);
    out += section::MakeEmptyHeader();
    section_last_output_ = out;
}

namespace config {
// set behavior of the output
// i future may be controlled using yml
bool g_local_no_send_if_empty_body = true;
bool g_local_send_empty_at_end = false;
};  // namespace config

void LocalProvider::updateSectionStatus() {
    std::string body;
    gatherAllData(body);

    if (config::g_local_no_send_if_empty_body && body.empty()) {
        section_last_output_.clear();
        return;
    }

    std::string out{section::MakeLocalHeader()};
    out += body;
    if (config::g_local_send_empty_at_end) {
        out += section::MakeEmptyHeader();
    }
    section_last_output_ = out;
}

std::string PluginsProvider::makeBody() { return section_last_output_; }

}  // namespace cma::provider
