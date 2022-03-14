
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/ohm.h"

#include <fmt/format.h>

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "glob_match.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

// makes OHM binary filename
std::filesystem::path GetOhmCliPath() noexcept {
    return GetOhmCliPath(cma::cfg::GetUserDir());
}

std::filesystem::path GetOhmCliPath(const std::filesystem::path &dir) noexcept {
    namespace fs = std::filesystem;

    fs::path ohm_exe = dir;
    ohm_exe /= cma::cfg::dirs::kUserBin;
    ohm_exe /= ohm::kExeModule;

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

std::string OhmProvider::makeBody() {
    using namespace cma::cfg;
    auto result = Wmi::makeBody();
    // probably we do not need this function
    // during loading config
    if (result.empty()) {
        auto error_count = registerError();
        XLOG::d.t("No data for OHM, error number [{}]", error_count + 1);
    } else {
        if (resetError()) {
            XLOG::d.t("OHM is available again ");
        }
    }

    return result;
}

}  // namespace cma::provider
