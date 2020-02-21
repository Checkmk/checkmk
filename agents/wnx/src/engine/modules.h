//
//
// Support for the Windows Agent  modules
//
//

#pragma once

#include <yaml-cpp/yaml.h>

#include <string>

namespace cma::cfg::modules {
class Module {
public:
    // loader
    [[nodiscard]] bool loadFrom(const YAML::Node& node);

    // accessors
    [[nodiscard]] bool valid() const noexcept { return !name_.empty(); }
    [[nodiscard]] auto name() const noexcept { return name_; }
    [[nodiscard]] auto exts() const noexcept { return exts_; }
    [[nodiscard]] auto exec() const noexcept { return exec_; }
    [[nodiscard]] auto dir() const noexcept { return dir_; }

private:
    void reset() noexcept;
    std::string name_;
    std::vector<std::string> exts_;
    std::wstring exec_;
    std::string dir_;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class Modules;
    FRIEND_TEST(ModulesTest, Loader);
    FRIEND_TEST(ModulesTest, Internal);
#endif
};

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node& yaml);

class Zip {};

}  // namespace cma::cfg::modules
