// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <chrono>
#include <string_view>

#include "common/wtools.h"
#include "test_tools.h"

using namespace std::string_literals;
using namespace std::chrono_literals;
namespace fs = std::filesystem;

namespace {
// Internal description of assorted counter params.
// Should be valid for all windows versions
struct CounterParam {
    const wchar_t *const description_;  // human form
    const wchar_t *const name_;         // usually number
    const uint32_t index_;              // the same as name
    const uint32_t counters_count;
    const uint32_t instances_min_;
    const uint32_t instances_max_;
};

constexpr CounterParam kCpuCounter = {.description_ = L"Processor",
                                      .name_ = L"238",
                                      .index_ = 238,
                                      .counters_count = 15,
                                      .instances_min_ = 1,
                                      .instances_max_ = 33};
constexpr CounterParam kDiskCounter = {.description_ = L"Disk",
                                       .name_ = L"234",
                                       .index_ = 234,
                                       .counters_count = 31,
                                       .instances_min_ = 1,
                                       .instances_max_ = 16};

}  // namespace

namespace cma::details {
extern bool g_is_service;
extern bool g_is_test;
}  // namespace cma::details

namespace wtools {  // to become friendly for cma::cfg classes

class WtoolsKillProcFixture : public ::testing::Test {
protected:
    static constexpr std::wstring_view dirToUse() { return L"kill_dir"; }
    static constexpr std::wstring_view nameToUse() { return L"kill_proc.exe"; }

    static void KillTmpProcesses() {
        // kill process
        wtools::ScanProcessList([](const PROCESSENTRY32 &entry) -> auto {
            if (std::wstring{entry.szExeFile} == nameToUse()) {
                wtools::KillProcess(entry.th32ProcessID, 99);
            }
            return true;  // continue scan
        });
    }

    int RunProcesses(int requested) const {
        const auto cmd = fmt::format("{} -t 8.8.8.8", test_exe_);

        int count = 0;
        for (int i = 0; i < requested; i++) {
            if (cma::tools::RunDetachedCommand(cmd)) {
                count++;
            }
        }

        return count;
    }

    static std::tuple<std::wstring, uint32_t> FindExpectedProcess() {
        uint32_t pid = 0;
        std::wstring path;
        ScanProcessList([&path, &pid ](const PROCESSENTRY32 &entry) -> auto {
            if (std::wstring{entry.szExeFile} != nameToUse()) {
                return true;  // continue scan
            }

            path = GetProcessPath(entry.th32ProcessID);
            pid = entry.th32ProcessID;
            return false;
        });

        return {path, pid};
    }

    void SetUp() override {
        test_dir_ = tst::MakeTempFolderInTempPath(dirToUse());
        test_exe_ = test_dir_ / nameToUse();
        fs::create_directories(test_dir_);
        fs::path ping(R"(c:\windows\system32\ping.exe)");
        ASSERT_TRUE(fs::copy_file(ping, test_exe_));
        RunProcesses(1);
    }

    void TearDown() override {
        KillTmpProcesses();
        ASSERT_NE(test_dir_.wstring().find(dirToUse()), std::wstring::npos);
        fs::remove_all(test_dir_);
    }

