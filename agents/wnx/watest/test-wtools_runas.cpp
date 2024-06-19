// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <vector>

#include "common/wtools.h"
#include "common/wtools_runas.h"
#include "common/wtools_user_control.h"
#include "watest/test_tools.h"
#include "wnx/cma_core.h"
using namespace std::chrono_literals;
using namespace std::string_literals;
namespace fs = std::filesystem;

namespace wtools::runas {

namespace {
bool WaitForExit(uint32_t pid) {
    for (int i = 0; i < 100; i++) {
        auto [code, error] = GetProcessExitCode(pid);
        if (code == 0) {
            return true;
        }
        fmt::print(" Code = {}, error = {}\n", code, error);
        cma::tools::sleep(100);
    }
    return false;
}

std::string ReadFromHandle(HANDLE h) {
    HANDLE handles[] = {h};
    const auto ready_ret = ::WaitForMultipleObjects(1, handles, FALSE, 500);

    if (ready_ret != WAIT_OBJECT_0) {
        return {};
    }

    auto buf = wtools::ReadFromHandle(handles[0]);
    EXPECT_TRUE(!buf.empty());
    if (buf.empty()) {
        return {};
    }

    buf.emplace_back(0);
    return buf.data();
}
}  // namespace

TEST(WtoolsRunAs, NoUser_Component) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    auto in = temp_fs->data();
    tst::CreateWorkFile(in / "runc.cmd",
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo %USERNAME%\n"
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo marker %1");
    wtools::AppRunner ar;
    EXPECT_TRUE(ar.goExecAsJob((in / "runc.cmd 1").wstring()));
    ASSERT_TRUE(WaitForExit(ar.processId()));
    auto data = ReadFromHandle(ar.getStdioRead());
    EXPECT_EQ(cma::tools::win::GetEnv("USERNAME"s) + "\r\nmarker 1\r\n", data);
}

class WtoolsRunAsFixture : public ::testing::Test {
public:
    void SetUp() override {
        user_ = L"a1" + fmt::format(L"_{}", ::GetCurrentProcessId());
        pwd_ = GenerateRandomString(12);
    }

    void TearDown() override { std::ignore = lc_.userDel(user_); }

    fs::path TempDir() const { return temp_dir_.in(); }
    uc::Status DelUser(const std::wstring_view user) const {
        return lc_.userDel(user);
    }
    uc::Status AddUser(const std::wstring_view user,
                       const std::wstring pwd) const {
        return lc_.userAdd(user, pwd);
    }
    std::wstring User() const { return user_; }
    std::wstring Pwd() const { return pwd_; }
    uc::Status ChangePwd() {
        pwd_ = GenerateRandomString(12);
        return lc_.changeUserPassword(User(), Pwd());
    }

private:
    uc::LdapControl lc_;
    std::wstring pwd_;
    std::wstring user_;
    tst::TempDirPair temp_dir_{"WtoolsRunAs"};
};

TEST_F(WtoolsRunAsFixture, TestUser_ComponentExt) {
    std::ignore = DelUser(User());  // silently del old trash

    if (AddUser(User(), Pwd()) != uc::Status::success) {
        GTEST_SKIP() << "failed to set password, maybe not admin?";
    }
    const auto old_pwd = Pwd();
    ASSERT_EQ(AddUser(User(), Pwd()), uc::Status::exists);

    const auto in = TempDir();
    const auto batch_file = in / "runc.cmd";
    tst::CreateWorkFile(batch_file,
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo %USERNAME%\n"
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo marker %1");
    // new password
    ASSERT_EQ(ChangePwd(), uc::Status::success);
    const auto new_pwd = Pwd();
    ASSERT_NE(old_pwd, new_pwd);

    // Allow Users to use the file
    // Must be done for testing. Plugin Engine must use own method to allow
    // execution
    // VALIDATE ALSO MANUALLY: script is complicated
    EXPECT_TRUE(wtools::ChangeAccessRights(batch_file, User(),
                                           STANDARD_RIGHTS_ALL | GENERIC_ALL,
                                           GRANT_ACCESS, OBJECT_INHERIT_ACE));

    wtools::AppRunner ar;

    // wrong password
    const auto fail =
        ar.goExecAsJobAndUser(User(), old_pwd, batch_file.wstring() + L" 1");
    ASSERT_FALSE(fail)
        << "password must be invalid or expired or you have problems with Access rights";

    // good password
    const auto success =
        ar.goExecAsJobAndUser(User(), new_pwd, batch_file.wstring() + L" 1");
    ASSERT_TRUE(success)
        << "password is invalid or expired or you have problems with Access rights";
    const auto b = WaitForExit(ar.processId());
    if (!b) {
        XLOG::SendStringToStdio("Retry waiting for the process\n",
                                XLOG::Colors::yellow);
        WaitForExit(ar.processId());  // we are starting waiter two times
    }
    ASSERT_TRUE(b);
    const auto data = ReadFromHandle(ar.getStdioRead());
    EXPECT_EQ(wtools::ToUtf8(User()) + "\r\nmarker 1\r\n", data);
}
}  // namespace wtools::runas
