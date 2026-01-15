// test-wtools.cpp
// windows mostly

#include "pch.h"
// this file is fixed

#include <fmt/format.h>
#include <fmt/xchar.h>

#include <chrono>
#include <string_view>
#include <unordered_set>

#include "common/wtools.h"
#include "common/wtools_user_control.h"
#include "tools/_process.h"
#include "tools/_raii.h"
#include "watest/test_tools.h"

using namespace std::string_literals;
using namespace std::chrono_literals;
namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace {
// Internal description of assorted counter params.
// Should be valid for all windows versions
struct CounterParam {
    const wchar_t *const name_;  // usually number
    uint32_t index_;             // the same as name
    uint32_t counters_count;
    uint32_t instances_min_;
    uint32_t instances_max_;
};

constexpr CounterParam g_cpu_counter = {.name_ = L"238",
                                        .index_ = 238,
                                        .counters_count = 15,
                                        .instances_min_ = 1,
                                        .instances_max_ = 33};
constexpr CounterParam g_disk_counter = {.name_ = L"234",
                                         .index_ = 234,
                                         .counters_count = 31,
                                         .instances_min_ = 1,
                                         .instances_max_ = 16};

}  // namespace

namespace wtools {

class WtoolsKillProcFixture : public ::testing::Test {
protected:
    static constexpr std::wstring_view dirToUse() { return L"kill_dir"; }
    static constexpr std::wstring_view nameToUse() { return L"kill_proc.exe"; }

    static void KillTmpProcesses() {
        ScanProcessList([](const PROCESSENTRY32 &entry) {
            if (std::wstring{entry.szExeFile} == nameToUse()) {
                KillProcess(entry.th32ProcessID, 99);
            }
            return ScanAction::advance;
        });
    }

    [[nodiscard]] int RunProcesses(int requested) const {
        const auto cmd = fmt::format("{} -t 8.8.8.8", test_exe_);

        int count = 0;
        for (int i = 0; i < requested; i++) {
            if (cma::tools::RunDetachedCommand(cmd).has_value()) {
                count++;
            }
        }

        return count;
    }
    [[nodiscard]] std::optional<uint32_t> RunProcess() const {
        const auto cmd = fmt::format("{} -t 8.8.8.8", test_exe_);

        return cma::tools::RunDetachedCommand(cmd);
    }

    static std::tuple<std::wstring, uint32_t> FindExpectedProcess() {
        uint32_t pid = 0;
        std::wstring path;
        ScanProcessList([&](const PROCESSENTRY32 &entry) {
            if (std::wstring{entry.szExeFile} != nameToUse()) {
                return ScanAction::advance;
            }

            path = GetProcessPath(entry.th32ProcessID);
            pid = entry.th32ProcessID;
            return ScanAction::terminate;
        });

        return {path, pid};
    }

    void SetUp() override {
        test_dir_ = tst::MakeTempFolderInTempPath(dirToUse());
        test_exe_ = test_dir_ / nameToUse();
        fs::create_directories(test_dir_);
        const fs::path ping(R"(c:\windows\system32\ping.exe)");
        ASSERT_TRUE(fs::copy_file(ping, test_exe_));
    }

    void TearDown() override {
        KillTmpProcesses();
        ASSERT_NE(test_dir_.wstring().find(dirToUse()), std::wstring::npos);
        std::error_code ec;
        fs::remove_all(test_dir_, ec);
        if (ec) {
            std::cerr << fmt::format(
                "Attention: remove_all failed, some of temporary processes are busy. "
                "Exception: '{}' [{}]\n",
                ec.message(), ec.value());
        }
    }

