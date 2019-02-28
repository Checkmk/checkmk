
// provides basic api to start and stop service

#pragma once
#ifndef plugins_h__
#define plugins_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class PluginsProvider : public Asynchronous {
public:
    PluginsProvider() : Asynchronous(cma::section::kPlugins) {
        headerless_ = true;
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cma::cfg::groups::kPlugins;
    }

    PluginsProvider(const std::string_view& Name, char Separator)
        : Asynchronous(Name, Separator) {
        headerless_ = true;
        timeout_ = 0;
        local_ = false;
        cfg_name_ = cma::cfg::groups::kPlugins;
    }

    virtual void loadConfig();

    virtual void updateSectionStatus();

    virtual bool isAllowedByCurrentConfig() const override;

protected:
    void gatherAllData(std::string& Out);
    std::string cfg_name_;
    bool local_;
    cma::PluginMap pm_;
    std::string section_last_output_;
    int last_count_;
    virtual std::string makeBody() const override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileInfoTest;
    FRIEND_TEST(FileInfoTest, Base);
#endif
};

class LocalProvider : public PluginsProvider {
public:
    LocalProvider() : PluginsProvider(cma::section::kLocalGroup, '\0') {
        local_ = true;
        cfg_name_ = cma::cfg::groups::kLocalGroup;
    }
    virtual void updateSectionStatus();
};

}  // namespace provider

};  // namespace cma

#endif  // plugins_h__
