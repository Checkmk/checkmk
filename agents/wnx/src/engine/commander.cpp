// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "commander.h"

#include <string>

#include "cfg.h"
#include "logger.h"

namespace cma {

namespace commander {

std::mutex run_command_processor_lock;

bool RunCommand(std::string_view peer, std::string_view cmd) {
    if (!cma::tools::IsEqual(peer, kMainPeer)) {
        XLOG::d("Peer name '{}' is invalid", peer);
        return false;
    }

    if (cmd.empty()) return false;

    if (cma::tools::IsEqual(cmd, kReload)) {
        XLOG::l.t("Commander: Reload");

        cma::ReloadConfig();  // command line
        return true;
    }

    if (cma::tools::IsEqual(cmd, kPassTrue)) {
        XLOG::l.t("Commander: Pass True");
        return true;
    }

    if (cma::tools::IsEqual(cmd, kUninstallAlert)) {
        XLOG::l.t("Commander: Alert of Uninstall");
        if (cma::IsTest()) return false;
        if (!cma::IsService()) return false;

        cma::G_UninstallALert.set();
        return true;
    }

    XLOG::l("Commander: Unknown command '{}'", cmd);
    return false;
}

// #TODO global. MOVE TO THE service processor
// #GLOBAL
RunCommandProcessor g_rcp = RunCommand;

RunCommandProcessor ObtainRunCommandProcessor() {
    std::lock_guard lk(run_command_processor_lock);
    return g_rcp;
}

void ChangeRunCommandProcessor(RunCommandProcessor rcp) {
    std::lock_guard lk(run_command_processor_lock);
    g_rcp = rcp;
}

}  // namespace commander

}  // namespace cma