    fs::path test_dir_;
    fs::path test_exe_;
};

TEST_F(WtoolsKillProcFixture, KillProcByPid) {
    EXPECT_EQ(RunProcesses(1), 1);
    auto [path, pid] = FindExpectedProcess();
    EXPECT_TRUE(!path.empty());
    ASSERT_NE(pid, 0);

    EXPECT_TRUE(KillProcess(pid, 1));
    cma::tools::sleep(500ms);

    auto [path_empty, pid_null] = FindExpectedProcess();
    EXPECT_TRUE(path_empty.empty());
    EXPECT_EQ(pid_null, 0);

    EXPECT_FALSE(KillProcess(pid, 1));
}

TEST_F(WtoolsKillProcFixture, KillProcsByDir) {
    EXPECT_EQ(RunProcesses(1), 1);
    ASSERT_EQ(RunProcesses(1), 1);  // additional process
    auto test_dir = test_dir_.wstring();
    cma::tools::WideUpper(test_dir);

    EXPECT_EQ(KillProcessesByDir(test_dir), 2);
    EXPECT_TRUE(tst::WaitForSuccessSilent(1500ms, []() {
        auto [path, pid] = FindExpectedProcess();
        return path.empty() && pid == 0;
    }));

    EXPECT_EQ(KillProcessesByDir(test_dir), 0);
    EXPECT_EQ(KillProcessesByDir(""), -1);
    EXPECT_EQ(KillProcessesByDir("k:"), -1);
}

TEST_F(WtoolsKillProcFixture, KillProcsByFullPath) {
    EXPECT_EQ(RunProcesses(1), 1);
    ASSERT_EQ(RunProcesses(1), 1);  // additional process
    KillProcessesByFullPath(test_exe_);
    EXPECT_TRUE(tst::WaitForSuccessSilent(1500ms, []() {
        auto [path, pid] = FindExpectedProcess();
        return path.empty() && pid == 0;
    }));
}

TEST_F(WtoolsKillProcFixture, KillProcsByFullPathAndPidComponent) {
    const auto maybe_pid = RunProcess();
    ASSERT_TRUE(maybe_pid.has_value());

    // bad pid
    {
        KillProcessesByPathEndAndPid(test_exe_.filename(), 4);
        cma::tools::sleep(500ms);
        auto [path, pid] = FindExpectedProcess();
        EXPECT_FALSE(path.empty());
        EXPECT_EQ(pid, *maybe_pid);
    }

    // bad path
    {
        KillProcessesByPathEndAndPid("aa.exe", *maybe_pid);
        cma::tools::sleep(500ms);
        auto [path, pid] = FindExpectedProcess();
        EXPECT_FALSE(path.empty());
        EXPECT_EQ(pid, *maybe_pid);
    }

    // should kill
    {
        KillProcessesByPathEndAndPid(test_exe_.filename(), *maybe_pid);
        cma::tools::sleep(500ms);
        auto [path, pid] = FindExpectedProcess();
        EXPECT_TRUE(path.empty());
        EXPECT_EQ(pid, 0);
    }
}

TEST_F(WtoolsKillProcFixture, FindProcsByFullPathAndPidComponent) {
    const auto maybe_pid = RunProcess();
    ASSERT_TRUE(maybe_pid.has_value());

    EXPECT_FALSE(FindProcessByPathEndAndPid(test_exe_.filename(), 4));
    EXPECT_TRUE(tst::WaitForSuccessSilent(5000ms, [&]() {
        return FindProcessByPathEndAndPid(test_exe_.filename(), *maybe_pid);
    })) << fmt::format("process {} not found", test_exe_.filename());
    KillProcessesByPathEndAndPid(test_exe_.filename(), *maybe_pid);
    EXPECT_TRUE(tst::WaitForSuccessSilent(5000ms, [&]() {
        return !FindProcessByPathEndAndPid(test_exe_.filename(), *maybe_pid);
    })) << fmt::format("process {} still found", test_exe_.filename());
}

class WtoolsKillProcessTreeFixture : public ::testing::Test {
protected:
    void SetUp() override {
        std::vector<std::string> names;
        temp_fs_ = tst::TempCfgFs::Create();

        ScanProcessList([&](const PROCESSENTRY32 &entry) {
            names.emplace_back(ToUtf8(entry.szExeFile));
            if (names.back() == "watest32.exe" ||
                names.back() == "watest64.exe") {
                XLOG::l.w(
                    "Suspicious '{}' pid: [{}] parent pid: [{}] current pid [{}]",
                    names.back(), entry.th32ProcessID,
                    entry.th32ParentProcessID, ::GetCurrentProcessId());
            }
            return ScanAction::advance;
        });
        EXPECT_TRUE(!names.empty());
        for (auto &name : names) {
            cma::tools::StringLower(name);
        }

        // check that we do not have own process
        EXPECT_TRUE(std::ranges::find(names, tgt::Is64bit()
                                                 ? "watest64.exe"s
                                                 : "watest32.exe"s) ==
                    names.end());
        EXPECT_TRUE(std::ranges::find(names, std::string("svchost.exe")) !=
                    names.end());
    }

    [[nodiscard]] uint32_t startProcessTree() const {
        const auto exe_a = tempDir() / "a.cmd";
        const auto exe_b = tempDir() / "b.cmd";
        const auto exe_c = tempDir() / "c.cmd";

        tst::CreateTextFile(exe_a, "@echo start\n@call " + ToStr(exe_b));
        tst::CreateTextFile(exe_b, "@echo start\n@call " + ToStr(exe_c));
        tst::CreateTextFile(exe_c,
                            "@echo start\n@powershell Start-Sleep 10000");
        return cma::tools::RunStdCommand(exe_a.wstring(),
                                         cma::tools::WaitForEnd::no)
            .value_or(0);
    }

    static [[nodiscard]] bool findProcessByPid(uint32_t pid) {
        bool found = false;
        ScanProcessList([&](const PROCESSENTRY32 &entry) {
            if (entry.th32ProcessID == pid) {
                found = true;
                return ScanAction::terminate;
            }
            return ScanAction::advance;
        });
        return found;
    }

    static [[nodiscard]] bool findProcessByParentPid(uint32_t pid) {
        bool found = false;
        ScanProcessList([&](const PROCESSENTRY32 &entry) {
            if (entry.th32ParentProcessID == pid) {
                found = true;
                return ScanAction::terminate;
            }
            return ScanAction::advance;
        });
        return found;
    }

    static std::tuple<std::wstring, uint32_t> findStartedProcess(
        uint32_t proc_id) {
        std::wstring proc_name;
        DWORD parent_process_id = 0;
        ScanProcessList([&](const PROCESSENTRY32 &entry) {
            if (entry.th32ProcessID != proc_id) {
                return ScanAction::advance;
            }
            proc_name = entry.szExeFile;
            parent_process_id = entry.th32ParentProcessID;
            return ScanAction::terminate;
        });

        return {proc_name, parent_process_id};
    }

