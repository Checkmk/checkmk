
// provides basic api to start and stop service
#include "stdafx.h"

#include <filesystem>
#include <regex>
#include <string>
#include <tuple>

#include "fmt/format.h"

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "cfg.h"
#include "cma_core.h"
#include "glob_match.h"

#include "logger.h"

#include "providers/plugins.h"

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

    auto execute = GetArray<std::string>(groups::kGlobal, vars::kExecute);

    cma::FilterPathByExtension(files, execute);
    cma::RemoveDuplicatedNames(files);

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
        XLOG::d("Timeout is corrected fropm {} to {}", timeout_,
                configured_timeout);
        timeout_ = configured_timeout;
    }
}

void PluginsProvider::gatherAllData(std::string& Out) {
    cma::cfg::SetupPluginEnvironment();
    int last_count = 0;
    auto data_sync = RunSyncPlugins(pm_, last_count, timeout_);
    last_count_ += last_count;

    auto data_async = RunAsyncPlugins(pm_, last_count, true);
    last_count_ += last_count;

    cma::tools::AddString(Out, data_sync);
    cma::tools::AddString(Out, data_async);
}

// empty body empty
void PluginsProvider::updateSectionStatus() {
    XLOG::d(XLOG_FUNC + " !");
    std::string out = cma::section::MakeEmptyHeader();
    gatherAllData(out);
    out += cma::section::MakeEmptyHeader();
    section_last_output_ = out;
}

// local body empty
void LocalProvider::updateSectionStatus() {
    XLOG::d(XLOG_FUNC + " !");
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
