// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef plugins_h__
#define plugins_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {
namespace config {
// set behavior of the output
// in future may be controlled using yml
extern bool g_local_no_send_if_empty_body;
extern bool g_local_send_empty_at_end;
};  // namespace config

enum class PluginType { normal, local };

class PluginsProvider : public Asynchronous {
public:
    PluginsProvider() : Asynchronous(section::kPlugins) {
        setHeaderless();
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cfg::groups::kPlugins;
    }

    PluginsProvider(std::string_view name, char separator)
        : Asynchronous(name, separator) {
        setHeaderless();
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cfg::groups::kPlugins;
    }

    void loadConfig() override;
    void updateSectionStatus() override;
    bool isAllowedByCurrentConfig() const override;
    void preStart() override;
    void detachedStart();
    void updateCommandLine();
    void updateTimeout();
    std::vector<std::string> gatherAllowedExtensions() const;

protected:
    static void UpdatePluginMapCmdLine(PluginMap &pm,
                                       srv::ServiceProcessor *sp);
    void gatherAllData(std::string &out);
    std::string cfg_name_;
    bool local_;
    PluginMap pm_;
    std::string section_last_output_;
    int last_count_;
    std::string makeBody() override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class PluginTest;
    FRIEND_TEST(PluginTest, ModulesCmdLine);
#endif
};

class LocalProvider : public PluginsProvider {
public:
    LocalProvider() : PluginsProvider(section::kLocal, '\0') {
        local_ = true;
        cfg_name_ = cfg::groups::kLocal;
    }
    virtual void updateSectionStatus();
};

enum class PluginMode { all, sync, async };
int FindMaxTimeout(const PluginMap &pm, PluginMode type);

}  // namespace cma::provider

#endif  // plugins_h__