    fs::path test_dir_;
    fs::path test_exe_;
};

TEST_F(WtoolsKillProcFixture, KillProcByPid) {
    auto [path, pid] = FindExpectedProcess();
    EXPECT_TRUE(!path.empty());
    ASSERT_NE(pid, 0);

    EXPECT_TRUE(wtools::KillProcess(pid, 1));
    cma::tools::sleep(500ms);

    auto [path_empty, pid_null] = FindExpectedProcess();
    EXPECT_TRUE(path_empty.empty());
    EXPECT_EQ(pid_null, 0);

    EXPECT_FALSE(wtools::KillProcess(pid, 1));
}

TEST_F(WtoolsKillProcFixture, KillProcsByDir) {
    ASSERT_EQ(RunProcesses(1), 1);  // additional process

    EXPECT_EQ(KillProcessesByDir(test_dir_), 2);
    cma::tools::sleep(500ms);

    auto [path, pid] = FindExpectedProcess();
    EXPECT_TRUE(path.empty());
    EXPECT_EQ(pid, 0);

    EXPECT_EQ(KillProcessesByDir(test_dir_), 0);
    EXPECT_EQ(KillProcessesByDir(""), -1);
    EXPECT_EQ(KillProcessesByDir("k:"), -1);
}

class WtoolsKillProcessTreeFixture : public ::testing::Test {
protected:
    void SetUp() override {
        std::vector<std::string> names;
        temp_fs = tst::TempCfgFs::Create();

        wtools::ScanProcessList([&names](const PROCESSENTRY32 &entry) -> auto {
            names.emplace_back(wtools::ToUtf8(entry.szExeFile));
            if (names.back() == "watest32.exe" ||
                names.back() == "watest64.exe") {
                XLOG::l.w(
                    "Suspicious '{}' pid: [{}] parentpid: [{}] current pid [{}]",
                    names.back(), entry.th32ProcessID,
                    entry.th32ParentProcessID, ::GetCurrentProcessId());
            }
            return true;
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

    void TearDown() override {}

    uint32_t startProcessTree() {
        auto exe_a = temp_dir() / "a.cmd";
        auto exe_b = temp_dir() / "b.cmd";
        auto exe_c = temp_dir() / "c.cmd";

        tst::CreateTextFile(exe_a, "@echo start\n@call " + exe_b.u8string());
        tst::CreateTextFile(exe_b, "@echo start\n@call " + exe_c.u8string());
        tst::CreateTextFile(exe_c,
                            "@echo start\n@powershell Start-Sleep 10000");
        return cma::tools::RunStdCommand(exe_a.wstring(), false);
    }

    bool findProcessByPid(uint32_t pid) {
        bool found = false;
        wtools::ScanProcessList(
            [&found, pid ](const PROCESSENTRY32 &entry) -> auto {
                if (entry.th32ProcessID == pid) {
                    found = true;
                    EXPECT_FALSE(true) << "bullshit found " << pid << "name is "
                                       << entry.szExeFile;
                }
                return true;
            });
        return found;
    }

    bool findProcessByParentPid(uint32_t pid) {
        bool found = false;
        wtools::ScanProcessList(
            [&found, pid ](const PROCESSENTRY32 &entry) -> auto {
                if (entry.th32ParentProcessID == pid) {
                    found = true;
                }
                return true;
            });
        return found;
    }

    static std::tuple<std::wstring, uint32_t> findStartedProcess(
        uint32_t proc_id) {
        std::wstring proc_name;
        DWORD parent_process_id = 0;
        wtools::ScanProcessList([ proc_id, &proc_name, &parent_process_id ](
                                    const PROCESSENTRY32 &entry) -> auto {
            if (entry.th32ProcessID == proc_id) {
                proc_name = entry.szExeFile;
                parent_process_id = entry.th32ParentProcessID;
            }
            return true;
        });

        return {proc_name, parent_process_id};
    }

    tst::TempCfgFs::ptr temp_fs;
    std::filesystem::path temp_dir() { return temp_fs->data(); };
};

TEST_F(WtoolsKillProcessTreeFixture, Integration) {
    using namespace std::chrono_literals;

    // we start process tree
    auto proc_id = startProcessTree();
    EXPECT_TRUE(proc_id != 0);
    cma::tools::sleep(200ms);

    // we check that process is running
    auto [proc_name, parent_process_id] = findStartedProcess(proc_id);

    EXPECT_TRUE(proc_name == L"cmd.exe");
    EXPECT_EQ(parent_process_id, ::GetCurrentProcessId());

    EXPECT_TRUE(findProcessByParentPid(proc_id)) << "child process absent";

    // killing
    KillProcessTree(proc_id);
    cma::tools::sleep(300ms);
    EXPECT_FALSE(findProcessByParentPid(proc_id)) << "child process exists";
    KillProcess(proc_id, 99);
    cma::tools::sleep(200ms);

    EXPECT_FALSE(findProcessByPid(proc_id)) << "parent process exists";
}

TEST(Wtools, ConditionallyConvertLowLevel) {
    std::vector<uint8_t> v1{0xFE, 0xFE};
    EXPECT_FALSE(wtools::IsVectorMarkedAsUTF16(v1));

    std::vector<uint8_t> v2{0xFE, 0xFE, 0, 0};
    EXPECT_FALSE(wtools::IsVectorMarkedAsUTF16(v2));

    std::vector<uint8_t> v3{0xFF, 0xFE, 0, 0};
    EXPECT_TRUE(wtools::IsVectorMarkedAsUTF16(v3));

    std::string v = "aa";
    auto data = v.data();
    data[2] = 1;  // simulate random data instead of the ending null
    AddSafetyEndingNull(v);
    data = v.data();
    EXPECT_TRUE(data[2] == '\0');
}

TEST(Wtools, ConditionallyConvert) {
    {
        std::vector<uint8_t> a;

        auto ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_TRUE(ret.empty());
        a.push_back('a');
        ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_EQ(1, ret.size());
        EXPECT_EQ(1, strlen(ret.c_str()));
    }
    {
        std::vector<uint8_t> a;

        auto ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_TRUE(ret.empty());
        a.push_back('\xFF');
        ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_EQ(1, ret.size());

        a.push_back('\xFE');
        ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_EQ(0, ret.size());

        const wchar_t *text = L"abcde";
        auto data = reinterpret_cast<const uint8_t *>(text);
        for (int i = 0; i < 10; ++i) {
            a.push_back(data[i]);
        }
        ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_EQ(5, ret.size());
        EXPECT_EQ(5, strlen(ret.c_str()));
    }
}

TEST(Wtools, PerformanceFrequency) {
    LARGE_INTEGER freq;
    ::QueryPerformanceFrequency(&freq);

    EXPECT_EQ(wtools::QueryPerformanceFreq(), freq.QuadPart);

    LARGE_INTEGER c1;
    ::QueryPerformanceCounter(&c1);
    auto c = wtools::QueryPerformanceCo();
    LARGE_INTEGER c2;
    ::QueryPerformanceCounter(&c2);
    EXPECT_LE(c1.QuadPart, c);
    EXPECT_LE(c, c2.QuadPart);
}

TEST(Wtools, Utf16Utf8) {
    using namespace std;
    unsigned short utf16string[] = {0x41, 0x0448, 0x65e5, 0xd834, 0xdd1e, 0};
    auto x = ToUtf8((wchar_t *)utf16string);
    EXPECT_EQ(x.size(), 10);
}

std::vector<int> TsValues = {
    8154,  // windows 10, dev machine
    2066,  // windows server, build machine
    5090,  // windows 10, dev machine, late build
    6324,  // windows 10, 20h2
    8868,  // windows server build machine
};

TEST(Wtools, Perf) {
    int num_cpu = std::thread::hardware_concurrency();

    using namespace wtools::perf;
    {
        auto cur_info = kCpuCounter;
        auto perf_data = ReadPerformanceDataFromRegistry(cur_info.name_);
        ASSERT_TRUE(perf_data.data_);
        EXPECT_TRUE(perf_data.len_ > 1000);
        // 2. Find required object
        auto object = FindPerfObject(perf_data, cur_info.index_);
        ASSERT_TRUE(object);
        EXPECT_EQ(object->ObjectNameTitleIndex, cur_info.index_);

        auto instances = GenerateInstances(object);
        EXPECT_TRUE(instances.size() >= cur_info.instances_min_);
        EXPECT_TRUE(instances.size() <= cur_info.instances_max_);

        EXPECT_EQ(instances.size(), num_cpu + 1);
        EXPECT_EQ(instances.size(), object->NumInstances);

        auto names = GenerateInstanceNames(object);
        EXPECT_TRUE(instances.size() == names.size());

        auto counters = GenerateCounters(object);
        EXPECT_EQ(counters.size(), cur_info.counters_count);
        EXPECT_EQ(counters.size(), object->NumCounters);
    }

    {
        auto cur_info = kDiskCounter;
        auto perf_data = ReadPerformanceDataFromRegistry(cur_info.name_);
        ASSERT_TRUE(perf_data.data_);
        EXPECT_TRUE(perf_data.len_ > 1000);
        // 2. Find required object
        auto object = FindPerfObject(perf_data, cur_info.index_);
        ASSERT_TRUE(object);
        EXPECT_EQ(object->ObjectNameTitleIndex, cur_info.index_);

        auto instances = GenerateInstances(object);
        EXPECT_TRUE(instances.size() >= cur_info.instances_min_);
        EXPECT_TRUE(instances.size() <= cur_info.instances_max_);

        EXPECT_EQ(instances.size(), object->NumInstances);

        auto names = GenerateInstanceNames(object);
        EXPECT_TRUE(instances.size() == names.size());

        const PERF_COUNTER_BLOCK *counterblock = nullptr;
        auto counters = GenerateCounters(object, counterblock);
        EXPECT_EQ(counterblock, nullptr);
        EXPECT_EQ(counters.size(), cur_info.counters_count);
        EXPECT_EQ(counters.size(), object->NumCounters);
    }

    {
        // Instance less Check
        // 8154 is "Terminal Services" perf counter without instances
        // 2066 is "Terminal Services" perf counter without instances
        auto pos = TsValues.cbegin();
        auto index = *pos;
        auto perf_data =
            ReadPerformanceDataFromRegistry(std::to_wstring(index));
        while (perf_data.data_ == nullptr ||
               !FindPerfObject(perf_data, index)) {
            // no data or data is not valid:
            pos++;
            ASSERT_TRUE(pos != TsValues.cend());
            index = *pos;
            perf_data = ReadPerformanceDataFromRegistry(std::to_wstring(index));
        }
        ASSERT_TRUE(perf_data.data_);
        EXPECT_TRUE(perf_data.len_ > 30) << "Data should be big enough";

        // 2. Find required object
        auto object = FindPerfObject(perf_data, index);
        ASSERT_TRUE(object);
        EXPECT_EQ(object->ObjectNameTitleIndex, index);

        // Check that object instance less
        auto instances = GenerateInstances(object);
        EXPECT_TRUE(instances.size() == 0);

        //  Check that object is name less too
        auto names = GenerateInstanceNames(object);
        EXPECT_TRUE(instances.size() == names.size());

        // low level;

        const PERF_COUNTER_BLOCK *counterblock = nullptr;
        auto counters = GenerateCounters(object, counterblock);
        EXPECT_NE(counterblock, nullptr);
        EXPECT_EQ(counters.size(), object->NumCounters);
    }
}

TEST(Wtools, AppRunnerCtorDtor) {
    wtools::AppRunner app;
    EXPECT_EQ(app.exitCode(), STILL_ACTIVE);
    EXPECT_EQ(app.getCmdLine(), L"");
    EXPECT_TRUE(app.getData().size() == 0);
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

    fs::path temp_dir = cma::cfg::GetTempDir();
    std::error_code ec;

    auto exe = temp_dir / "a.cmd";

    tst::CreateFile(exe, "@echo xxxxxx\n");
    for (int i = 0; i < 30; i++) {
        wtools::AppRunner app;
        app.goExec(exe.wstring(), false, true, true);
        cma::tools::sleep(1000);
    }
    EXPECT_TRUE(true);
}
#endif

TEST(Wtools, SimplePipeBase) {
    wtools::SimplePipe pipe;
    EXPECT_EQ(pipe.getRead(), nullptr);
    EXPECT_EQ(pipe.getWrite(), nullptr);

    pipe.create();
    EXPECT_NE(pipe.getRead(), nullptr);
    EXPECT_NE(pipe.getWrite(), nullptr);

    auto write_handle = pipe.getWrite();
    auto handle = pipe.moveWrite();
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

    auto f = std::ranges::find(TsValues, index.value());
    EXPECT_NE(f, TsValues.end());

    index = perf::FindPerfIndexInRegistry(L"Memory");
    ASSERT_TRUE(index.has_value());
    EXPECT_EQ(index, 4);
}
TEST(Wtools, GetArgv) {
    std::filesystem::path val{GetArgv(0)};
    EXPECT_TRUE(cma::tools::IsEqual(val.extension().wstring(), L".exe"));

    EXPECT_TRUE(GetArgv(10).empty());
}

TEST(Wtools, MemSize) {
    auto sz = GetOwnVirtualSize();
    EXPECT_TRUE(sz > static_cast<size_t>(400'000));
}

TEST(Wtools, KillTree) {
    // Safety double check
    EXPECT_FALSE(kProcessTreeKillAllowed);
}

TEST(Wtools, Acl) {
    wtools::ACLInfo info("c:\\windows\\notepad.exe");
    auto ret = info.query();
    ASSERT_EQ(ret, 0) << "Bad return" << fmt::format("{:#X}", ret);
    auto stat = info.output();
    XLOG::l.i("\n{}", stat);
    EXPECT_TRUE(!stat.empty());

    {
        wtools::ACLInfo info_temp("c:\\windows\\temp\\check_mk_agent.msi");
        auto ret = info_temp.query();
        if (ret == S_OK) XLOG::l("\n{}", info_temp.output());
    }

    {
        wtools::ACLInfo info_temp("c:\\windows\\temp");
        auto ret = info_temp.query();
        if (ret == S_OK) XLOG::l("\n{}", info_temp.output());
    }
}

TEST(Wtools, PatchFileLineEnding) {
    constexpr std::string_view to_write{"a\nb\r\nc\nd\n\n"};
    constexpr std::string_view expected{"a\r\nb\r\r\nc\r\nd\r\n\r\n"};

    auto work_file = tst::GetTempDir() / "line_ending.tst";
    tst::CreateBinaryFile(work_file, to_write);

    wtools::PatchFileLineEnding(work_file);
    EXPECT_EQ(wtools::ReadWholeFile(work_file), expected);
}

TEST(Wtools, UserGroupName) {
    EXPECT_TRUE(GenerateCmaUserNameInGroup(L"").empty());
    EXPECT_EQ(GenerateCmaUserNameInGroup(L"XX"), L"cmk_TST_XX");

    cma::details::g_is_service = true;
    ON_OUT_OF_SCOPE(cma::details::g_is_service = false;
                    cma::details::g_is_test = true);

    EXPECT_EQ(GenerateCmaUserNameInGroup(L"XX"), L"cmk_in_XX");
    cma::details::g_is_service = false;
    cma::details::g_is_test = false;
    EXPECT_TRUE(GenerateCmaUserNameInGroup(L"XX").empty());
}

TEST(Wtools, Registry) {
    constexpr std::wstring_view path = LR"(SOFTWARE\checkmk_tst\unit_test)";
    constexpr std::wstring_view name = L"cmk_test";
    namespace fs = std::filesystem;

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
            EXPECT_TRUE(
                cma::tools::IsEqual(in_normalized, expected_normalized));
        }
    }

    {
        constexpr std::wstring_view value = L"21";
        constexpr std::wstring_view weird_value = L"_____";
        constexpr uint32_t uint_value = 123;
        ASSERT_TRUE(wtools::SetRegistryValue(path, name, value));
        EXPECT_EQ(wtools::GetRegistryValue(path, name, weird_value),
                  std::wstring(value));
        EXPECT_EQ(GetRegistryValue(path, name, uint_value), uint_value);
        EXPECT_TRUE(wtools::DeleteRegistryValue(path, name));
    }
}

TEST(Wtools, IsGoodHandleApi) {
    ASSERT_EQ(InvalidHandle(), INVALID_HANDLE_VALUE);
    EXPECT_TRUE(IsInvalidHandle(INVALID_HANDLE_VALUE));
    char c[10] = "aaa";
    auto h = static_cast<HANDLE>(c);
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
    auto no_variable{L"%temroot%\\servicing\\TrustedInstaller.exe"sv};
    EXPECT_EQ(ToCanonical(no_variable), no_variable);

    // Border value
    EXPECT_TRUE(ToCanonical(L"").empty());
}

TEST(PlayerTest, Pipe) {
    auto p = std::make_unique<wtools::SimplePipe>();
    EXPECT_EQ(p->getRead(), nullptr);
    EXPECT_EQ(p->getWrite(), nullptr);
    p->create();
    EXPECT_NE(p->getRead(), nullptr);
    EXPECT_NE(p->getWrite(), nullptr);
}

TEST(Wtools, HandleDeleter) {
    auto pid = ::GetCurrentProcessId();
    UniqueHandle mount;
    ASSERT_EQ(mount.get(), nullptr);
    mount.reset(::OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid));
    ASSERT_TRUE(mount.get() != nullptr);
    mount.reset();
    ASSERT_TRUE(mount.get() == nullptr);
}

TEST(Wtools, HandleDeleterInvalidAndNull) {
    const std::array<HANDLE, 2> handles{wtools::InvalidHandle(), nullptr};
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
    wchar_t *end = pos + 11;
    pos = nullptr;
    EXPECT_EQ(GetMultiSzEntry(pos, end), nullptr);
    pos = data.data();
    EXPECT_EQ(GetMultiSzEntry(pos, nullptr), nullptr);
    EXPECT_EQ(std::wstring{GetMultiSzEntry(pos, end)}, L"abcde");
    EXPECT_EQ(std::wstring{GetMultiSzEntry(pos, end)}, L"fgh");
    EXPECT_EQ(GetMultiSzEntry(pos, end), nullptr);
}

TEST(Wtools, ExecuteCommandsAsync) {
    namespace fs = std::filesystem;
    using namespace std::chrono_literals;

    auto output_file = fmt::format(L"{}cmk_test_{}.output",
                                   fs::temp_directory_path().wstring(),
                                   ::GetCurrentProcessId());
    std::vector<std::wstring> commands{L"echo x>" + output_file,
                                       L"@echo powershell Start-Sleep 1"};
    auto result = ExecuteCommandsAsync(L"test", commands);
    std::error_code ec;
    ON_OUT_OF_SCOPE({
        if (!result.empty()) {
            std::filesystem::remove(result, ec);
        }
        std::filesystem::remove(output_file, ec);
    });
    EXPECT_FALSE(result.empty());
    EXPECT_TRUE(std::filesystem::exists(result));
    auto table = tst::ReadFileAsTable(result);
    EXPECT_EQ(table[0], ToUtf8(commands[0]));
    EXPECT_EQ(table[1], ToUtf8(commands[1]));

    tst::WaitForSuccessSilent(5000ms, [output_file]() {
        std::error_code ec;
        return fs::exists(output_file, ec) && fs::file_size(output_file) >= 1;
    });
    auto output = tst::ReadFileAsTable(output_file);
    EXPECT_EQ(output[0], "x");
}

TEST(Wtools, RunCommandCheck) {
    auto s = RunCommand(L"icacls.exe /?");
    EXPECT_FALSE(s.empty());
}

}  // namespace wtools
