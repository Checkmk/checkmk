// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/plugins.h"

#include <filesystem>
#include <iostream>
#include <numeric>
#include <ranges>
#include <string>
#include <string_view>
#include <vector>

#include "common/wtools.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/logger.h"
#include "wnx/service_processor.h"

using namespace std::literals;
namespace vs = std::views;

namespace cma::provider {
namespace config {

// set behavior of the output
// i future may be controlled using yml
bool g_local_no_send_if_empty_body = true;
bool g_local_send_empty_at_end = false;
}  // namespace config

bool PluginsBaseProvider::isAllowedByCurrentConfig() const {
    return cfg::groups::g_global.allowedSection(cfg_name_);
}

static bool IsPluginRequiredType(const PluginEntry &plugin,
                                 PluginMode need_type) {
    switch (need_type) {
        case PluginMode::async:
            return plugin.isRealAsync();

        case PluginMode::sync:
            return !plugin.isRealAsync();

        case PluginMode::all:
            return true;
    }

    // unreachable
    return true;
}

// returns 0 on lack plugin entries
int FindMaxTimeout(const PluginMap &pm, PluginMode need_type) {
    auto x = pm | vs::values | vs::filter([need_type](const auto &v) {
                 return IsPluginRequiredType(v, need_type);
             }) |
             vs::transform([](const auto &p) noexcept { return p.timeout(); });
    return x.empty() ? 0 : *std::ranges::max_element(x);
}

// Scans for sync plugins max timeout and set this max
// if timeout is too big, than set default from the max_wait
void PluginsBaseProvider::updateSyncTimeout() {
    const auto max_plugin_timeout = FindMaxTimeout(pm_, PluginMode::sync);
    const auto section_max_wait = cfg::GetVal(
        cfg_name_, cfg::vars::kPluginMaxWait, cfg::kDefaultPluginTimeout);
    setTimeout(std::min(max_plugin_timeout, section_max_wait));
}

static void LogExecuteExtensions(std::string_view title,
                                 const std::vector<std::string> &arr) {
    auto joined = arr | std::views::join_with(',');
    auto formatted_string =
        std::accumulate(joined.begin(), joined.end(), std::string{});
    XLOG::d.i("{} [{}]", title, formatted_string);
}

void PluginsBaseProvider::updateCommandLine() {
    try {
        if (getHostSp() == nullptr && exec_type_ == ExecType::plugin) {
            XLOG::l("Plugins must have correctly set owner to use modules");
        }

        UpdatePluginMapCmdLine(pm_, getHostSp());
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " unexpected exception '{}'", e.what());
    }
}

void PluginsBaseProvider::UpdatePluginMapCmdLine(PluginMap &pm,
                                                 srv::ServiceProcessor *sp) {
    for (auto &entry : pm | std::views::values) {
        XLOG::t.i("checking entry");
        entry.setCmdLine(L""sv);
        if (entry.path().empty()) {
            continue;
        }
        XLOG::t.i("checking host");

        if (sp == nullptr) {
            continue;
        }

        auto &mc = sp->getModuleCommander();
        auto file_name = wtools::ToStr(entry.path());
        XLOG::t.i("checking our script");

        if (!mc.isModuleScript(file_name)) {
            continue;
        }

        XLOG::t.i("building command line");

        auto cmd_line = mc.buildCommandLine(file_name);
        if (!cmd_line.empty()) {
            XLOG::t.i("A Module changes command line of the plugin '{}'",
                      wtools::ToUtf8(cmd_line));
            entry.setCmdLine(cmd_line);
        }
    }
}

std::vector<std::string> PluginsBaseProvider::gatherAllowedExtensions() const {
    auto *sp = getHostSp();
    auto global_exts =
        cfg::GetInternalArray(cfg::groups::kGlobal, cfg::vars::kExecute);

    // check that plugin has owner(in the case of local it is not true)
    if (sp == nullptr) {
        return global_exts;
    }

    const auto &mc = sp->getModuleCommander();

    auto exts = mc.getExtensions();
    for (auto &e : exts) {
        if (e.empty()) {
            continue;
        }

        if (e[0] == '.') {
            e.erase(e.begin(), e.begin() + 1);
        }
    }

    for (auto &ge : global_exts) {
        exts.emplace_back(ge);
    }

    return exts;
}

void PluginsBaseProvider::loadConfig() {
    const auto folder_vector = exec_type_ == ExecType::local
                                   ? cfg::groups::g_local_group.folders()
                                   : cfg::groups::g_plugins.folders();

    PathVector pv;
    for (auto &&folder : folder_vector) {
        pv.emplace_back(folder);
    }

    // linking all files, execute and extensions
    auto files = cma::GatherAllFiles(pv);
    XLOG::t("Found [{}] files to execute", files.size());
    const auto extensions = gatherAllowedExtensions();

    LogExecuteExtensions("Allowed Extensions:", extensions);
    if (extensions.empty()) {
        XLOG::l("There are no allowed extensions in config. This is strange.");
    }

    FilterPathByExtension(files, extensions);
    RemoveForbiddenNames(files);

    XLOG::d.t("Left [{}] files to execute", files.size());

    const auto yaml_units =
        cfg::GetArray<YAML::Node>(cfg_name_, cfg::vars::kPluginsExecution);

    // linking exe units with all plugins in map
    const auto  exe_units  = cfg::LoadExeUnitsFromYaml(yaml_units);
    UpdatePluginMap(
        getHostSp() == nullptr ? nullptr : getHostSp()->getInternalUsers(), pm_,
        exec_type_, files, exe_units, true);
    XLOG::d.t("Left [{}] files to execute in '{}'", pm_.size(), uniq_name_);

    updateCommandLine();
    updateSyncTimeout();
}

namespace {
std::string ToString(const std::vector<char> &v) {
    return std::string{v.begin(), v.end()};
}
}  // namespace

void PluginsBaseProvider::gatherAllData(std::string &out) {
    const auto [data_sync, sync_count] = RunSyncPlugins(pm_, timeout());
    const auto [data_async, async_count] = RunAsyncPlugins(pm_, true);
    last_count_ += sync_count + async_count;
    out += ToString(data_sync);
    out += ToString(data_async);
}

void PluginsBaseProvider::preStart() {
    loadConfig();
    RunAsyncPlugins(pm_, true);
}

void PluginsBaseProvider::detachedStart() {
    loadConfig();
    int last_count = 0;
    RunDetachedPlugins(pm_, last_count);
}

std::string PluginsBaseProvider::makeBody() { return section_last_output_; }

void PluginsProvider::updateSectionStatus() {
    auto out = section::MakeEmptyHeader();
    gatherAllData(out);
    out += section::MakeEmptyHeader();
    section_last_output_ = out;
}

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

}  // namespace cma::provider
