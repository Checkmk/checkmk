// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <chrono>
#include <filesystem>

#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "yaml-cpp/yaml.h"

namespace wtools {  // to become friendly for cma::cfg classes

TEST(Wtools, ScanProcess) {
    using namespace std::chrono;
    try {
        std::vector<std::string> names;

        wtools::ScanProcessList([&names](const PROCESSENTRY32& entry) -> auto {
            names.emplace_back(wtools::ConvertToUTF8(entry.szExeFile));
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
        for (auto& name : names) cma::tools::StringLower(name);

        // check that we do not have own process
        EXPECT_FALSE(cma::tools::find(names, std::string("watest32.exe")));
        EXPECT_FALSE(cma::tools::find(names, std::string("watest64.exe")));
        EXPECT_TRUE(cma::tools::find(names, std::string("svchost.exe")));

        {
            tst::YamlLoader w;
            tst::SafeCleanTempDir();
            ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

            namespace fs = std::filesystem;

            fs::path temp_dir = cma::cfg::GetTempDir();
            std::error_code ec;

            auto exe_a = temp_dir / "a.cmd";
            auto exe_b = temp_dir / "b.cmd";
            auto exe_c = temp_dir / "c.cmd";

            tst::ConstructFile(exe_a, "@echo start\n@call " + exe_b.u8string());
            tst::ConstructFile(exe_b, "@echo start\n@call " + exe_c.u8string());
            tst::ConstructFile(exe_c,
                               "@echo start\n@powershell Start-Sleep 10000");
            auto proc_id = cma::tools::RunStdCommand(exe_a.wstring(), false);
            EXPECT_TRUE(proc_id != 0);

            names.clear();
            bool found = false;
            std::wstring proc_name;
            DWORD parent_process_id = 0;
            wtools::ScanProcessList([
                proc_id, &proc_name, &found, &names, &parent_process_id
            ](const PROCESSENTRY32& entry) -> auto {
                names.push_back(wtools::ConvertToUTF8(entry.szExeFile));
                if (entry.th32ProcessID == proc_id) {
                    proc_name = entry.szExeFile;
                    parent_process_id = entry.th32ParentProcessID;
                    found = true;
                }
                return true;
            });

            EXPECT_TRUE(found) << "NOT FOUND STARTED PROCESS";
            EXPECT_TRUE(proc_name == L"cmd.exe");
            EXPECT_EQ(parent_process_id, ::GetCurrentProcessId());

            // killing
            KillProcessTree(proc_id);
            KillProcess(proc_id);
            cma::tools::sleep(500ms);

            found = false;
            wtools::ScanProcessList(
                [&found, proc_id ](const PROCESSENTRY32& entry) -> auto {
                    if (entry.th32ProcessID == proc_id) {
                        found = true;
                        EXPECT_FALSE(true) << "bullshit found " << proc_id;

                        ;
                    }
                    return true;
                });
            EXPECT_FALSE(found) << "process exists";
        }
    } catch (const std::exception& e) {
        XLOG::l("Error ops '{}'", e.what());
    } catch (...) {
        XLOG::l("Error ops");
    }
}

TEST(Wtools, ConditionallyConvertLowLevel) {
    {
        std::vector<uint8_t> v = {0xFE, 0xFE};
        EXPECT_FALSE(wtools::IsVectorMarkedAsUTF16(v));
    }
    {
        std::vector<uint8_t> v = {0xFE, 0xFE, 0, 0};
        EXPECT_FALSE(wtools::IsVectorMarkedAsUTF16(v));
    }
    {
        std::vector<uint8_t> v = {0xFF, 0xFE, 0, 0};
        EXPECT_TRUE(wtools::IsVectorMarkedAsUTF16(v));
    }

    {
        std::string v = "aa";
        auto data = v.data();
        data[2] = 1;  // simulate random data instead of the ending null
        AddSafetyEndingNull(v);
        data = v.data();
        EXPECT_TRUE(data[2] == 0);
    }
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

        const wchar_t* text = L"abcde";
        auto data = reinterpret_cast<const uint8_t*>(text);
        for (int i = 0; i < 10; ++i) {
            a.push_back(data[i]);
        }
        ret = wtools::ConditionallyConvertFromUTF16(a);
        EXPECT_EQ(5, ret.size());
        EXPECT_EQ(5, strlen(ret.c_str()));
    }
}

TEST(Wtools, FreqCo) {
    auto f = wtools::QueryPerformanceFreq();
    LARGE_INTEGER freq;
    ::QueryPerformanceFrequency(&freq);

    EXPECT_EQ(f, freq.QuadPart);

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
    auto x = ConvertToUTF8((wchar_t*)utf16string);
    EXPECT_EQ(x.size(), 10);
}

std::vector<int> TsValues = {
    8154,  // windows 10, dev machine
    2066,  // windows server, build machine
    5090   // windows 10, dev machine, late build
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

        const PERF_COUNTER_BLOCK* counterblock = nullptr;
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

        const PERF_COUNTER_BLOCK* counterblock = nullptr;
        auto counters = GenerateCounters(object, counterblock);
        EXPECT_NE(counterblock, nullptr);
        EXPECT_EQ(counters.size(), object->NumCounters);
    }
}

static auto null_handle = (HANDLE)0;

TEST(Wtools, AppRunnerCtorDtor) {
    wtools::AppRunner app;
    EXPECT_EQ(app.exitCode(), STILL_ACTIVE);
    EXPECT_EQ(app.getCmdLine(), L"");
    EXPECT_TRUE(app.getData().size() == 0);
    EXPECT_EQ(app.getStderrRead(), null_handle);
    EXPECT_EQ(app.getStdioRead(), null_handle);
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
    EXPECT_EQ(pipe.getRead(), null_handle);
    EXPECT_EQ(pipe.getWrite(), null_handle);

    pipe.create();
    EXPECT_NE(pipe.getRead(), null_handle);
    EXPECT_NE(pipe.getWrite(), null_handle);

    auto write_handle = pipe.getWrite();
    auto handle = pipe.moveWrite();
    EXPECT_EQ(pipe.getWrite(), null_handle);
    EXPECT_EQ(handle, write_handle);

    pipe.shutdown();
    EXPECT_EQ(pipe.getRead(), null_handle);
    EXPECT_EQ(pipe.getWrite(), null_handle);
}

TEST(Wtools, Perf2) {
    {
        auto index = wtools::perf::FindPerfIndexInRegistry(L"Zuxxx");
        EXPECT_TRUE(false == index.has_value());
    }
    {
        auto index =
            wtools::perf::FindPerfIndexInRegistry(L"Terminal Services");
        ASSERT_TRUE(index.has_value());
        int i = index.value();
        EXPECT_TRUE(cma::tools::find(TsValues, i));
    }
    {
        auto index = wtools::perf::FindPerfIndexInRegistry(L"Memory");
        ASSERT_TRUE(index.has_value());
        EXPECT_EQ(index, 4);
    }
}
TEST(Wtools, GetArgv2) {
    std::filesystem::path val = GetArgv(0);
    EXPECT_TRUE(cma::tools::IsEqual(val.extension().wstring(), L".exe"));
    std::filesystem::path val1 = GetArgv(10);
    EXPECT_TRUE(val1.empty());
}

TEST(Wtools, MemSize) {
    auto sz = GetOwnVirtualSize();
    EXPECT_TRUE(sz > static_cast<size_t>(400'000));
}

TEST(Wtools, ParentPid) {
    //    uint32_t pid = 0;
    //    auto parent_pid = GetParentPid(pid);
    //    EXPECT_TRUE(pid == 0);
}

TEST(Wtools, KillTree) {
    //
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

TEST(Wtools, LineEnding) {
    cma::OnStartTest();
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    std::filesystem::path tmp = cma::cfg::GetTempDir();

    auto work_file = tmp / "lf.test";

    const std::string s = "a\nb\r\nc\nd\n\n";
    const std::string expected = "a\r\nb\r\r\nc\r\nd\r\n\r\n";

    std::ofstream tst(work_file, std::ios::binary);
    tst.write(s.c_str(), s.size());
    tst.close();

    wtools::PatchFileLineEnding(work_file);

    auto result = ReadWholeFile(work_file);
    EXPECT_EQ(result, expected);
}

namespace {
// copy paste from the 2.0
bool DeleteRegistryValue(std::wstring_view path,
                         std::wstring_view value_name) noexcept {
    HKEY hkey = nullptr;
    auto ret = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);
    if (ERROR_SUCCESS == ret && nullptr != hkey) {
        ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
        ret = ::RegDeleteValue(hkey, value_name.data());
        if (ret == ERROR_SUCCESS) return true;
        if (ret == ERROR_FILE_NOT_FOUND) {
            XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}",
                      ConvertToUTF8(path), ConvertToUTF8(value_name));
            return true;
        }

        XLOG::l(XLOG_FLINE + "Failed to delete {}\\{} error [{}]",
                ConvertToUTF8(path), ConvertToUTF8(value_name), ret);
        return false;
    }
    //  here
    XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}", ConvertToUTF8(path),
              ConvertToUTF8(value_name));
    return true;
}
}  // namespace

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
        std::filesystem::path in_registry(
            GetRegistryValue(path, name, expand_value));
        std::filesystem::path expected(
            LR"(c:\Program Files (x86)\\checkmk\service\)");
        EXPECT_TRUE(std::filesystem::equivalent(in_registry.lexically_normal(),
                                                expected.lexically_normal()));
        EXPECT_TRUE(DeleteRegistryValue(path, name));
    }
}

TEST(Wtools, ExpandString) {
    using namespace std::string_literals;
    EXPECT_EQ(L"*Windows_NTWindows_NT*"s,
              ExpandStringWithEnvironment(L"*%OS%%OS%*"));
    EXPECT_EQ(L"%_1_2_a%"s, ExpandStringWithEnvironment(L"%_1_2_a%"));
}

}  // namespace wtools
