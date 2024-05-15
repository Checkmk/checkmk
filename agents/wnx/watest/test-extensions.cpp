//
// modules tests
//
//
#include "pch.h"

#include "watest/test_tools.h"
#include "wnx/extensions.h"

using namespace std::chrono_literals;

namespace fs = std::filesystem;

namespace cma::cfg::extensions {

TEST(Extensions, GetAll) {
    const auto temp_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    const auto cfg = GetLoadedConfig();
    const auto extensions = GetAll(cfg);
    ASSERT_EQ(extensions.size(), 1);
    EXPECT_EQ(extensions[0].binary, "$CUSTOM_AGENT_PATH$/bin/robotmk_ext.exe");
    EXPECT_EQ(extensions[0].command_line, "daemon");
    EXPECT_EQ(extensions[0].name, "robot_mk");
    EXPECT_EQ(extensions[0].mode, Mode::automatic);
}

std::pair<fs::path, fs::path> MakePowershellFileAndLog(const fs::path &dir) {
    tst::CreateTextFile(dir / "exec.ps1", fmt::format(R"#(
while ($true)
{{
    Add-Content -Path {} -Value (Get-Date)
    start-sleep 1
}}
)#",
                                                      dir / "exec.log"));
    return {dir / "exec.ps1", dir / "exec.log"};
}

TEST(Extensions, FindBinary) {
    EXPECT_EQ(FindBinary("powerShell"), "powershell.exe");
    EXPECT_EQ(FindBinary("powerShell.exE"), "powershell.exe");
    EXPECT_EQ(FindBinary("powerShel-l"), "powerShel-l");
}

/// Test may require a lot of time to complete
TEST(Extensions, ExtensionsManagerComponent) {
    const tst::TempDirPair temp{tst::GetUnitTestName()};
    {
        const auto &[ps1, log] = MakePowershellFileAndLog(temp.in());
        std::vector<Extension> extensions;
        extensions.emplace_back(Extension{
            .name = "test",
            .binary = "powershell.exe",
            .command_line =
                fmt::format("-ExecutionPolicy ByPass -File {}", ps1),
            .mode = Mode::yes,
        });

        ExtensionsManager em(extensions, 1, std::nullopt);

        EXPECT_TRUE(tst::WaitForSuccessSilent(5000ms, [&]() {
            return !em.processes().empty() &&
                   wtools::FindProcessByPathEndAndPid(em.processes()[0].path,
                                                      em.processes()[0].pid);
        }));
        EXPECT_TRUE(fs::exists(fs::path{GetTempDir()} / "test.run"));

        wtools::KillProcessesByPathEndAndPid(em.processes()[0].path,
                                             em.processes()[0].pid);

        EXPECT_TRUE(tst::WaitForSuccessSilent(5000ms, [&]() {
            return !wtools::FindProcessByPathEndAndPid(em.processes()[0].path,
                                                       em.processes()[0].pid);
        }));

        EXPECT_TRUE(tst::WaitForSuccessSilent(10000ms, [&]() {
            return wtools::FindProcessByPathEndAndPid(em.processes()[0].path,
                                                      em.processes()[0].pid);
        }));
    }
    EXPECT_FALSE(fs::exists(fs::path{GetTempDir()} / "test.run"));
}

}  // namespace cma::cfg::extensions
