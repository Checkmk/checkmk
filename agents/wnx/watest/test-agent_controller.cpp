// test-service.cpp

//
#include "pch.h"

#include <filesystem>

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

using namespace std::chrono_literals;
namespace fs = std::filesystem;
namespace cma::details {
extern bool g_is_service;
}

namespace cma::ac {
TEST(AgentController, StartAgent) {
    EXPECT_FALSE(ac::StartAgentController("cmd.exe"));
}

TEST(AgentController, KillAgent) {
    EXPECT_FALSE(ac::KillAgentController("anything"));
}

constexpr std::string_view port{"1111"};
constexpr std::string_view allowed{"::1 111.11.11/11 8.8.8.8"};
TEST(AgentController, BuildCommandLine) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "  only_from: \n"
                                         "  port: {}\n",
                                         port)));
    EXPECT_EQ(wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
              fmt::format("x daemon -P {} --agent_channel localhost:{} -vv",
                          port, windows_internal_port));
}

TEST(AgentController, BuildCommandLineAllowed) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "  only_from: {}\n"
                                         "  port: {}\n",
                                         allowed, port)));
    EXPECT_EQ(
        wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
        fmt::format("x daemon -P {} --agent_channel localhost:{} -A {} -vv",
                    port, windows_internal_port, allowed));
}

TEST(AgentController, LegacyMode) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_FALSE(ac::IsInLegacyMode());
    tst::CreateTextFile(fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile,
                        "test");
    EXPECT_TRUE(ac::IsInLegacyMode());
}

TEST(AgentController, CreateControllerFlagFile) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_FALSE(ac::IsControllerFlagFileExists());
    ac::CreateControllerFlagFile();
    EXPECT_TRUE(ac::IsControllerFlagFileExists());
}

TEST(AgentController, FabricConfig) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_TRUE(ac::IsRunController(cfg::GetLoadedConfig()));
}

TEST(AgentController, ConfigApi) {
    auto cfg = YAML::Load("system:\n  controller:\n    run: yes\n");
    EXPECT_TRUE(ac::IsRunController(cfg));
}

TEST(AgentController, ConfigApiDefaults) {
    auto cfg = YAML::Load("system:\n");
    EXPECT_FALSE(ac::IsRunController(cfg));
}

class AgentControllerCreateArtifacts : public ::testing::Test {
public:
    static constexpr std::string_view marker_2_1 =
        "Check MK monitoring and management Service - 2.1, 64-bit";
    static constexpr std::string_view marker_1_6_2_0 =
        "Check MK monitoring and management Service, 64-bit";
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(temp_fs_->loadFactoryConfig());
    }

    void TearDown() override { killArtifacts(); }

    bool markerExists() { return fs::exists(markerFile()); }
    bool legacyExists() { return fs::exists(legacyFile()); }
    bool flagExists() { return fs::exists(flagFile()); }

    void killArtifacts() {
        std::error_code ec;
        fs::remove(markerFile(), ec);
        fs::remove(legacyFile(), ec);
        fs::remove(flagFile(), ec);
    }

    fs::path markerFile() const {
        return temp_fs_->data() / ac::kCmkAgentUnistall;
    }

    fs::path flagFile() const {
        return temp_fs_->data() / ac::kControllerFlagFile;
    }

private:
    fs::path legacyFile() const {
        return temp_fs_->data() / ac::kLegacyPullFile;
    }

    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(AgentControllerCreateArtifacts, FromNothingNoController) {
    ac::CreateArtifacts("", false);
    EXPECT_FALSE(markerExists());
    EXPECT_FALSE(flagExists());
    EXPECT_FALSE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, FromNothingWithController) {
    ac::CreateArtifacts("", true);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(legacyExists());
    EXPECT_TRUE(flagExists());
}

TEST_F(AgentControllerCreateArtifacts, From21ncNoController) {
    tst::CreateTextFile(markerFile(), marker_2_1);
    ac::CreateArtifacts(markerFile(), false);
    EXPECT_FALSE(markerExists());
    EXPECT_FALSE(flagExists());
    EXPECT_FALSE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, From21ncWithController) {
    tst::CreateTextFile(markerFile(), marker_2_1);
    ac::CreateArtifacts(markerFile(), true);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(flagExists());
    EXPECT_FALSE(legacyExists());  // no changes!
}

TEST_F(AgentControllerCreateArtifacts, From21wcNoController) {
    tst::CreateTextFile(markerFile(), marker_2_1);
    tst::CreateTextFile(flagFile(), "flag_file");
    ac::CreateArtifacts(markerFile(), false);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(flagExists());  // no changes
    EXPECT_FALSE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, From21wcWithController) {
    tst::CreateTextFile(markerFile(), marker_2_1);
    tst::CreateTextFile(flagFile(), "flag_file");
    ac::CreateArtifacts(markerFile(), true);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(flagExists());
    EXPECT_FALSE(legacyExists());  // no changes!
}

TEST_F(AgentControllerCreateArtifacts, From1620NoController) {
    tst::CreateTextFile(markerFile(), marker_1_6_2_0);
    ac::CreateArtifacts(markerFile(), false);
    EXPECT_FALSE(markerExists());
    EXPECT_FALSE(flagExists());
    EXPECT_FALSE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, From1620WithController) {
    tst::CreateTextFile(markerFile(), marker_1_6_2_0);
    ac::CreateArtifacts(markerFile(), true);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(flagExists());
    EXPECT_TRUE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, From1620OldNoController) {
    tst::CreateTextFile(markerFile(), marker_1_6_2_0);
    auto timestamp = fs::last_write_time(markerFile());
    fs::last_write_time(markerFile(), timestamp - 11s);
    ac::CreateArtifacts(markerFile(), false);
    EXPECT_FALSE(markerExists());
    EXPECT_FALSE(flagExists());
    EXPECT_FALSE(legacyExists());
}

TEST_F(AgentControllerCreateArtifacts, From1620OldWithController) {
    tst::CreateTextFile(markerFile(), marker_1_6_2_0);
    auto timestamp = fs::last_write_time(markerFile());
    fs::last_write_time(markerFile(), timestamp - 11s);
    ac::CreateArtifacts(markerFile(), true);
    EXPECT_FALSE(markerExists());
    EXPECT_TRUE(flagExists());
    EXPECT_TRUE(legacyExists());
}

TEST(AgentController, SimulationIntegration) {
    details::g_is_service = true;
    ON_OUT_OF_SCOPE(details::g_is_service = false;);
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    fs::copy(fs::path{"c:\\windows\\system32\\whoami.exe"},
             temp_fs->root() / cfg::files::kAgentCtl);
    const auto service = fs::path{cfg::GetRootDir()} / "cmd.exe";
    const auto expected =
        fs::path{cfg::GetUserBinDir()} / cfg::files::kAgentCtl;
    EXPECT_TRUE(ac::StartAgentController(service));
    EXPECT_TRUE(fs::exists(expected));
    EXPECT_TRUE(ac::KillAgentController(service));
    EXPECT_FALSE(fs::exists(expected));
}
}  // namespace cma::ac
