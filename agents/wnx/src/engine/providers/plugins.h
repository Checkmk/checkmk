
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

    void updateTimeout() noexcept;

protected:
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

enum class PluginType { all, sync, async };
int FindMaxTimeout(const cma::PluginMap& pm, PluginType type);

}  // namespace provider

};  // namespace cma

#endif  // plugins_h__
