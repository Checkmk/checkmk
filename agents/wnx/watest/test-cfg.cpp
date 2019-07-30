// test-yaml.cpp :
// YAML and around

#include "pch.h"

#include <filesystem>

#include "cfg.h"
#include "cfg_details.h"
#include "commander.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "providers/mrpe.h"
#include "read_file.h"
#include "service_processor.h"
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

namespace cma::commander {

static bool GetEnabledFlag(bool dflt) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    return cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
}

static void SetEnabledFlag(bool flag) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    yaml_global[cma::cfg::vars::kEnabled] = flag;
}

TEST(Cma, Commander) {
    using namespace std::chrono;
    //
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    EXPECT_TRUE(yaml_global[cma::cfg::vars::kEnabled].IsScalar());
    auto enabled =
        cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, false);
    ASSERT_TRUE(enabled);
    SetEnabledFlag(false);
    enabled = cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
    ASSERT_FALSE(enabled);
    cma::commander::RunCommand("a", cma::commander::kReload);
    EXPECT_FALSE(enabled);
    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    EXPECT_NO_THROW(cma::commander::RunCommand("", ""));
    cma::commander::RunCommand(cma::commander::kMainPeer,
                               cma::commander::kReload);
    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);
    SetEnabledFlag(false);

    cma::MailSlot mailbox("WinAgentTestLocal", 0);
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    cma::srv::ServiceProcessor processor;
    mailbox.ConstructThread(cma::srv::SystemMailboxCallback, 20, &processor);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    cma::tools::sleep(100ms);

    cma::carrier::CoreCarrier cc;
    // "mail"
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    cc.sendCommand(cma::commander::kMainPeer, "a");
    cma::tools::sleep(100ms);
    enabled = GetEnabledFlag(true);
    EXPECT_FALSE(enabled);
    cc.sendCommand(cma::commander::kMainPeer, cma::commander::kReload);
    cma::tools::sleep(100ms);

    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);

    cc.shutdownCommunication();
}
}  // namespace cma::commander

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

namespace details {
TEST(CmaCfg, InitEnvironment) {
    auto msi = FindMsiExec();
    auto host = FindHostName();

    ConfigInfo ci;
    EXPECT_TRUE(ci.getCwd().empty());
    EXPECT_TRUE(ci.getMsiExecPath().empty());
    EXPECT_TRUE(ci.getHostName().empty());
    ci.initEnvironment();
    EXPECT_EQ(ci.getCwd(), std::filesystem::current_path().wstring());
    EXPECT_EQ(ci.getMsiExecPath(), msi);
    EXPECT_EQ(ci.getHostName(), host);

    cma::OnStartTest();
    EXPECT_FALSE(cma::cfg::GetUserDir().empty());
}

TEST(CmaCfg, LogFileLocation) {
    namespace fs = std::filesystem;
    //
    cma::OnStartTest();
    fs::path expected = GetUserDir();
    expected /= dirs::kLog;

    {
        // default config to data/log
        fs::path dflt = details::GetDefaultLogPath();
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), expected.u8string()));
    }

    {
        // empty data to user/public
        auto& user = details::G_ConfigInfo.folders_.data_;
        auto old_user = user;
        ON_OUT_OF_SCOPE(details::G_ConfigInfo.folders_.data_ = old_user);
        user.clear();
        fs::path dflt = details::GetDefaultLogPath();
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Users\\public"));
    }

    {
        // empty gives us default to the data/log
        fs::path dflt = details::ConvertLocationToLogPath("");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), expected.u8string()));
    }

    {
        // empty without user gives us default to the public/user
        auto& user = details::G_ConfigInfo.folders_.data_;
        auto old_user = user;
        ON_OUT_OF_SCOPE(details::G_ConfigInfo.folders_.data_ = old_user);
        user.clear();

        fs::path dflt = details::ConvertLocationToLogPath("");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Users\\public"));
    }

    {
        // non empty gives us the dir
        fs::path dflt = details::ConvertLocationToLogPath("c:\\Windows\\Logs");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Windows\\Logs"));
    }
}
}  // namespace details

TEST(CmaCfg, SmallFoos) {
    auto s = ConstructTimeString();
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

namespace details {
TEST(CmaToolsDetails, FindServiceImage) {
    EXPECT_TRUE(FindServiceImagePath(L"").empty());
    auto x = FindServiceImagePath(L"check_mk_agent");
    if (x.empty()) {
        XLOG::SendStringToStdio(
            "Legacy Agent is not installed, test is not full",
            XLOG::Colors::yellow);
    } else {
        EXPECT_TRUE(std::filesystem::exists(x));
    }
}
TEST(CmaToolsDetails, ExtractPathFromServiceName) {
    auto x = ExtractPathFromServiceName(L"check_mk_agent");
    if (x.empty()) {
        XLOG::SendStringToStdio(
            "Legacy Agent is not installed, test is not full",
            XLOG::Colors::yellow);
    } else {
        EXPECT_TRUE(std::filesystem::exists(x));
        EXPECT_TRUE(cma::tools::IsEqual(x.u8string(),
                                        "c:\\Program Files (x86)\\check_mk"));
    }
}
}  // namespace details

TEST(Cma, OnStart) {
    {
        auto [r, d] = cma::FindAlternateDirs(L"");
        EXPECT_TRUE(r.empty());
        EXPECT_TRUE(d.empty());
    }
    {
        auto [r, d] = cma::FindAlternateDirs(kRemoteMachine);
        EXPECT_EQ(r, cma::tools::win::GetEnv(kRemoteMachine));
        EXPECT_EQ(d,
                  cma::tools::win::GetEnv(kRemoteMachine) + L"\\ProgramData");
    }
}

}  // namespace cma::cfg
