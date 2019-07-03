// test-yaml.cpp :
// YAML and around

#include "pch.h"

#include <filesystem>

#include "cfg.h"
#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "providers/mrpe.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "yaml-cpp/yaml.h"

// we want to avoid those data public
namespace cma {
namespace details {
extern bool G_Service;
extern bool G_Test;
}  // namespace details
}  // namespace cma

namespace cma::cfg {

std::string packaged_ini(kIniFromInstallMarker);

std::string wato_ini =
    "# Created by Check_MK Agent Bakery.\n"
    "# This file is managed via WATO, do not edit manually or you \n"
    "# lose your changes next time when you update the agent.\n"
    "\n"
    "[global]\n"
    "    # TCP port the agent is listening on\n"
    "    port = 6556\n"
    "\n";

[[nodiscard]] static bool CreateFileTest(std::filesystem::path Path,
                                         std::string Content) {
    std::error_code ec;
    std::filesystem::remove(Path, ec);
    if (ec.value() != 0 && ec.value() != 2) return false;

    std::ofstream ofs(Path);
    ofs << Content;
    return true;
}

extern void SetTestInstallationType(InstallationType);

TEST(CmaCfg, SmallFoos) {
    auto s = GetTimeString();
    EXPECT_TRUE(!s.empty());
}

TEST(CmaCfg, InstallProtocol) {
    auto name = ConstructInstallFileName(cma::cfg::GetRootDir());
    EXPECT_TRUE(!name.empty());
    auto str = name.string();
    EXPECT_TRUE(str.find(files::kInstallProtocol) != std::string::npos);

    name = ConstructInstallFileName("");
    EXPECT_TRUE(name.empty());
}

TEST(CmaCfg, ProcessPluginEnvironment) {
    //
    cma::OnStartTest();
    std::vector<std::pair<std::string, std::string>> pairs;
    ProcessPluginEnvironment(
        [&pairs](std::string_view name, std::string_view value) {
            pairs.emplace_back(std::string(name), std::string(value));
        });

    EXPECT_EQ(pairs.size(), 9);
    auto ret = std::none_of(pairs.begin(), pairs.end(),
                            [](std::pair<std::string, std::string> p) {
                                return p.first.empty() || p.second.empty();
                            });
    EXPECT_TRUE(ret);
    //
}

TEST(CmaCfg, InstallationTypeCheck) {
    namespace fs = std::filesystem;
    //
    cma::OnStartTest();
    ASSERT_TRUE(cma::IsTest());
    ON_OUT_OF_SCOPE(SetTestInstallationType(InstallationType::packaged));
    ON_OUT_OF_SCOPE(cma::details::G_Test = true;);

    EXPECT_EQ(DetermineInstallationType(), InstallationType::packaged);

    auto to_test = InstallationType::wato;
    cma::cfg::SetTestInstallationType(to_test);
    EXPECT_EQ(cma::cfg::DetermineInstallationType(), to_test);

    cma::details::G_Test = false;

    fs::path install_ini = cma::cfg::GetFileInstallDir();
    std::error_code ec;
    fs::create_directories(install_ini, ec);
    install_ini /= files::kIniFile;

    auto backup_file = install_ini;
    backup_file.replace_extension("in_");
    fs::remove(backup_file, ec);
    fs::copy_file(install_ini, backup_file, ec);
    ON_OUT_OF_SCOPE(fs::rename(backup_file, install_ini, ec);)

    ASSERT_TRUE(CreateFileTest(install_ini, wato_ini));

    EXPECT_EQ(DetermineInstallationType(), InstallationType::wato);

    ASSERT_TRUE(CreateFileTest(install_ini, packaged_ini));

    EXPECT_EQ(DetermineInstallationType(), InstallationType::packaged);
    // fs::remove(install_ini, ec);
}

}  // namespace cma::cfg
