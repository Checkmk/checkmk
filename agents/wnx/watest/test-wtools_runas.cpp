// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <vector>

#include "cma_core.h"
#include "common/wtools.h"
#include "common/wtools_runas.h"
#include "common/wtools_user_control.h"
#include "test_tools.h"
using namespace std::chrono_literals;
using namespace std::string_literals;

namespace wtools::runas {  // to become friendly for cma::cfg classes

static bool WaitForExit(uint32_t pid) {
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

static std::string ReadFromHandle(HANDLE h) {
    HANDLE handles[] = {h};
    auto ready_ret = ::WaitForMultipleObjects(1, handles, FALSE, 500);

    if (ready_ret != WAIT_OBJECT_0) return {};

    auto buf = wtools::ReadFromHandle(handles[0]);
    EXPECT_TRUE(!buf.empty());
    if (buf.empty()) return {};

    buf.emplace_back(0);
    return reinterpret_cast<char *>(buf.data());
}

TEST(WtoolsRunAs, NoUser_Integration) {
    cma::OnStartTest();
    auto [in, out] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    tst::CreateWorkFile(in / "runc.cmd",
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo %USERNAME%\n"
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo marker %1");
    //
    // test();
    {
        wtools::AppRunner ar;
        auto ret = ar.goExecAsJob((in / "runc.cmd 1").wstring());
        EXPECT_TRUE(ret);
        ASSERT_TRUE(WaitForExit(ar.processId()));
        auto data = ReadFromHandle(ar.getStdioRead());
        ASSERT_TRUE(!data.empty());
        EXPECT_EQ(cma::tools::win::GetEnv("USERNAME"s) + "\r\nmarker 1\r\n",
                  data);
    }
}

TEST(WtoolsRunAs, TestUser_Integration) {
    XLOG::setup::DuplicateOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false));
    wtools::uc::LdapControl lc;
    auto pwd = GenerateRandomString(12);
    std::wstring user = L"a1";
    auto status = lc.userAdd(user, pwd);
    if (status == uc::Status::exists) {
        status = lc.changeUserPassword(user, pwd);
    }
    if (status != uc::Status::success) {
        GTEST_SKIP() << "failed to set password, maybe not admin?";
    }

    cma::OnStartTest();
    auto [in, out] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    tst::CreateWorkFile(in / "runc.cmd",
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo %USERNAME%\n"
                        "@powershell  Start-Sleep -Milliseconds 150\n"
                        "@echo marker %1");

    // Allow Users to use the file
    EXPECT_TRUE(wtools::ChangeAccessRights(
        (in / "runc.cmd").wstring().c_str(), SE_FILE_OBJECT, L"a1",
        TRUSTEE_IS_NAME, STANDARD_RIGHTS_ALL | GENERIC_ALL, GRANT_ACCESS,
        OBJECT_INHERIT_ACE));

    wtools::AppRunner ar;

    auto ret =
        ar.goExecAsJobAndUser(user, pwd, (in / "runc.cmd").wstring() + L" 1");
    ASSERT_TRUE(ret)
        << "password is invalid or expired or you have problems with Access rights";
    auto b = WaitForExit(ar.processId());
    if (!b) {
        XLOG::SendStringToStdio("Retry waiting for the process\n",
                                XLOG::Colors::yellow);
        WaitForExit(ar.processId());  // we are starting waiter two times
    }
    ASSERT_TRUE(b);
    auto data = ReadFromHandle(ar.getStdioRead());
    ASSERT_TRUE(!data.empty());
    EXPECT_EQ("a1\r\nmarker 1\r\n", data);
}
}  // namespace wtools::runas
