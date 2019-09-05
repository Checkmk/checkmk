// Configuration Parameters for whole Agent
#include "stdafx.h"

#include "commander.h"

#include <string>

#include "cfg.h"
#include "logger.h"

namespace cma {

namespace commander {
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

    XLOG::l("Commander: Unknown command '{}'", cmd);
    return false;
}
}  // namespace commander

}  // namespace cma
