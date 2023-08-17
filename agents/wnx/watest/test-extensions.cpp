//
// modules tests
//
//
#include "pch.h"

#include "extensions.h"
#include "test_tools.h"

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

}  // namespace cma::cfg::extensions
