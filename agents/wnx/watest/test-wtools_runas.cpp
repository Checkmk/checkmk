// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <vector>

#include "cma_core.h"
#include "common/wtools.h"
#include "common/wtools_runas.h"
#include "test_tools.h"

namespace wtools::runas {  // to become friendly for cma::cfg classes

extern void test();

static bool WaitForExit(uint32_t pid) {
    for (int i = 0; i < 20; i++) {
        auto [code, error] = GetProcessExitCode(pid);
        if (code == 0) return true;
        cma::tools::sleep(100);
    }
    return false;
}

static std::string ReadFromHandle(HANDLE h) {
    HANDLE handles[] = {h};
    auto ready_ret = ::WaitForMultipleObjects(1, handles, FALSE, 500);

    if (ready_ret != WAIT_OBJECT_0) return {};

    auto buf = cma::tools::ReadFromHandle<std::vector<char>>(handles[0]);
    EXPECT_TRUE(!buf.empty());
    if (buf.empty()) return {};

    buf.emplace_back(0);
    return reinterpret_cast<char*>(buf.data());
}

TEST(WtoolsRunAs, Base) {
    using namespace std::chrono_literals;
    using namespace std::string_literals;
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

    {
        wtools::AppRunner ar;
        auto ret = ar.goExecAsJobAndUser(L"a1", L"a1",
                                         (in / "runc.cmd").wstring() + L" 1");
        EXPECT_TRUE(ret);
        ASSERT_TRUE(WaitForExit(ar.processId()));
        auto data = ReadFromHandle(ar.getStdioRead());
        ASSERT_TRUE(!data.empty());
        EXPECT_EQ("a1\r\nmarker 1\r\n", data);
    }
    //
}
}  // namespace wtools::runas
