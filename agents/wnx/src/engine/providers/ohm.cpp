
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/ohm.h"

#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "logger.h"
namespace fs = std::filesystem;

namespace cma::provider {
fs::path GetOhmCliPath() noexcept { return GetOhmCliPath(cfg::GetUserDir()); }

fs::path GetOhmCliPath(const fs::path &dir) noexcept {
    return dir / cfg::dirs::kUserBin / ohm::kExeModule;
}

void OhmProvider::updateSectionStatus() {
    if (!cma::tools::win::IsElevated()) {
        XLOG::d("You may have problems with OHM: service is not elevated");
    }
}

std::string OhmProvider::makeBody() {
    auto result = getData();
    if (result.empty()) {
        XLOG::d.t("No data for OHM, error number [{}]", registerError() + 1);
        return {};
    }
    if (resetError()) {
        XLOG::d.t("OHM is available again ");
    }

    return result;
}

}  // namespace cma::provider
