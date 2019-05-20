
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

void PluginsProvider::loadConfig() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    PathVector pv;
    if (local_) {
        for (auto& folder : groups::localGroup.folders()) {
            pv.emplace_back(folder);
        }
    } else {
        for (auto& folder : groups::plugins.folders()) {
            pv.emplace_back(folder);
        }
    }
    auto files = cma::GatherAllFiles(pv);

    auto execute = GetInternalArray(groups::kGlobal, vars::kExecute);

    cma::FilterPathByExtension(files, execute);

    auto yaml_units =
        GetArray<YAML::Node>(cfg_name_, cma::cfg::vars::kPluginsExecution);
    std::vector<Plugins::ExeUnit> exe_units;
    cma::cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);

    UpdatePluginMap(pm_, local_, files, exe_units, true);
    timeout_ = 0;
    for (auto& entry : pm_) {
        auto current_timeout = entry.second.timeout();
        if (current_timeout > timeout_) timeout_ = current_timeout;
    }

    auto configured_timeout =
        GetVal(cfg_name_, vars::kPluginMaxWait, kDefaultPluginTimeout);

    if (configured_timeout < timeout_) {
        XLOG::d("Timeout is corrected from {} to {}", timeout_,
                configured_timeout);
        timeout_ = configured_timeout;
    }
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
    XLOG::d.t(XLOG_FUNC + " !");
    std::string out = cma::section::MakeEmptyHeader();
    gatherAllData(out);
    out += cma::section::MakeEmptyHeader();
    section_last_output_ = out;
}

// local body empty
void LocalProvider::updateSectionStatus() {
    XLOG::d.t(XLOG_FUNC + " !");
    std::string out = cma::section::MakeLocalHeader();
    gatherAllData(out);
    out += cma::section::MakeEmptyHeader();
    section_last_output_ = out;
}

std::string PluginsProvider::makeBody() const {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering {} processed", last_count_);

    return section_last_output_;
}

}  // namespace cma::provider
