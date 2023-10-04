// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef PLUGINS_H
#define PLUGINS_H

#include <string>
#include <string_view>

#include "wnx/cma_core.h"
#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {
namespace config {
// set behavior of the output
// in future may be controlled using yml
extern bool g_local_no_send_if_empty_body;
extern bool g_local_send_empty_at_end;
}  // namespace config

class PluginsBaseProvider : public Asynchronous {
public:
    PluginsBaseProvider(std::string_view name, ExecType exec_type,
                        std::string_view cfg_name)
        : Asynchronous(name, '\0')
        , cfg_name_{cfg_name}
        , exec_type_{exec_type}
        , last_count_{0} {
        setHeaderless();
    }

    void loadConfig() override;
    void updateSectionStatus() override = 0;
    bool isAllowedByCurrentConfig() const override;
    void preStart() override;
    void detachedStart();
    void updateCommandLine();
    std::vector<std::string> gatherAllowedExtensions() const;

protected:
    void updateSyncTimeout();
    static void UpdatePluginMapCmdLine(PluginMap &pm,
                                       srv::ServiceProcessor *sp);
    void gatherAllData(std::string &out);
    std::string cfg_name_;
    ExecType exec_type_;
    PluginMap pm_;
    std::string section_last_output_;
    int last_count_;
    std::string makeBody() override;
};

class PluginsProvider final : public PluginsBaseProvider {
public:
    PluginsProvider()
        : PluginsBaseProvider(section::kPlugins, ExecType::plugin,
                              cfg::groups::kPlugins) {}
    void updateSectionStatus() override;
#if defined(ENABLE_WHITE_BOX_TESTING)
    friend class PluginTest;
    FRIEND_TEST(PluginTest, ModulesCmdLine);
#endif
};

class LocalProvider final : public PluginsBaseProvider {
public:
    LocalProvider()
        : PluginsBaseProvider(section::kLocal, ExecType::local,
                              cfg::groups::kLocal) {}
    void updateSectionStatus() override;
};

enum class PluginMode { all, sync, async };
int FindMaxTimeout(const PluginMap &pm, PluginMode need_type);

}  // namespace cma::provider

#endif  // PLUGINS_H
