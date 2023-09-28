// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <string>  // for string

#include "providers/mrpe.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"

namespace fs = std::filesystem;
using namespace std::chrono_literals;

/*
Typic output:

<<<mrpe>>>
(mode.com) Console 0 Status von Gert CON: 1 --------------------- 1
Codepage:        437 (chcp.com) sk 1 Geben Sie das Kennwort fuer "sk" ein:
*/

namespace cma::provider {  // to become friendly for wtools classes

namespace {
void SetMrpeConfig(const std::vector<std::string> &vec) {
    constexpr std::string_view group = cfg::groups::kMrpe;
    constexpr std::string_view section = cfg::vars::kMrpeConfig;
    auto yaml = cfg::GetLoadedConfig();
    for (size_t i = 0; i < yaml[group][section].size(); i++)
        yaml[group][section].remove(0);

    yaml[group][section].reset();

    for (const auto &str : vec) {
        yaml[group][section].push_back(str);
    }
}
}  // namespace

class SectionProviderMrpeFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(
            temp_fs_->loadContent("global:\n"
                                  "  enabled: yes\n"
                                  "  sections:\n"
                                  "  - mrpe\n"
                                  "  logging:\n"
                                  "    debug: all\n"
                                  "    windbg: yes\n"
                                  "mrpe:\n"
                                  "  enabled: yes\n"
                                  "  parallel: no\n"
                                  "  timeout: 60\n"
                                  "  config:\n"));
    }

    static void PrepareRunTest() {
        SetMrpeConfig({
            R"(check = Codepage 'c:\windows\system32\chcp.com')",
            R"(check = Console 'c:\windows\system32\mode.com' CON CP /STATUS)",
        });
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(SectionProviderMrpeFixture, Construction) {
    MrpeProvider mrpe;
    EXPECT_TRUE(mrpe.checks().empty());
    EXPECT_TRUE(mrpe.entries().empty());
    EXPECT_TRUE(mrpe.includes().empty());
    EXPECT_TRUE(mrpe.generateContent().empty());
}

TEST_F(SectionProviderMrpeFixture, CheckConfigTimeout) {
    MrpeProvider mrpe;
    mrpe.loadConfig();
    ASSERT_EQ(mrpe.timeout(), 60);
}

TEST_F(SectionProviderMrpeFixture, RunCachedComponent_DISABLED) {
    MrpeProvider mrpe;
    auto yaml = cfg::GetLoadedConfig();

    SetMrpeConfig({
        R"(check = Time 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' Get-Date -Format HHmmssffff)",
        R"(check = CachedTime (interval=10) 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' Get-Date -Format HHmmssffff)",
        R"(check = LegacyCachedTime (20:no) 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' Get-Date -Format HHmmssffff)",
    });

    auto strings =
        cfg::GetArray<std::string>(cfg::groups::kMrpe, cfg::vars::kMrpeConfig);
    EXPECT_EQ(strings.size(), 3);
    mrpe.loadConfig();
    ASSERT_EQ(mrpe.includes().size(), 0);
    ASSERT_EQ(mrpe.checks().size(), 3);

    EXPECT_EQ(mrpe.entries().size(), 3);
    mrpe.updateSectionStatus();

    yaml[cfg::groups::kMrpe][cfg::vars::kMrpeParallel] = false;
    const auto accu = mrpe.generateContent();
    ASSERT_TRUE(!accu.empty());
    auto table = tools::SplitString(accu, "\n");
    EXPECT_EQ(table[0], "<<<mrpe>>>");

    // expect "(powershell.exe) Time 0 TIMESTAMP"
    auto result_1 = tools::SplitString(table[1], " ");
    auto mrpe_1 = mrpe.entries()[0];
    EXPECT_EQ(result_1.size(), 4);
    EXPECT_EQ(result_1[0], fmt::format("({})", mrpe_1.exe_name_));
    EXPECT_EQ(result_1[1], mrpe_1.description_);
    EXPECT_EQ(result_1[2], "0");
    auto &time_1 = result_1[3];
    std::cout << time_1 << std::endl;

    // expect "cached(TIME_SINCE_EPOCH,10) (powershell.exe) CachedTime 0
    // TIMESTAMP"
    auto result_2 = tools::SplitString(table[2], " ");
    auto mrpe_2 = mrpe.entries()[1];
    EXPECT_EQ(result_2.size(), 5);
    EXPECT_EQ(result_2[0].find("cached("), 0);
    EXPECT_EQ(result_2[0].find(",10)"), result_2[0].size() - 4);
    EXPECT_EQ(result_2[1], fmt::format("({})", mrpe_2.exe_name_));
    EXPECT_EQ(result_2[2], mrpe_2.description_);
    EXPECT_EQ(result_2[3], "0");
    auto &time_2 = result_2[4];

    // expect "cached(TIME_SINCE_EPOCH,10) (powershell.exe) LegacyCachedTime 0
    // TIMESTAMP"
    auto result_3 = tools::SplitString(table[3], " ");
    auto mrpe_3 = mrpe.entries()[2];
    EXPECT_EQ(result_3.size(), 5);
    EXPECT_EQ(result_3[0].find("cached("), 0);
    EXPECT_EQ(result_3[0].find(",20)"), result_3[0].size() - 4);
    EXPECT_EQ(result_3[1], fmt::format("({})", mrpe_3.exe_name_));
    EXPECT_EQ(result_3[2], mrpe_3.description_);
    EXPECT_EQ(result_3[3], "0");
    auto &time_3 = result_3[4];

    tools::sleep(10);

    // expect TIMESTAMP to change for first check, while the other two are
    // cached and stay unchanged
    auto second_run = mrpe.generateContent();
    auto second_table = tools::SplitString(second_run, "\n");
    EXPECT_TRUE(time_1 != tools::SplitString(second_table[1], " ")[3]);
    EXPECT_TRUE(time_2 == tools::SplitString(second_table[2], " ")[4]);
    EXPECT_TRUE(time_3 == tools::SplitString(second_table[3], " ")[4]);
}

TEST_F(SectionProviderMrpeFixture, RunDefault) {
    PrepareRunTest();

    MrpeProvider mrpe;
    mrpe.loadConfig();
    ASSERT_EQ(mrpe.includes().size(), 0);
    ASSERT_EQ(mrpe.checks().size(), 2);

    EXPECT_EQ(mrpe.entries().size(), 2);
    mrpe.updateSectionStatus();

    auto table = tools::SplitString(mrpe.generateContent(), "\n");
    EXPECT_EQ(table[0], "<<<mrpe>>>");
    table.erase(table.begin());
    ASSERT_EQ(table.size(), 2);

    auto e0 = mrpe.entries()[0];
    auto hdr0 = fmt::format("({}) {} 0", e0.exe_name_, e0.description_);
    EXPECT_TRUE(table[0].starts_with(hdr0));

    auto e1 = mrpe.entries()[1];
    auto hdr1 = fmt::format("({}) {} 0", e1.exe_name_, e1.description_);
    EXPECT_TRUE(table[1].starts_with(hdr1));
}

TEST_F(SectionProviderMrpeFixture, RunParallel) {
    PrepareRunTest();

    MrpeProvider mrpe;
    mrpe.loadConfig();
    mrpe.updateSectionStatus();

    auto yaml = cfg::GetLoadedConfig();
    yaml[cfg::groups::kMrpe][cfg::vars::kMrpeParallel] = true;

    auto table = tools::SplitString(mrpe.generateContent(), "\n");
    table.erase(table.begin());
    ASSERT_EQ(table.size(), 2);

    auto e0 = mrpe.entries()[0];
    auto hdr0 = fmt::format("({}) {} 0", e0.exe_name_, e0.description_);

    auto e1 = mrpe.entries()[1];
    auto hdr1 = fmt::format("({}) {} 0", e1.exe_name_, e1.description_);
    EXPECT_TRUE(table[0].starts_with(hdr0) || table[1].starts_with(hdr0));
    EXPECT_TRUE(table[0].starts_with(hdr1) || table[1].starts_with(hdr1));
}

class SectionProviderMrpeConfigFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(temp_fs_->loadFactoryConfig());
        tst::CreateWorkFile(
            std::filesystem::path{cfg::GetUserDir()} / "mrpe_checks.cfg",
            R"(check = Type 'c:\windows\system32\chcp.com')");
        SetMrpeConfig(
            {R"(check = Console 'c:\windows\system32\mode.com' CON CP /STATUS)",
             R"(include sk = $CUSTOM_AGENT_PATH$\mrpe_checks.cfg)",  // reference
             R"(Include=$CUSTOM_AGENT_PATH$\mrpe_checks.cfg)",       // no space
             R"(include  =   'mrpe_checks.cfg')",                    //
             R"(includes = $CUSTOM_AGENT_PATH$\mrpe_checks.cfg)",    // invalid
             R"(includ = $CUSTOM_AGENT_PATH$\mrpe_checks.cfg)",      // invalid
             R"(chck = Console 'c:\windows\system32\mode.com' CON CP /STATUS)",  // invalid
             R"(check = 'c:\windows\system32\mode.com' CON CP /STATUS)"});  // valid
    }

    static void PrepareRunTest() {
        SetMrpeConfig({
            R"(check = Codepage 'c:\windows\system32\chcp.com')",
            R"(check = Console 'c:\windows\system32\mode.com' CON CP /STATUS)",
        });
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(SectionProviderMrpeConfigFixture, Load) {
    MrpeProvider mrpe;
    mrpe.loadConfig();
    ASSERT_EQ(mrpe.includes().size(), 3);
    mrpe.loadConfig();
    ASSERT_EQ(mrpe.includes().size(), 3);
    EXPECT_EQ(mrpe.includes()[0],
              R"(sk = $CUSTOM_AGENT_PATH$\mrpe_checks.cfg)");
    EXPECT_EQ(mrpe.includes()[1], R"(=$CUSTOM_AGENT_PATH$\mrpe_checks.cfg)");
    EXPECT_EQ(mrpe.includes()[2], "=   'mrpe_checks.cfg'");
    ASSERT_EQ(mrpe.checks().size(), 2);
    EXPECT_EQ(mrpe.checks()[0],
              R"(Console 'c:\windows\system32\mode.com' CON CP /STATUS)");
    EXPECT_EQ(mrpe.checks()[1],
              R"('c:\windows\system32\mode.com' CON CP /STATUS)");

    EXPECT_EQ(mrpe.includes().size(), 3);
    EXPECT_EQ(mrpe.checks().size(), 2);
    EXPECT_EQ(mrpe.entries().size(), kMrpeRemoveAbsentFiles ? 4 : 5);
}

namespace {
auto CreateMrpeFiles(const fs::path &cfg_dir, const fs::path &file_dir) {
    const auto mrpe_file_1 =
        tst::CreateWorkFile(file_dir / "mrpe1.bat", "@echo output_of_mrpe1");

    const auto mrpe_file_2 =
        tst::CreateWorkFile(file_dir / "mrpe2.bat", "@echo output_of_mrpe2");

    const auto text = fmt::format(
        "# a\n"
        "  ;\n"  // expected clean
        "check = Type '{}'\n"
        "\n"
        "check = Type '{}'\n"
        "check = BadFile 'sss.bat'\n",
        mrpe_file_1, mrpe_file_2);

    auto cfg_file = tst::CreateWorkFile(cfg_dir / "mrpe_check.cfg", text);
    return std::make_tuple(cfg_file, mrpe_file_1, mrpe_file_2);
}
}  // namespace

TEST(SectionProviderMrpe, ProcessCfg) {
    tst::TempDirPair dirs{test_info_->name()};
    auto [cfg_file, mrpe_file_1, mrpe_file_2] =
        CreateMrpeFiles(dirs.in(), dirs.out());

    std::vector<MrpeEntry> entries;
    AddCfgFileToEntries("", cfg_file, entries);

    ASSERT_EQ(entries.size(), 3);
    EXPECT_EQ(entries[0].command_line_, mrpe_file_1.u8string());
    EXPECT_EQ(entries[1].command_line_, mrpe_file_2.u8string());
    std::filesystem::path missing = cfg::GetUserDir();
    missing /= "sss.bat";
    EXPECT_EQ(entries[2].command_line_, missing.u8string());
    auto result_1 = ExecMrpeEntry(entries[0], 10s);
    EXPECT_FALSE(result_1.empty());

    auto table_1 = tools::SplitString(result_1, " ");
    EXPECT_EQ(table_1.size(), 4);
    EXPECT_EQ(table_1[0],
              std::string("(") + wtools::ToStr(mrpe_file_1.filename()) + ")");
    EXPECT_EQ(table_1[1], "Type");
    EXPECT_EQ(table_1[2], "0");
    EXPECT_EQ(table_1[3], "output_of_mrpe1");

    auto result_2 = ExecMrpeEntry(entries[1], 10s);
    auto table_2 = tools::SplitString(result_2, " ");
    EXPECT_FALSE(result_2.empty());
    EXPECT_EQ(table_2.size(), 4);
    EXPECT_EQ(table_2[0],
              std::string("(") + wtools::ToStr(mrpe_file_2.filename()) + ")");
    EXPECT_EQ(table_2[1], "Type");
    EXPECT_EQ(table_2[2], "0");
    EXPECT_EQ(table_2[3], "output_of_mrpe2");

    auto result_missing = ExecMrpeEntry(entries[2], 10s);
    EXPECT_FALSE(result_missing.empty());
    auto table_missing = tools::SplitString(result_missing, " ", 3);
    EXPECT_EQ(table_missing.size(), 4);
    EXPECT_EQ(table_missing[0], "(sss.bat)");
    EXPECT_EQ(table_missing[1], "BadFile");
    EXPECT_EQ(table_missing[2], "3");
    EXPECT_EQ(table_missing[3], "Unable to execute - plugin may be missing.");
}

TEST(SectionProviderMrpe, CtorDefault) {
    const std::string base = R"(Codepage 'c:\windows\system32\chcp.com' x d f)";
    const MrpeEntry me("", base);
    EXPECT_EQ(me.exe_name_, "chcp.com");
    EXPECT_EQ(me.full_path_name_, R"(c:\windows\system32\chcp.com)");
    EXPECT_EQ(me.command_line_, R"(c:\windows\system32\chcp.com x d f)");
    EXPECT_EQ(me.description_, "Codepage");
    EXPECT_FALSE(me.caching_interval_.has_value());
}

TEST(SectionProviderMrpe, CtorInterval) {
    const std::string base =
        R"(Codepage (interval=123456) 'c:\windows\system32\chcp.com' x d f)";
    const MrpeEntry me("", base);
    EXPECT_EQ(me.exe_name_, "chcp.com");
    EXPECT_EQ(me.full_path_name_, R"(c:\windows\system32\chcp.com)");
    EXPECT_EQ(me.command_line_, R"(c:\windows\system32\chcp.com x d f)");
    EXPECT_EQ(me.description_, "Codepage");
    EXPECT_EQ(*me.caching_interval_, 123456);
}

TEST(SectionProviderMrpe, Name) {
    const MrpeProvider mrpe;
    EXPECT_EQ(mrpe.getUniqName(), section::kMrpe);
}

TEST(SectionProviderMrpe, FixCrCnForMrpe) {
    std::string s = "a\rb\n\n";
    FixCrCnForMrpe(s);
    EXPECT_EQ(s, "a b\1\1");
}

TEST(SectionProviderMrpe, ParseIncludeEntry) {
    const auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    auto [u, p] =
        ParseIncludeEntry("sk = $CUSTOM_AGENT_PATH$\\mrpe_checks.cfg");
    EXPECT_EQ(u, "sk");
    EXPECT_EQ(p.u8string(),
              wtools::ToUtf8(cfg::GetUserDir()) + "\\" + "mrpe_checks.cfg");

    std::tie(u, p) =
        ParseIncludeEntry(" = $CUSTOM_AGENT_PATH$\\mpe_cecks.cfg  ");
    EXPECT_TRUE(u.empty());
    EXPECT_EQ(p.u8string(),
              wtools::ToUtf8(cfg::GetUserDir()) + "\\" + "mpe_cecks.cfg");

    std::tie(u, p) =
        ParseIncludeEntry(" = '$CUSTOM_AGENT_PATH$\\mpe_cecks.cfg'  ");
    EXPECT_TRUE(u.empty());
    EXPECT_EQ(p.u8string(),
              wtools::ToUtf8(cfg::GetUserDir()) + "\\" + "mpe_cecks.cfg");
}

}  // namespace cma::provider
