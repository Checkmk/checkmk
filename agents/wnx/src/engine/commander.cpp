// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "commander.h"

#include <string>

#include "cfg.h"
#include "logger.h"

namespace cma::commander {

namespace {
std::mutex g_run_command_processor_lock{};

}  // namespace

bool RunCommand(std::string_view peer, std::string_view cmd) {
    if (!tools::IsEqual(peer, kMainPeer)) {
        XLOG::d("Peer name '{}' is invalid", peer);
        return false;
    }

    if (cmd.empty()) return false;

    if (tools::IsEqual(cmd, kReload)) {
        XLOG::l.t("Commander: Reload");

        ReloadConfig();  // command line
        return true;
    }

    if (tools::IsEqual(cmd, kPassTrue)) {
        XLOG::l.t("Commander: Pass True");
        return true;
    }

    if (tools::IsEqual(cmd, kUninstallAlert)) {
        XLOG::l.t("Commander: Alert of Uninstall");
        if (GetModus() != Modus::service) {
            return false;
        }

        g_uninstall_alert.set();
        return true;
    }

    XLOG::l("Commander: Unknown command '{}'", cmd);
    return false;
}

// #TODO global. MOVE TO THE service processor
// #GLOBAL
RunCommandProcessor g_rcp = RunCommand;

RunCommandProcessor ObtainRunCommandProcessor() {
    std::lock_guard lk(g_run_command_processor_lock);
    return g_rcp;
}

void ChangeRunCommandProcessor(RunCommandProcessor rcp) {
    std::lock_guard lk(g_run_command_processor_lock);
    g_rcp = rcp;
}

}  // namespace cma::commander
