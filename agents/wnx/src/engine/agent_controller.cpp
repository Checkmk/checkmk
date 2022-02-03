
#include "stdafx.h"

#include "agent_controller.h"

#include <filesystem>

#include "cfg.h"
#include "common/wtools.h"

namespace fs = std::filesystem;

namespace cma::ac {
bool StartAgentController(const fs::path &service) {
    if (!cma::IsService()) {
        return false;
    }

    auto controller = service;
    controller.replace_filename(cfg::files::kAgentCtl);
    wtools::AppRunner ar;
    auto proc_id = ar.goExecAsDetached(controller.wstring() + L" daemon");
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]", controller,
                  proc_id);
        return true;
    } else {
        XLOG::l("Agent controller '{}' failed to start", controller);
        return false;
    }
}

bool KillAgentController() {
    if (cma::IsService()) {
        return wtools::KillProcess(cfg::files::kAgentCtl, 1);
    }
    return false;
}

}  // namespace cma::ac