    tst::TempCfgFs::ptr temp_fs_;
    [[nodiscard]] std::filesystem::path tempDir() const {
        return temp_fs_->data();
    }
};

TEST_F(WtoolsKillProcessTreeFixture, Component) {
    using namespace std::chrono_literals;

    // we start process tree
    const auto proc_id = startProcessTree();
    EXPECT_TRUE(proc_id != 0);
    cma::tools::sleep(200ms);

    // we check that process is running
    auto [proc_name, parent_process_id] = findStartedProcess(proc_id);

    EXPECT_TRUE(proc_name == L"cmd.exe");
    EXPECT_EQ(parent_process_id, ::GetCurrentProcessId());

    ASSERT_TRUE(tst::WaitForSuccessSilent(2000ms, [&]() {
        return findProcessByParentPid(proc_id);
    })) << "child process absent";

    // killing
    KillProcessTree(proc_id);
    cma::tools::sleep(300ms);
    EXPECT_FALSE(findProcessByParentPid(proc_id)) << "child process exists";
    KillProcess(proc_id, 99);
    cma::tools::sleep(200ms);

    EXPECT_FALSE(findProcessByPid(proc_id)) << "parent process exists";
}

TEST(Wtools, ConditionallyConvertLowLevel) {
    const std::vector<uint8_t> v1{0xFE, 0xFE};
    EXPECT_FALSE(IsVectorMarkedAsUTF16(v1));

    const std::vector<uint8_t> v2{0xFE, 0xFE, 0, 0};
    EXPECT_FALSE(IsVectorMarkedAsUTF16(v2));

    const std::vector<uint8_t> v3{0xFF, 0xFE, 0, 0};
    EXPECT_TRUE(IsVectorMarkedAsUTF16(v3));

    std::string v = "aa";
    auto data = v.data();
    data[2] = 1;  // simulate random data instead of the ending null
    AddSafetyEndingNull(v);
    data = v.data();
    EXPECT_TRUE(data[2] == '\0');
}

TEST(Wtools, ConditionallyConvert) {
    std::vector<uint8_t> a;

    auto ret = ConditionallyConvertFromUtf16(a);
    EXPECT_TRUE(ret.empty());
    a.push_back('a');
    ret = ConditionallyConvertFromUtf16(a);
    EXPECT_EQ(1, ret.size());
    EXPECT_EQ(1, strlen(ret.c_str()));
}

TEST(Wtools, ConditionallyConvertBom) {
    std::vector<uint8_t> a;

    auto ret = ConditionallyConvertFromUtf16(a);
    EXPECT_TRUE(ret.empty());
    a.push_back('\xFF');
    ret = ConditionallyConvertFromUtf16(a);
    EXPECT_EQ(1, ret.size());

    a.push_back('\xFE');
    ret = ConditionallyConvertFromUtf16(a);
    EXPECT_EQ(0, ret.size());

    constexpr auto text = L"abcde";
    const auto data = reinterpret_cast<const uint8_t *>(text);
    for (int i = 0; i < 10; ++i) {
        a.push_back(data[i]);
    }
    ret = ConditionallyConvertFromUtf16(a);
    EXPECT_EQ(5, ret.size());
    EXPECT_EQ(5, strlen(ret.c_str()));
}

TEST(Wtools, PerformanceFrequency) {
    LARGE_INTEGER freq;
    ::QueryPerformanceFrequency(&freq);

    EXPECT_EQ(QueryPerformanceFreq(), freq.QuadPart);

    LARGE_INTEGER start;
    ::QueryPerformanceCounter(&start);
    cma::tools::sleep(10);  // we need guarantie that timestamp will be changed
    const auto middle = QueryPerformanceCo();
    cma::tools::sleep(10);  // we need guarantie that timestamp will be changed
    LARGE_INTEGER end;
    ::QueryPerformanceCounter(&end);

    EXPECT_LT(start.QuadPart, middle);
    EXPECT_LT(middle, end.QuadPart);
}

TEST(Wtools, Utf16Utf8) {
    const unsigned short utf16_string[] = {0x41,   0x0448, 0x65e5,
                                           0xd834, 0xdd1e, 0};
    const auto x = ToUtf8(reinterpret_cast<const wchar_t *>(utf16_string));
    EXPECT_EQ(x.size(), 10);
}

const auto g_num_cpu = std::thread::hardware_concurrency();
namespace perf {

TEST(Wtools, PerfCpuCounter) {
    constexpr auto cur_info = g_cpu_counter;
    const auto perf_data = ReadPerformanceDataFromRegistry(cur_info.name_);
    ASSERT_TRUE(perf_data.data_);
    EXPECT_TRUE(perf_data.len_ > 1000);
    // 2. Find required object
    const auto object = FindPerfObject(perf_data, cur_info.index_);
    ASSERT_TRUE(object);
    EXPECT_EQ(object->ObjectNameTitleIndex, cur_info.index_);

    const auto instances = GenerateInstances(object);
    EXPECT_TRUE(instances.size() >= cur_info.instances_min_);
    EXPECT_TRUE(instances.size() <= cur_info.instances_max_);

    EXPECT_EQ(instances.size(), g_num_cpu + 1);
    EXPECT_EQ(instances.size(), object->NumInstances);

    const auto names = GenerateInstanceNames(object);
    EXPECT_TRUE(instances.size() == names.size());

    const auto counters = GenerateCounters(object);
    EXPECT_EQ(counters.size(), cur_info.counters_count);
    EXPECT_EQ(counters.size(), object->NumCounters);
}

TEST(Wtools, PerfDiskCounter) {
    constexpr auto cur_info = g_disk_counter;
    const auto perf_data = ReadPerformanceDataFromRegistry(cur_info.name_);
    ASSERT_TRUE(perf_data.data_);
    EXPECT_TRUE(perf_data.len_ > 1000);
    // 2. Find required object
    const auto object = FindPerfObject(perf_data, cur_info.index_);
    ASSERT_TRUE(object);
    EXPECT_EQ(object->ObjectNameTitleIndex, cur_info.index_);

    const auto instances = GenerateInstances(object);
    EXPECT_TRUE(instances.size() >= cur_info.instances_min_);
    EXPECT_TRUE(instances.size() <= cur_info.instances_max_);

    EXPECT_EQ(instances.size(), object->NumInstances);

    const auto names = GenerateInstanceNames(object);
    EXPECT_TRUE(instances.size() == names.size());

    const PERF_COUNTER_BLOCK *counter_block = nullptr;
    const auto counters = GenerateCounters(object, counter_block);
    EXPECT_EQ(counter_block, nullptr);
    EXPECT_EQ(counters.size(), cur_info.counters_count);
    EXPECT_EQ(counters.size(), object->NumCounters);
}

TEST(Wtools, PerfTs) {
    // Instance less Check
    // 8154 is "Terminal Services" perf counter without instances
    // 2066 is "Terminal Services" perf counter without instances
    auto pos = tst::g_terminal_services_indexes.cbegin();
    auto index = *pos;
    auto perf_data = ReadPerformanceDataFromRegistry(std::to_wstring(index));
    while (perf_data.data_ == nullptr || !FindPerfObject(perf_data, index)) {
        // no data or data is not valid:
        ++pos;
        ASSERT_TRUE(pos != tst::g_terminal_services_indexes.cend());
        index = *pos;
        perf_data = ReadPerformanceDataFromRegistry(std::to_wstring(index));
    }
    ASSERT_TRUE(perf_data.data_);
    EXPECT_TRUE(perf_data.len_ > 30) << "Data should be big enough";

    // 2. Find required object
    const auto object = FindPerfObject(perf_data, index);
    ASSERT_TRUE(object);
    EXPECT_EQ(object->ObjectNameTitleIndex, index);

    // Check that object instance less
    const auto instances = GenerateInstances(object);
    EXPECT_TRUE(instances.empty());

    //  Check that object is name less too
    const auto names = GenerateInstanceNames(object);
    EXPECT_TRUE(instances.size() == names.size());

    const PERF_COUNTER_BLOCK *counter_block = nullptr;
    const auto counters = GenerateCounters(object, counter_block);
    EXPECT_NE(counter_block, nullptr);
    EXPECT_EQ(counters.size(), object->NumCounters);
}

}  // namespace perf

TEST(Wtools, AppRunnerCtorDtor) {
    AppRunner app;
    EXPECT_EQ(app.exitCode(), STILL_ACTIVE);
    EXPECT_EQ(app.getCmdLine(), L"");
    EXPECT_TRUE(app.getData().empty());
    EXPECT_EQ(app.getStderrRead(), nullptr);
    EXPECT_EQ(app.getStdioRead(), nullptr);
    EXPECT_EQ(app.processId(), 0);
}

#if 0
// this is example of code how to check leaks
//
TEST(Wtools, AppRunnerRunAndSTop) {
    namespace fs = std::filesystem;
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    fs::path tempDir = cma::cfg::GetTempDir();
    std::error_code ec;

    auto exe = tempDir / "a.cmd";

    tst::CreateFile(exe, "@echo xxxxxx\n");
    for (int i = 0; i < 30; i++) {
        AppRunner app;
        app.goExec(exe.wstring(), false, true, true);
        cma::tools::sleep(1000);
    }
    EXPECT_TRUE(true);
}
#endif

TEST(Wtools, SimplePipeBase) {
    DirectPipe pipe;
    EXPECT_EQ(pipe.getRead(), nullptr);
    EXPECT_EQ(pipe.getWrite(), nullptr);

    pipe.create();
    EXPECT_NE(pipe.getRead(), nullptr);
    EXPECT_NE(pipe.getWrite(), nullptr);

    const auto write_handle = pipe.getWrite();
    const auto handle = pipe.moveWrite();
    EXPECT_EQ(pipe.getWrite(), nullptr);
    EXPECT_EQ(handle, write_handle);

    pipe.shutdown();
    EXPECT_EQ(pipe.getRead(), nullptr);
    EXPECT_EQ(pipe.getWrite(), nullptr);
}

TEST(Wtools, FindPerfIndexInRegistry) {
    auto index = perf::FindPerfIndexInRegistry(L"Zuxxx");
    EXPECT_FALSE(index.has_value());

    index = perf::FindPerfIndexInRegistry(L"Terminal Services");
    ASSERT_TRUE(index.has_value());

    EXPECT_NE(std::ranges::find(tst::g_terminal_services_indexes, *index),
              tst::g_terminal_services_indexes.end());

    index = perf::FindPerfIndexInRegistry(L"Memory");
    ASSERT_TRUE(index.has_value());
    EXPECT_EQ(index, 4);
}

TEST(Wtools, GetArgv) {
    const fs::path val{GetArgv(0)};
    EXPECT_TRUE(cma::tools::IsEqual(val.extension().wstring(), L".exe"));

    EXPECT_TRUE(GetArgv(10).empty());
}

constexpr size_t g_min_size{400'000U};

TEST(Wtools, GetOwnVirtualSize) { EXPECT_GT(GetOwnVirtualSize(), g_min_size); }

TEST(Wtools, GetCommitCharge) {
    EXPECT_GT(GetCommitCharge(GetCurrentProcessId()), g_min_size);
}

TEST(Wtools, KillTree) {
    // Safety double check
    EXPECT_FALSE(kProcessTreeKillAllowed);
}

TEST(Wtools, Acl) {
    ACLInfo info(R"(c:\windows\notepad.exe)");
    auto ret = info.query();
    ASSERT_EQ(ret, 0) << "Bad return" << fmt::format("{:#X}", ret);
    const auto stat = info.output();
    EXPECT_TRUE(!stat.empty());
}

TEST(Wtools, PatchFileLineEnding) {
    constexpr std::string_view to_write{"a\nb\r\nc\nd\n\n"};
    constexpr std::string_view expected{"a\r\nb\r\r\nc\r\nd\r\n\r\n"};

    const auto work_file = tst::GetTempDir() / "line_ending.tst";
    tst::CreateBinaryFile(work_file, to_write);

    PatchFileLineEnding(work_file);
    EXPECT_EQ(ReadWholeFile(work_file), expected);
}

TEST(Wtools, UserGroupName) {
    const auto m = cma::GetModus();
    ON_OUT_OF_SCOPE(cma::details::SetModus(m));
    EXPECT_TRUE(GenerateCmaUserNameInGroup(L"").empty());
    EXPECT_EQ(GenerateCmaUserNameInGroup(L"XX"), L"cmk_TST_XX");

    cma::details::SetModus(cma::Modus::service);
    EXPECT_EQ(GenerateCmaUserNameInGroup(L"XX"), L"cmk_in_XX");

    cma::details::SetModus(cma::Modus::integration);
    EXPECT_EQ(GenerateCmaUserNameInGroup(L"XX"), L"cmk_IT_XX");

    cma::details::SetModus(cma::Modus::app);
    EXPECT_TRUE(GenerateCmaUserNameInGroup(L"XX").empty());
}

TEST(Wtools, Registry) {
    constexpr std::wstring_view path = LR"(SOFTWARE\checkmk_tst\unit_test)";
    constexpr std::wstring_view name = L"cmk_test";

    // clean
    DeleteRegistryValue(path, name);
    EXPECT_TRUE(DeleteRegistryValue(path, name));
    ON_OUT_OF_SCOPE(DeleteRegistryValue(path, name));

    {
        constexpr uint32_t value = 2;
        constexpr uint32_t weird_value = 546'444;
        constexpr std::wstring_view str_value = L"aaa";
        ASSERT_TRUE(SetRegistryValue(path, name, value));
        EXPECT_EQ(GetRegistryValue(path, name, weird_value), value);
        EXPECT_EQ(GetRegistryValue(path, name, str_value), str_value);
        ASSERT_TRUE(SetRegistryValue(path, name, value + 1));
        EXPECT_EQ(GetRegistryValue(path, name, weird_value), value + 1);
        EXPECT_TRUE(DeleteRegistryValue(path, name));
    }

    {
        constexpr std::wstring_view expand_value{
            LR"(%ProgramFiles(x86)%\checkmk\service\)"};
        ASSERT_TRUE(SetRegistryValueExpand(path, name, expand_value));
        fs::path in_registry(GetRegistryValue(path, name, expand_value));
        fs::path expected(LR"(c:\Program Files (x86)\checkmk\service\)");
        auto in_normalized = in_registry.lexically_normal();
        auto expected_normalized = expected.lexically_normal();
        if (fs::exists(in_normalized)) {
            EXPECT_TRUE(fs::equivalent(in_normalized, expected_normalized));
        } else {
            EXPECT_TRUE(cma::tools::IsEqual(in_normalized.wstring(),
                                            expected_normalized.wstring()));
        }
    }

    {
        constexpr std::wstring_view value = L"21";
        constexpr std::wstring_view weird_value = L"_____";
        constexpr uint32_t uint_value = 123;
        ASSERT_TRUE(SetRegistryValue(path, name, value));
        EXPECT_EQ(GetRegistryValue(path, name, weird_value),
                  std::wstring(value));
        EXPECT_EQ(GetRegistryValue(path, name, uint_value), uint_value);
        EXPECT_TRUE(DeleteRegistryValue(path, name));
    }
}

TEST(Wtools, IsGoodHandleApi) {
    ASSERT_EQ(InvalidHandle(), INVALID_HANDLE_VALUE);
    EXPECT_TRUE(IsInvalidHandle(INVALID_HANDLE_VALUE));
    char c[10] = "aaa";
    const auto h = static_cast<HANDLE>(c);
    EXPECT_FALSE(IsInvalidHandle(h));
    EXPECT_FALSE(IsInvalidHandle(nullptr));

    EXPECT_FALSE(IsGoodHandle(nullptr));
    EXPECT_FALSE(IsGoodHandle(INVALID_HANDLE_VALUE));
    EXPECT_TRUE(IsGoodHandle(reinterpret_cast<HANDLE>(4)));

    EXPECT_TRUE(IsBadHandle(nullptr));
    EXPECT_TRUE(IsBadHandle(INVALID_HANDLE_VALUE));
    EXPECT_FALSE(IsBadHandle(reinterpret_cast<HANDLE>(4)));
}

TEST(Wtools, ExpandStringWithEnvironment) {
    using namespace std::string_literals;
    EXPECT_EQ(L"*Windows_NTWindows_NT*"s,
              ExpandStringWithEnvironment(L"*%OS%%OS%*"));
    EXPECT_EQ(L"%_1_2_a%"s, ExpandStringWithEnvironment(L"%_1_2_a%"));
}

TEST(Wtools, ToCanonical) {
    using cma::tools::IsEqual;
    using namespace std::string_view_literals;

    // Existing environment variable must succeed
    EXPECT_TRUE(
        IsEqual(ToCanonical(L"%systemroot%\\servicing\\TrustedInstaller.exe"),
                L"c:\\windows\\servicing\\TrustedInstaller.exe"));

    // .. should be replaced with correct path
    EXPECT_TRUE(IsEqual(
        ToCanonical(L"%systemroot%\\servicing\\..\\TrustedInstaller.exe"),
        L"c:\\windows\\TrustedInstaller.exe"));

    // Non existing environment variable must  not change
    constexpr auto no_variable{L"%temroot%\\servicing\\TrustedInstaller.exe"sv};
    EXPECT_EQ(ToCanonical(no_variable), no_variable);

    // Border value
    EXPECT_TRUE(ToCanonical(L"").empty());
}

TEST(PlayerTest, Pipe) {
    const auto p = std::make_unique<DirectPipe>();
    EXPECT_EQ(p->getRead(), nullptr);
    EXPECT_EQ(p->getWrite(), nullptr);
    p->create();
    EXPECT_NE(p->getRead(), nullptr);
    EXPECT_NE(p->getWrite(), nullptr);
}

TEST(Wtools, HandleDeleter) {
    const auto pid = ::GetCurrentProcessId();
    UniqueHandle mount;
    ASSERT_EQ(mount.get(), nullptr);
    mount.reset(::OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid));
    ASSERT_TRUE(mount.get() != nullptr);
    mount.reset();
    ASSERT_TRUE(mount.get() == nullptr);
}

TEST(Wtools, HandleDeleterInvalidAndNull) {
    const std::array handles{InvalidHandle(), HANDLE{nullptr}};
    for (auto h : handles) {
        UniqueHandle unique_handle(h);
        ASSERT_EQ(unique_handle.get(), h);
        unique_handle.reset();  // check for no crash and no throw
        ASSERT_TRUE(unique_handle.get() == nullptr) << "Current handle " << h;
    }
}

TEST(Wtools, GetMultiSz) {
    std::array<wchar_t, 12> data{L"abcde\0fgh\0\0"};
    wchar_t *pos = data.data();
    const wchar_t *end = pos + 11;
    pos = nullptr;
    EXPECT_EQ(GetMultiSzEntry(pos, end), nullptr);
    pos = data.data();
    EXPECT_EQ(GetMultiSzEntry(pos, nullptr), nullptr);
    EXPECT_EQ(std::wstring{GetMultiSzEntry(pos, end)}, L"abcde");
    EXPECT_EQ(std::wstring{GetMultiSzEntry(pos, end)}, L"fgh");
    EXPECT_EQ(GetMultiSzEntry(pos, end), nullptr);
}

TEST(Wtools, oemToUtf8) {
    EXPECT_EQ(wtools::oemToUtf8("abc"), "abc");
    EXPECT_EQ(wtools::oemToUtf8(""), "");
    EXPECT_EQ(wtools::oemToUtf8("\x84\x94\x81 \x8E\x99\x9A \xE1", 850),
              "äöü ÄÖÜ ß");
    EXPECT_NE(wtools::oemToUtf8("\x84\x94\x81 \x8E\x99\x9A \xE1", 1252),
              "äöü ÄÖÜ ß");
}

TEST(Wtools, ExecuteCommandsAsync) {
    namespace fs = std::filesystem;
    using namespace std::chrono_literals;

    auto output_file = fmt::format(L"{}cmk_test_{}.output",
                                   fs::temp_directory_path().wstring(),
                                   ::GetCurrentProcessId());
    const std::vector<std::wstring> commands{L"echo x>" + output_file,
                                             L"@echo powershell Start-Sleep 1"};
    const auto result = ExecuteCommands(L"test", commands, ExecuteMode::async);
    std::error_code ec;
    ON_OUT_OF_SCOPE({
        if (!result.empty()) {
            std::filesystem::remove(result, ec);
        }
        std::filesystem::remove(output_file, ec);
    });
    EXPECT_FALSE(result.empty());
    EXPECT_TRUE(std::filesystem::exists(result));
    const auto table = tst::ReadFileAsTable(result);
    EXPECT_EQ(table[0], ToUtf8(commands[0]));
    EXPECT_EQ(table[1], ToUtf8(commands[1]));

    tst::WaitForSuccessSilent(5000ms, [output_file] {
        std::error_code code;
        return fs::exists(output_file, code) && fs::file_size(output_file) >= 1;
    });
    const auto output = tst::ReadFileAsTable(output_file);
    EXPECT_EQ(output[0], "x");
}

TEST(Wtools, RunCommandCheck) {
    const auto s = RunCommand(L"icacls.exe /?");
    EXPECT_FALSE(s.empty());
}

TEST(Wtools, GetServiceStatus) {
    EXPECT_EQ(GetServiceStatus(L"snmptrap"), SERVICE_STOPPED);
    EXPECT_EQ(GetServiceStatus(L"vds-bad-service"), 0U);
    EXPECT_EQ(GetServiceStatus(L"SamSS"), SERVICE_RUNNING);
}

TEST(Wtools, InternalUsersDbIntegration) {
    // Power Users
    const auto group = SidToName(L"S-1-5-32-547", SidTypeGroup);
    auto group_name = group;
    rs::replace(group_name, ' ', '_');

    auto iu = std::make_unique<InternalUsersDb>();
    const auto nothing = iu->obtainUser(L"weird group");
    EXPECT_TRUE(nothing.first.empty());

    auto [name, pwd] = iu->obtainUser(group);
    if (name.empty()) {
        GTEST_SKIP() << "can't get user, admin rights?";
    }

    EXPECT_EQ(name, L"cmk_TST_"s + group_name);
    EXPECT_EQ(iu->size(), 1U);

    auto [name_2, pwd_2] = iu->obtainUser(group);
    EXPECT_TRUE(!name_2.empty());
    EXPECT_EQ(name_2, L"cmk_TST_"s + group_name);
    EXPECT_EQ(name, name_2);
    EXPECT_EQ(iu->size(), 1U);
    iu.reset();
    const uc::LdapControl lc;
    ASSERT_EQ(lc.userDel(name), uc::Status::absent);
}

TEST(Wtools, MakeSafeFolderIntegration) {
    const auto path = MakeSafeTempFolder("temp");  //
    EXPECT_TRUE(fs::exists(*path));
    fs::remove_all(*path);
}

TEST(Wtools, GetAdapterInfoStore) {
    const auto store = GetAdapterInfoStore();
    EXPECT_GE(store.size(), 1U);
    std::unordered_set<IF_OPER_STATUS> types;
    for (auto &&info : store | std::views::values) {
        types.insert(info.oper_status);
    }
    EXPECT_TRUE(types.contains(IF_OPER_STATUS::IfOperStatusUp));
    EXPECT_TRUE(types.contains(IF_OPER_STATUS::IfOperStatusDown));
}

TEST(Wtools, MangleNameForPerfCounter) {
    EXPECT_EQ(MangleNameForPerfCounter(L"abc"), L"abc");
    EXPECT_EQ(MangleNameForPerfCounter(L"/\\!@#$%^&**()__ `~'\""),
              L"__!@_$%^&**[]__ `~'\"");
}

TEST(Wtools, OsInfo) {
    const auto obtained = *GetOsInfo();
    EXPECT_TRUE(obtained.name.starts_with(L"Microsoft Windows"));
    EXPECT_TRUE(obtained.name.ends_with(L"Pro") ||      // local
                obtained.name.ends_with(L"Standard"));  // CI

    const auto num_strings = cma::tools::SplitString(obtained.version, L".");
    // 10.0.14559
    EXPECT_GE(std::stoi(num_strings[0]), 10);
    EXPECT_GE(std::stoi(num_strings[1]), 0);
    EXPECT_GE(std::stoi(num_strings[2]), 20);
}

TEST(Wtools, GetTimeAsTmBasic) {
    const auto now = std::chrono::system_clock::now();
    const auto result = GetTimeAsTm(now);

    ASSERT_TRUE(result.has_value());
    const auto &tm = result.value();

    // Basic validation - year should be reasonable
    EXPECT_GE(tm.tm_year, 124);  // 2024 = 124 (years since 1900)
    EXPECT_LT(tm.tm_year, 200);  // Should be less than 2100

    // Month should be in valid range (0-11)
    EXPECT_GE(tm.tm_mon, 0);
    EXPECT_LE(tm.tm_mon, 11);

    // Day should be in valid range (1-31)
    EXPECT_GE(tm.tm_mday, 1);
    EXPECT_LE(tm.tm_mday, 31);

    // Hour should be in valid range (0-23)
    EXPECT_GE(tm.tm_hour, 0);
    EXPECT_LE(tm.tm_hour, 23);

    // Minute should be in valid range (0-59)
    EXPECT_GE(tm.tm_min, 0);
    EXPECT_LE(tm.tm_min, 59);

    // Second should be in valid range (0-60, allowing for leap seconds)
    EXPECT_GE(tm.tm_sec, 0);
    EXPECT_LE(tm.tm_sec, 60);
}

TEST(Wtools, GetTimeAsTmEpoch) {
    // Test with Unix epoch (January 1, 1970 00:00:00 UTC)
    const auto epoch = std::chrono::system_clock::time_point{};
    const auto result = GetTimeAsTm(epoch);

    ASSERT_TRUE(result.has_value());
    const auto &tm = result.value();

    // Should be 1970 in local time (accounting for timezone)
    EXPECT_EQ(tm.tm_year, 70);  // 1970 = 70 (years since 1900)
    EXPECT_EQ(tm.tm_mon, 0);    // January = 0
    EXPECT_EQ(tm.tm_mday, 1);   // 1st day of month

    EXPECT_GE(tm.tm_hour, 0);
    EXPECT_LE(tm.tm_hour, 23);
}

TEST(Wtools, Adapter) {
    auto store = GetAdapterInfoStore();
    for (const auto &entry : store) {
        XLOG::l.i("{}: \t{}", wtools::ToUtf8(entry.first),
                  entry.second.mac_address);
        auto arr = cma::tools::SplitString(entry.second.mac_address, ":");
        if (arr.size() == 8) {
            EXPECT_TRUE(
                rs::any_of(arr, [](const auto &e) { return e == "00"; }))
                << entry.first << "mac is wrong" << entry.second.mac_address;
        } else if (arr.size() == 6) {
            EXPECT_TRUE(
                rs::any_of(arr, [](const auto &e) { return e != "0)"; }))
                << entry.first << "mac is wrong" << entry.second.mac_address;
        } else {
            FAIL() << entry.first << "mac is wrong" << entry.second.mac_address;
        }
    }
    EXPECT_FALSE(store.empty());
}

static void ExpectEq(std::string const &in, std::string_view sep,
                     std::string const &expected) {
    EXPECT_EQ(ReplaceBlankLineWithSeparator(in, sep), expected)
        << "Input: [" << in << "] Separator: [" << sep << "]";
}

TEST(ReplaceBlankLineWithSeparator, EmptyInput) { ExpectEq("", "---", ""); }

TEST(ReplaceBlankLineWithSeparator, OnlyNewlineSingleBlankLine) {
    // One blank line with trailing newline -> separator + newline
    ExpectEq("\n", "---", "---\n");
}

TEST(ReplaceBlankLineWithSeparator, OnlySpacesNoTrailingNewline) {
    // No trailing newline -> output must not end with newline
    ExpectEq("   ", "---", "---");
}

TEST(ReplaceBlankLineWithSeparator, SpacesAndTabBlankLine) {
    ExpectEq(" \t  \n", "...", "...\n");
}

TEST(ReplaceBlankLineWithSeparator, VerticalTabAndFormFeedAreBlank) {
    // \v and \f are classified as space by isspace()
    ExpectEq("\v\f\n", "***", "***\n");
}

TEST(ReplaceBlankLineWithSeparator, CarriageReturnOnlyBeforeSplit) {
    // Line containing only '\r' (from a CRLF normalization scenario) is blank
    ExpectEq("\r\nX\n", "---", "---\nX\n");
}

TEST(ReplaceBlankLineWithSeparator, MixedContentNoBlankLines) {
    ExpectEq("a\nb\nc", "---", "a\nb\nc");
}

TEST(ReplaceBlankLineWithSeparator, MixedWithInternalBlankLines) {
    ExpectEq("a\n \n\t\nb\n", "---", "a\n---\n---\nb\n");
}

TEST(ReplaceBlankLineWithSeparator, NoTrailingNewlinePreserved) {
    ExpectEq("a\n\nb", "---", "a\n---\nb");
}

TEST(ReplaceBlankLineWithSeparator, TrailingBlankLinePreserved) {
    ExpectEq("a\n\n", "---", "a\n---\n");
}

TEST(ReplaceBlankLineWithSeparator, MultipleConsecutiveBlankLines) {
    ExpectEq("a\n\n\nb\n", "---", "a\n---\n---\nb\n");
}

TEST(ReplaceBlankLineWithSeparator, SeparatorCustomMultiChar) {
    ExpectEq("X\n \nY\n", "<<<BLANK>>>", "X\n<<<BLANK>>>\nY\n");
}

TEST(ReplaceBlankLineWithSeparator, EmptySeparatorRemovesMarker) {
    // Behavior: blank lines become empty lines (just newline retained)
    ExpectEq("A\n \n\nB", "", "A\n\n\nB");
}

TEST(ReplaceBlankLineWithSeparator, AllBlankLinesInput) {
    ExpectEq("\n \n\t\n", "---", "---\n---\n---\n");
}

TEST(ReplaceBlankLineWithSeparator, LastLineNonBlankNoFinalNewline) {
    ExpectEq("A\n \nB", "---", "A\n---\nB");
}

TEST(ReplaceBlankLineWithSeparator, LastLineBlankNoFinalNewlineInInput) {
    // Input ends with blank line without newline -> newline stripped at end
    ExpectEq("A\n  ", "---", "A\n---");
}

TEST(ReplaceBlankLineWithSeparator, MultiPeerBlankLinesAreReplaced) {
    const std::string input = R"(#Peers: 10

Peer: time.facebook.com
State: Active
Time Remaining: 26301.0890449s
Mode: 3 (Client)
Stratum: 1 (primary reference - syncd by radio clock)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 10:17:07 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255

Peer: time.google.com
State: Active
Time Remaining: 26301.2923728s
Mode: 3 (Client)
Stratum: 1 (primary reference - syncd by radio clock)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 10:17:07 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255

Peer: de.pool.ntp.org
State: Active
Time Remaining: 21063.2289556s
Mode: 3 (Client)
Stratum: 2 (secondary reference - syncd by (S)NTP)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 8:49:49 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255

Peer: time.cloudflare.com
State: Active
Time Remaining: 25164.9380930s
Mode: 3 (Client)
Stratum: 3 (secondary reference - syncd by (S)NTP)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 9:58:11 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255

Peer: example.com
State: Active
Time Remaining: 31328.6701628s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2

Peer: example.com
State: Active
Time Remaining: 31328.7829018s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2

Peer: example.com
State: Active
Time Remaining: 31328.9080142s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2

Peer: example.com
State: Active
Time Remaining: 31329.0328789s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2

Peer: example.com
State: Active
Time Remaining: 31329.1577069s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2

Peer: example.com
State: Active
Time Remaining: 31329.2822485s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2)";

