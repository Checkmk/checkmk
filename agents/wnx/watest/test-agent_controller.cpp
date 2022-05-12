// test-service.cpp

//
#include "pch.h"

#include <filesystem>
#include <numeric>
#include <ranges>

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

using namespace std::chrono_literals;
namespace fs = std::filesystem;
namespace rs = std::ranges;
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
              fmt::format("x daemon --agent-channel {} -vv",
                          cfg::defaults::kControllerAgentChannelDefault));
}

class AgentControllerCreateToml : public ::testing::Test {
public:
    void SetUp() override { temp_fs_ = tst::TempCfgFs::Create(); }

    void TearDown() override { killArtifacts(); }

    std::vector<std::string> loadConfigAndGetResult(const std::string &cfg) {
        if (!temp_fs_->loadContent(cfg)) {
            return {};
        }
        ac::CreateTomlConfig(tomlFile());
        return tst::ReadFileAsTable(tomlFile());
    }

    void killArtifacts() {
        std::error_code ec;
        fs::remove(tomlFile(), ec);
    }
    fs::path tomlFile() const { return tst::GetTempDir() / "the_file.toml"; }

    // "allowed_ip = [x,b,z]" -> ["x","b","z"]
    static std::vector<std::string> convertTomlToIps(
        std::string_view toml_statement) {
        std::string all{toml_statement};
        rs::replace_if(
            all, [](const char c) { return c == '='; }, ':');
        auto yaml = YAML::Load(all);
        auto actual_ips = yaml["allowed_ip"];
        std::vector<std::string> actual;
        rs::transform(actual_ips, std::back_inserter(actual),
                      [](const YAML::Node &n) { return n.as<std::string>(); });
        return actual;
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(AgentControllerCreateToml, Port) {
    auto table =
        loadConfigAndGetResult(fmt::format("global:\n"
                                           "  enabled: yes\n"
                                           "  only_from: \n"
                                           "  port: {}\n",
                                           port));
    for (auto index : {0, 1, 2}) {
        EXPECT_EQ(table[index][0], '#');
    }
    EXPECT_TRUE(table[3].empty());
    EXPECT_EQ(table[4], fmt::format("pull_port = {}", port));
}

TEST_F(AgentControllerCreateToml, PortAndAllowed) {
    auto table =
        loadConfigAndGetResult(fmt::format("global:\n"
                                           "  enabled: yes\n"
                                           "  only_from: {}\n"
                                           "  port: {}\n",
                                           allowed, port));
    for (auto index : {0, 1, 2}) {
        EXPECT_EQ(table[index][0], '#');
    }
    EXPECT_TRUE(table[3].empty());
    EXPECT_EQ(table[4], fmt::format("pull_port = {}", port));

    auto all = std::accumulate(
        table.begin() + 5, table.end(), std::string{},
        [](const std::string &a, const std::string &b) -> std::string {
            return a + b;
        });
    auto actual_ips = convertTomlToIps(all);
    auto expected_ips = tools::SplitString(std::string{allowed}, " ");
    EXPECT_TRUE(rs::is_permutation(actual_ips, expected_ips));
    EXPECT_EQ(actual_ips.size(), expected_ips.size());
}

TEST(AgentController, BuildCommandLineAgentChannelOk) {
    std::tuple<std::string, uint16_t, std::string_view> mapping[] = {
        {"ll:12345", 12345, "ll:12345"},
        {"ll:999", kWindowsInternalPort,
         cfg::defaults::kControllerAgentChannelDefault},
        {"ll:-1", kWindowsInternalPort,
         cfg::defaults::kControllerAgentChannelDefault},
    };
    for (const auto &e : mapping) {
        auto temp_fs = tst::TempCfgFs::CreateNoIo();
        ASSERT_TRUE(
            temp_fs->loadContent(fmt::format("global:\n"
                                             "  enabled: yes\n"
                                             "system:\n"
                                             "  controller:\n"
                                             "    run: yes\n"
                                             "    agent_channel: {}\n",
                                             std::get<0>(e))));
        EXPECT_EQ(
            wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
            fmt::format("x daemon --agent-channel {} -vv", std::get<2>(e)));
        EXPECT_EQ(GetConfiguredAgentChannelPort(), std::get<1>(e));
    }
}

TEST(AgentController, BuildCommandLineAgentChannelMalformed) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "system:\n"
                                         "  controller:\n"
                                         "    run: yes\n"
                                         "    agent_channel: ll\n")));
    EXPECT_EQ(wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
              fmt::format("x daemon --agent-channel {} -vv",
                          cfg::defaults::kControllerAgentChannelDefault));
    EXPECT_EQ(GetConfiguredAgentChannelPort(), kWindowsInternalPort);
}

TEST(AgentController, BuildCommandLineAllowed) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "  only_from: {}\n"
                                         "  port: {}\n",
                                         allowed, port)));
    EXPECT_EQ(wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
              fmt::format("x daemon --agent-channel {} -vv",
                          cfg::defaults::kControllerAgentChannelDefault));
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

namespace {
bool IsLegacyFileExists() {
    std::error_code ec;
    return fs::exists(ac::LegacyPullFile(), ec);
}

void CleanArtifacts() {
    std::error_code ec;
    fs::remove(ac::LegacyPullFile(), ec);
    fs::remove(ac::ControllerFlagFile(), ec);
    fs::remove(ac::ControllerFlagFile(), ec);
}
constexpr auto marker_new =
    "Check MK monitoring and management Service - 2.1, 64-bit";
constexpr auto marker_old =
    "Check MK monitoring and management Service, 64-bit";

}  // namespace

TEST(AgentController, CreateLegacyPullFile) {
    constexpr auto config_str =
        "global:\n"
        "  enabled: yes\n"
        "system:\n"
        "  controller:\n"
        "    run: {}\n"
        "    force_legacy: {}\n";
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_FALSE(ac::IsLegacyFileExists());
    struct Param {
        std::string run;
        std::string force_legacy;
        std::string marker;
        bool exists;
    };
    // NOTE(sk): better to have std::array, but init is a mess
    Param params[] = {
        {.run = "no",
         .force_legacy = "no",
         .marker = marker_old,
         .exists = false},
        {.run = "no",
         .force_legacy = "yes",
         .marker = marker_old,
         .exists = false},
        {.run = "yes",
         .force_legacy = "no",
         .marker = marker_old,
         .exists = true},
        {.run = "yes",
         .force_legacy = "no",
         .marker = marker_new,
         .exists = true},
        {.run = "yes",
         .force_legacy = "yes",
         .marker = marker_old,
         .exists = true},
    };
    for (auto const &p : params) {
        auto to_load = fmt::format(config_str, p.run, p.force_legacy);
        ASSERT_TRUE(temp_fs->loadContent(to_load));
        ac::CreateArtifacts("", p.run == "yes");
        EXPECT_EQ(ac::IsLegacyFileExists(), p.exists)
            << "conf str is " << to_load;
        CleanArtifacts();
    }
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
    static constexpr std::string_view marker_2_1 = marker_new;
    static constexpr std::string_view marker_1_6_2_0 = marker_old;
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
