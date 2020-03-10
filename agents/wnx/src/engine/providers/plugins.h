// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef plugins_h__
#define plugins_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {
namespace config {
// set behavior of the output
// i future may be controlled using yml
extern bool G_LocalNoSendIfEmptyBody;
extern bool G_LocalSendEmptyAtEnd;
};  // namespace config

enum class PluginType { normal, local };

class PluginsProvider : public Asynchronous {
public:
    PluginsProvider() : Asynchronous(cma::section::kPlugins) {
        setHeaderless();
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cma::cfg::groups::kPlugins;
    }

    PluginsProvider(const std::string_view& Name, char Separator)
        : Asynchronous(Name, Separator) {
        setHeaderless();
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cma::cfg::groups::kPlugins;
    }

    virtual void loadConfig();

    virtual void updateSectionStatus();

    virtual bool isAllowedByCurrentConfig() const override;

    void preStart() noexcept override;

    void detachedStart() noexcept;

    void updateCommandLine() noexcept;

    void updateTimeout() noexcept;

protected:
    std::vector<std::string> gatherAllowedExtensions() const;
    static void UpdatePluginMapCmdLine(PluginMap& pm,
                                       cma::srv::ServiceProcessor* sp);
    void gatherAllData(std::string& Out);
    std::string cfg_name_;
    bool local_;
    cma::PluginMap pm_;
    std::string section_last_output_;
    int last_count_;
    std::string makeBody() override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileInfoTest;
    FRIEND_TEST(FileInfoTest, Base);

    friend class PluginTest;
    FRIEND_TEST(PluginTest, ModulesCmdLine);
    FRIEND_TEST(PluginTest, AllowedExtensions);
#endif
};

class LocalProvider : public PluginsProvider {
public:
    LocalProvider() : PluginsProvider(cma::section::kLocal, '\0') {
        local_ = true;
        cfg_name_ = cma::cfg::groups::kLocal;
    }
    virtual void updateSectionStatus();
};

enum class PluginMode { all, sync, async };
int FindMaxTimeout(const cma::PluginMap& pm, PluginMode type);

}  // namespace provider

};  // namespace cma

#endif  // plugins_h__