    // Expected: each blank line replaced by '---'
    const std::string expected = R"(#Peers: 10
---
Peer: time.facebook.com
State: Active
Time Remaining: 26301.0890449s
Mode: 3 (Client)
Stratum: 1 (primary reference - syncd by radio clock)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 10:17:07 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255
---
Peer: time.google.com
State: Active
Time Remaining: 26301.2923728s
Mode: 3 (Client)
Stratum: 1 (primary reference - syncd by radio clock)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 10:17:07 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255
---
Peer: de.pool.ntp.org
State: Active
Time Remaining: 21063.2289556s
Mode: 3 (Client)
Stratum: 2 (secondary reference - syncd by (S)NTP)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 8:49:49 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255
---
Peer: time.cloudflare.com
State: Active
Time Remaining: 25164.9380930s
Mode: 3 (Client)
Stratum: 3 (secondary reference - syncd by (S)NTP)
PeerPoll Interval: 15 (32768s)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: 9/30/2025 9:58:11 PM
LastSyncError: 0x00000000 (Succeeded)
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 0
ValidDataCounter: 8
Reachability: 255
---
Peer: example.com
State: Active
Time Remaining: 31328.6701628s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2
---
Peer: example.com
State: Active
Time Remaining: 31328.7829018s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2
---
Peer: example.com
State: Active
Time Remaining: 31328.9080142s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2
---
Peer: example.com
State: Active
Time Remaining: 31329.0328789s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2
---
Peer: example.com
State: Active
Time Remaining: 31329.1577069s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2
---
Peer: example.com
State: Active
Time Remaining: 31329.2822485s
Mode: 3 (Client)
Stratum: 0 (unspecified)
PeerPoll Interval: 0 (unspecified)
HostPoll Interval: 15 (32768s)
Last Successful Sync Time: (null)
LastSyncError: 0x800705B4 (This operation returned because the timeout period expired. )
LastSyncErrorMsgId: 0x00000000 (Succeeded)
AuthTypeMsgId: 0x0000005A (NoAuth )
Resolve Attempts: 7
ValidDataCounter: 1
Reachability: 2)";

    auto output = ReplaceBlankLineWithSeparator(input, "---");

    EXPECT_EQ(output, expected);

    // 10 separators expected (one for each peer block)
    size_t count = 0;
    for (size_t pos = output.find("---"); pos != std::string::npos;
         pos = output.find("---", pos + 3)) {
        ++count;
    }
    EXPECT_EQ(count, 10u);

    EXPECT_EQ(output.find("\n\n"), std::string::npos);
}

}  // namespace wtools
