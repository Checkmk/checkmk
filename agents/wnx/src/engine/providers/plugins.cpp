
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/plugins.h"

#include <filesystem>
#include <regex>
#include <string>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "glob_match.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

bool PluginsProvider::isAllowedByCurrentConfig() const {
    auto name = cfg_name_;
    bool allowed = cma::cfg::groups::global.allowedSection(name);
    return allowed;
}

static bool IsPluginRequiredType(const PluginEntry& plugin,
                                 PluginType need_type) {
    switch (need_type) {
        case PluginType::async:
            return plugin.isRealAsync();

        case PluginType::sync:
            return !plugin.isRealAsync();

        case PluginType::all:
            return true;
    }

    // safety check: warning disabled and enum changed
    XLOG::l.bp(XLOG_FUNC + " input is unknown [{}], return true by default");

    return true;
}

// scans plugin map by criteria to  find MAX timeout
// returns 0 on lack plugin entries
int FindMaxTimeout(const cma::PluginMap& pm, PluginType need_type) {
    int timeout = 0;
    for (const auto& [path, plugin] : pm) {
        if (IsPluginRequiredType(plugin, need_type))
            timeout = std::max(timeout, plugin.timeout());
    }

    return timeout;
}

// scans for sync plugins max timeout and set this max
// if timeout is too big, than set default from the max_wait
void PluginsProvider::updateTimeout() noexcept {
    using namespace cma::cfg;
    timeout_ = FindMaxTimeout(pm_, PluginType::sync);

    auto config_max_wait =
        GetVal(cfg_name_, vars::kPluginMaxWait, kDefaultPluginTimeout);

    if (timeout_ > config_max_wait) {
        // too high timeout and bad plugin in config may break agent fully
        XLOG::d("Timeout is corrected from [{}] to [{}]", timeout_,
                config_max_wait);
        timeout_ = config_max_wait;
        return;
    }

    if (timeout_)
        XLOG::t("Timeout for '{}' is updated to [{}]", cfg_name_, timeout_);
}

static void LogExecuteExtensions(std::string_view title,
                                 const std::vector<std::string>& arr) {
    std::string formatted_string = "[";
    for (const auto& s : arr) {
        formatted_string += s;
        formatted_string += ",";
    }
    if (arr.size()) formatted_string.pop_back();
    formatted_string += "]";

    XLOG::d.i("{} {}", title, formatted_string);
}

void PluginsProvider::loadConfig() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering '{}'", uniq_name_);

    // this is a copy...
    auto folder_vector =
        local_ ? groups::localGroup.folders() : groups::plugins.folders();

    PathVector pv;
    for (auto& folder : folder_vector) {
        pv.emplace_back(folder);
    }

    // linking all files, execute and extensions
    auto files = cma::GatherAllFiles(pv);
    XLOG::d.t("Found [{}] files to execute", files.size());
    auto execute = GetInternalArray(groups::kGlobal, vars::kExecute);
    LogExecuteExtensions("Allowed Extensions:", execute);
    if (execute.size() == 0) XLOG::l("No allowed extensions. This is strange.");

    cma::FilterPathByExtension(files, execute);
    XLOG::d.t("Left [{}] files to execute", files.size());

    auto yaml_units =
        GetArray<YAML::Node>(cfg_name_, cma::cfg::vars::kPluginsExecution);

    // linking exe units with all plugins in map
    std::vector<Plugins::ExeUnit> exe_units;
    LoadExeUnitsFromYaml(exe_units, yaml_units);
    UpdatePluginMap(pm_, local_, files, exe_units, true);
    XLOG::d.t("Left [{}] files to execute in '{}'", pm_.size(), uniq_name_);

    // calculating timeout(may change in every kick)
    updateTimeout();
}

void PluginsProvider::gatherAllData(std::string& Out) {
    int last_count = 0;
    auto data_sync = RunSyncPlugins(pm_, last_count, timeout_);
    last_count_ += last_count;

    auto data_async = RunAsyncPlugins(pm_, last_count, true);
    last_count_ += last_count;

    cma::tools::AddString(Out, data_sync);
    cma::tools::AddString(Out, data_async);
}

void PluginsProvider::preStart() noexcept {
    loadConfig();
    int last_count = 0;
    RunAsyncPlugins(pm_, last_count, true);
}

void PluginsProvider::detachedStart() noexcept {
    loadConfig();
    int last_count = 0;
    RunDetachedPlugins(pm_, last_count);
}

// empty body empty
void PluginsProvider::updateSectionStatus() {
    std::string out = cma::section::MakeEmptyHeader();
    gatherAllData(out);
    out += cma::section::MakeEmptyHeader();
    section_last_output_ = out;
}

// local body empty
void LocalProvider::updateSectionStatus() {
    std::string out = cma::section::MakeLocalHeader();
    gatherAllData(out);
    out += cma::section::MakeEmptyHeader();
    section_last_output_ = out;
}

std::string PluginsProvider::makeBody() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering {} processed", last_count_);

    return section_last_output_;
}

}  // namespace cma::provider
