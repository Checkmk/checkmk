
// provides basic api to start and stop service
#include "stdafx.h"

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "fmt/format.h"

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "cfg.h"
#include "cma_core.h"
#include "glob_match.h"

#include "logger.h"

#include "providers/ohm.h"

namespace cma::provider {

std::filesystem::path GetOhmCliPath() {
    namespace fs = std::filesystem;
    fs::path ohm_exe = cma::cfg::GetRootDir();
    ohm_exe /= cma::cfg::dirs::kAgentBin;
    ohm_exe /= cma::provider::kOpenHardwareMonitorCli;
    return ohm_exe;
}

void OhmProvider::loadConfig() {
    // normally open hardware monitor does nothing
    // during loading config
}

void OhmProvider::updateSectionStatus() {
    // normally open hardware monitor does nothing
    // during loading config
    if (!cma::tools::win::IsElevated()) {
        XLOG::d("You may have problems with OHM: service is not elevated");
    }
}

/*
std::string OhmProvider::makeBody() const {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    // probably we do not need this function
    // during loading config

    return "";
}
*/

}  // namespace cma::provider
