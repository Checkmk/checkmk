// test-plugin.cpp

//
#include "pch.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <future>
#include <string_view>

#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/plugins.h"
#include "read_file.h"
#include "service_processor.h"
#include "test_tools.h"

namespace cma {  // to become friendly for wtools classes
constexpr auto G_EndOfString = tgt::IsWindows() ? "\r\n" : "\n";

constexpr const char* SecondLine = "0, 1, 2, 3, 4, 5, 6, 7, 8";

static void CreatePluginInTemp(const std::filesystem::path& Path, int Timeout,
                               std::string Name) {
    std::ofstream ofs(Path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    ofs << "@echo off\n"
        //<< "timeout /T " << Timeout << " /NOBREAK > nul\n"
        << "powershell Start-Sleep " << Timeout << " \n"
        << "@echo ^<^<^<" << Name << "^>^>^>\n"
        << "@echo " << SecondLine << "\n";
}

static void CreateVbsPluginInTemp(const std::filesystem::path& Path,
                                  std::string Name) {
    std::ofstream ofs(Path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    for (int i = 0; i < 100; i++)
        ofs << "wscript.echo \"123456789 123456789123456789123456789123456789123456"
               "89 123456789 123456789123456789123456789123451234567891234567891234"
               "6789123456789123456789 12345678912345678912345678912345678912345678"
               "  123456789 1234567891234567891234567891234567891234567891234567890"
               "123456789123456789123456789123456789123456789123456789 123456789123"
               "45678912345678912345678912345678912345678912345678912345678912345aa\"\n";
}

static void CreateComplicatedPluginInTemp(const std::filesystem::path& Path,
                                          std::string Name) {
    std::ofstream ofs(Path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    ofs << "@echo off\n"
        << "@echo ^<^<^<" << Name << "^>^>^>\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n"
        << "@echo " << SecondLine << "\n";
}

static void CreatePluginInTemp(const std::filesystem::path& Path, int Timeout,
                               std::string Name, std::string_view code,
                               cma::provider::PluginType type) {
    std::ofstream ofs(Path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    ofs << "@echo off\n"
        << "powershell Start-Sleep " << Timeout << " \n";
    if (type == cma::provider::PluginType::normal) {
        ofs << "@echo ^<^<^<" << Name << "^>^>^>\n";
    }
    ofs << code << "\n";
}

static void RemoveFolder(const std::filesystem::path& Path) {
    namespace fs = std::filesystem;
    fs::path top = Path;
    fs::path dir_path;

    cma::PathVector directories;
    std::error_code ec;
    for (auto& p : fs::recursive_directory_iterator(top, ec)) {
        dir_path = p.path();
        if (fs::is_directory(dir_path)) {
            directories.push_back(fs::canonical(dir_path));
        }
    }

    for (std::vector<fs::path>::reverse_iterator rit = directories.rbegin();
         rit != directories.rend(); ++rit) {
        if (fs::is_empty(*rit)) {
            fs::remove(*rit);
        }
    }

    fs::remove_all(Path);
}

// because PluginMap is relative complicated(PluginEntry is not trivial)
// we will use special method to insert artificial data in map
static void InsertEntry(PluginMap& pm, const std::string& name, int timeout,
                        bool async, int cache_age) {
    namespace fs = std::filesystem;
    fs::path p = name;
    pm.emplace(std::make_pair(name, p));
    auto it = pm.find(name);
    if (async || cache_age) {
        cma::cfg::PluginInfo e = {timeout, cache_age, 1};
        it->second.applyConfigUnit(e, false);
    } else {
        cma::cfg::PluginInfo e = {timeout, 1};
        it->second.applyConfigUnit(e, false);
    }
}

TEST(PluginTest, TimeoutCalc) {
    using namespace cma::provider;
    {
        PluginMap pm;

        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::all))
            << "empty should has 0 timeout";
    }

    {
        // test failures on parameter change
        PluginMap pm;
        InsertEntry(pm, "a1", 5, true, 0);
        auto entry = GetEntrySafe(pm, "a1");
        ASSERT_TRUE(entry != nullptr);
        EXPECT_EQ(entry->failures(), 0);
        entry->failures_++;
        InsertEntry(pm, "a1", 5, true, 200);
        EXPECT_EQ(entry->failures(), 1);
        InsertEntry(pm, "a1", 3, true, 200);
        EXPECT_EQ(entry->failures(), 0);
        entry->failures_++;
        InsertEntry(pm, "a1", 3, true, 250);
        EXPECT_EQ(entry->failures(), 1);
        InsertEntry(pm, "a1", 3, false, 0);
        EXPECT_EQ(entry->failures(), 0);
    }

    // test async
    {
        PluginMap pm;
        InsertEntry(pm, "a1", 5, true, 0);
        {
            auto& e = pm.at("a1");
            EXPECT_TRUE(e.defined());
            EXPECT_TRUE(e.async());
        }
        EXPECT_EQ(5, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(5, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::sync));
        InsertEntry(pm, "a2", 15, true, 0);
        EXPECT_EQ(15, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(15, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::sync));
        InsertEntry(pm, "a3", 25, false, 100);
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::sync));

        InsertEntry(pm, "a4", 7, true, 100);
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::sync));
        {
            auto& e = pm.at("a4");
            EXPECT_TRUE(e.defined());
            EXPECT_TRUE(e.async());
        }

        InsertEntry(pm, "a4", 100, false, 0);  // sync
        {
            auto& e = pm.at("a4");
            EXPECT_TRUE(e.defined());
            EXPECT_FALSE(e.async());
        }
        EXPECT_EQ(100, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(100, FindMaxTimeout(pm, provider::PluginMode::sync));
    }

    // test sync
    {
        PluginMap pm;
        InsertEntry(pm, "a1", 5, false, 0);
        EXPECT_EQ(5, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(5, FindMaxTimeout(pm, provider::PluginMode::sync));
        InsertEntry(pm, "a2", 15, false, 0);
        EXPECT_EQ(15, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(0, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(15, FindMaxTimeout(pm, provider::PluginMode::sync));

        InsertEntry(pm, "a3", 25, false, 100);
        {
            auto& e = pm.at("a3");
            EXPECT_TRUE(e.defined());
            EXPECT_TRUE(e.async());
        }
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::all));
        EXPECT_EQ(25, FindMaxTimeout(pm, provider::PluginMode::async));
        EXPECT_EQ(15, FindMaxTimeout(pm, provider::PluginMode::sync));
    }
}

TEST(PluginTest, JobStartSTop) {
    namespace fs = std::filesystem;

    fs::path temp_folder = cma::cfg::GetTempDir();

    CreatePluginInTemp(temp_folder / "a.cmd", 120, "a");
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    auto [pid, job, process] =
        cma::tools::RunStdCommandAsJob((temp_folder / "a.cmd").wstring());
    ::Sleep(1000);
    TerminateJobObject(job, 21);
    if (job) CloseHandle(job);
    if (process) CloseHandle(process);
    /*

        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        PROCESSENTRY32 process;
        ZeroMemory(&process, sizeof(process));
        process.dwSize = sizeof(process);
        Process32First(snapshot, &process);
        do {
            // process.th32ProcessId is the PID.
            if (process.th32ParentProcessID == pid) {
                cma::tools::win::KillProcess(process.th32ProcessID);
            }

        } while (Process32Next(snapshot, &process));

        CloseHandle(job);
    cma::tools::win::KillProcess(pid);
    */
}

TEST(PluginTest, Extensions) {
    using namespace std;

    auto pshell = MakePowershellWrapper();
    EXPECT_TRUE(pshell.find(L"powershell.exe") != std::wstring::npos);

    auto p = ConstructCommandToExec(L"a.exe");
    auto p_expected = L"\"a.exe\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.cmd");
    p_expected = L"\"a.cmd\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.bat");
    p_expected = L"\"a.bat\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.e");
    EXPECT_EQ(p.empty(), true);
    p = ConstructCommandToExec(L"xxxxxxxxx");
    EXPECT_EQ(p.empty(), true);

    p = ConstructCommandToExec(L"a.pl");
    p_expected = L"perl.exe \"a.pl\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.py");
    p_expected = L"python.exe \"a.py\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.vbs");
    p_expected = L"cscript.exe //Nologo \"a.vbs\"";
    EXPECT_EQ(p, p_expected);

    p = ConstructCommandToExec(L"a.ps1");
    p_expected =
        L"powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File \"a.ps1\"";
    EXPECT_EQ(p, p_expected);
}

TEST(PluginTest, ConfigFolders) {
    using namespace cma::cfg;
    using namespace wtools;
    cma::OnStart(cma::AppType::test);

    {
        std::string s(yml_var::kCore);
        s += "\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, ConvertToUTF8(GetSystemPluginsDir()) + "\\");
    }

    {
        std::string s(yml_var::kBuiltinPlugins);
        s += "\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, ConvertToUTF8(GetSystemPluginsDir()) + "\\");
    }

    {
        std::string s(yml_var::kUserPlugins);
        s += "\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, ConvertToUTF8(GetUserPluginsDir()) + "\\");
    }

    {
        std::string s(yml_var::kAgent);
        s += "\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, ConvertToUTF8(GetUserDir()) + "\\");
    }

    {
        std::string s(yml_var::kLocal);
        s += "\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, ConvertToUTF8(GetLocalDir()) + "\\");
    }

    {
        std::string s = "user\\";
        auto result = cma::cfg::ReplacePredefinedMarkers(s);
        EXPECT_EQ(result, s);
    }
}

namespace cfg {
TEST(PluginTest, PluginInfoCheck) {
    cma::cfg::PluginInfo e_empty;
    EXPECT_EQ(e_empty.async(), false);
    EXPECT_EQ(e_empty.timeout(), kDefaultPluginTimeout);
    EXPECT_EQ(e_empty.retry(), 0);
    EXPECT_FALSE(e_empty.defined());
    EXPECT_EQ(e_empty.cacheAge(), 0);
    EXPECT_TRUE(e_empty.user().empty());
    EXPECT_TRUE(e_empty.group().empty());

    cma::cfg::PluginInfo e(10, 2, 1);
    EXPECT_TRUE(e.defined());
    EXPECT_EQ(e.async_, true);
    EXPECT_EQ(e.timeout_, 10);
    EXPECT_EQ(e.retry_, 1);
    EXPECT_EQ(e.cache_age_, 2);

    EXPECT_EQ(e.async(), true);
    EXPECT_EQ(e.timeout(), 10);
    EXPECT_EQ(e.retry(), 1);
    EXPECT_EQ(e.cacheAge(), 2);
    EXPECT_TRUE(e_empty.user().empty());
    EXPECT_TRUE(e_empty.group().empty());

    e.extend("g", "u");
    EXPECT_EQ(e.user(), "u");
    EXPECT_EQ(e.group(), "g");
    EXPECT_EQ(e.user_, "u");
    EXPECT_EQ(e.group_, "g");
}
}  // namespace cfg
TEST(PluginTest, ApplyConfig) {
    {
        cma::PluginEntry pe("c:\\a\\x.cmd");
        ASSERT_TRUE(pe.iu_.first.empty());
        ASSERT_TRUE(pe.iu_.second.empty());
        pe.fillInternalUser();
        ASSERT_TRUE(pe.iu_.first.empty());
        ASSERT_TRUE(pe.iu_.second.empty());
        pe.group_ = "Users";
        pe.fillInternalUser();
        ASSERT_TRUE(!pe.iu_.first.empty());
        ASSERT_TRUE(!pe.iu_.second.empty());
        pe.group_.clear();
        pe.fillInternalUser();
        ASSERT_TRUE(pe.iu_.first.empty());
        ASSERT_TRUE(pe.iu_.second.empty());
        pe.group_ = "Users";
        pe.user_ = "u p";
        pe.fillInternalUser();
        ASSERT_TRUE(pe.iu_.first == L"cmk_TST_Users");
        ASSERT_TRUE(!pe.iu_.second.empty());
        pe.group_.clear();
        pe.fillInternalUser();
        ASSERT_TRUE(pe.iu_.first == L"u");
        ASSERT_TRUE(pe.iu_.second == L"p");
    }
    cma::PluginEntry pe("c:\\a\\x.cmd");
    EXPECT_EQ(pe.failures(), 0);
    pe.failures_ = 2;
    EXPECT_EQ(pe.failures(), 2);
    pe.retry_ = 0;
    EXPECT_EQ(pe.failed(), false);
    pe.retry_ = 1;
    EXPECT_EQ(pe.failed(), true);

    {
        cma::cfg::PluginInfo e = {10, 1, 1};
        pe.applyConfigUnit(e, false);
        EXPECT_EQ(pe.failures(), 0);
        EXPECT_EQ(pe.async(), true);
        EXPECT_EQ(pe.local(), false);
        EXPECT_EQ(pe.retry(), 1);
        EXPECT_EQ(pe.timeout(), 10);
        EXPECT_EQ(pe.cacheAge(), cma::cfg::kMinimumCacheAge);
        EXPECT_TRUE(pe.user().empty());
        EXPECT_TRUE(pe.group().empty());

        pe.failures_ = 2;
        EXPECT_EQ(pe.failures(), 2);
        EXPECT_EQ(pe.failed(), true);
        e.extend("g", "u");
        pe.applyConfigUnit(e, false);
        EXPECT_EQ(pe.user(), "u");
        EXPECT_EQ(pe.group(), "g");
    }

    // heck that async configured entry reset to sync with data drop
    {
        pe.data_.resize(10);
        pe.failures_ = 5;
        EXPECT_EQ(pe.data().size(), 10);
        cma::cfg::PluginInfo e = {10, 11};
        pe.applyConfigUnit(e, true);
        EXPECT_EQ(pe.failures(), 0);
        EXPECT_EQ(pe.async(), false);
        EXPECT_EQ(pe.local(), true);
        EXPECT_EQ(pe.cacheAge(), 0);
        EXPECT_EQ(pe.retry(), 11);
        EXPECT_EQ(pe.failures(), 0);
        EXPECT_TRUE(pe.data().empty());
    }
}

static void CreateFileInTemp(const std::filesystem::path& Path) {
    std::ofstream ofs(Path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    ofs << Path.u8string() << std::endl;
}

// returns folder where
static cma::PathVector GetFolderStructure() {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    fs::path tmp = cma::cfg::GetTempDir();
    if (!fs::exists(tmp) || !fs::is_directory(tmp) ||
        tmp.u8string().find("\\tmp") == 0 ||
        tmp.u8string().find("\\tmp") == std::string::npos) {
        XLOG::l(XLOG::kStdio)("Cant create folder structure {} {} {}",
                              fs::exists(tmp), fs::is_directory(tmp),
                              tmp.u8string().find("\\tmp"));
        return {};
    }
    PathVector pv;
    for (auto& folder : {"a", "b", "c"}) {
        auto dir = tmp / folder;
        pv.emplace_back(dir);
    }
    return pv;
}

static void MakeFolderStructure(cma::PathVector Paths) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    for (auto& dir : Paths) {
        std::error_code ec;
        fs::create_directory(dir, ec);
        if (ec.value() != 0) {
            XLOG::l(XLOG::kStdio)("Can't create a folder {}", dir.u8string());
            continue;
        }

        CreateFileInTemp(dir / "x1.txt");
        CreateFileInTemp(dir / "x2.ps1");
        CreateFileInTemp(dir / "x3.ps2");
        CreateFileInTemp(dir / "y4.bat");
        CreateFileInTemp(dir / "z5.cmd");
        CreateFileInTemp(dir / "z6.exe");
        CreateFileInTemp(dir / "z7.vbs");
    }
}

static void RemoveFolderStructure(cma::PathVector Pv) {
    using namespace cma::cfg;
    for (auto& folder : Pv) {
        RemoveFolder(folder);
    }
}

TEST(PluginTest, ExeUnitCtor) {
    using namespace cma::cfg;

    // valid
    {
        bool as = false;
        int tout = 1;
        int age = 0;
        int retr = 2;
        Plugins::ExeUnit e("Plugin", tout, retr, true);
        EXPECT_EQ(e.async(), as);
        EXPECT_EQ(e.retry(), retr);
        EXPECT_EQ(e.timeout(), tout);
        EXPECT_EQ(e.cacheAge(), age);
        EXPECT_EQ(e.run(), true);
    }

    // valid async
    {
        bool as = true;
        int tout = 1;
        int age = 120;
        int retr = 2;
        Plugins::ExeUnit e("Plugin", tout, age, retr, true);
        EXPECT_EQ(e.async(), as);
        EXPECT_EQ(e.cacheAge(), age);
    }

    // valid async but low cache
    {
        bool as = true;
        int tout = 1;
        int age = cma::cfg::kMinimumCacheAge - 1;
        int retr = 2;
        Plugins::ExeUnit e("Plugin", tout, age, retr, true);
        EXPECT_EQ(e.async(), as);
        EXPECT_EQ(e.cacheAge(), cma::cfg::kMinimumCacheAge);
    }
}

TEST(PluginTest, HackPlugin) {
    std::vector<char> in;
    cma::tools::AddVector(in, std::string("<<<a>>>\r\n***\r\r\n<<<b>>>"));

    {
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::line);
        EXPECT_EQ(patch, "cached(123,456) ");
    }
    {
        auto patch = cma::ConstructPatchString(0, 456, HackDataMode::line);
        EXPECT_TRUE(patch.empty());
    }
    {
        auto patch = cma::ConstructPatchString(123, 0, HackDataMode::line);
        EXPECT_TRUE(patch.empty());
    }
    {
        auto patch = cma::ConstructPatchString(0, 456, HackDataMode::header);
        EXPECT_TRUE(patch.empty());
    }
    {
        auto patch = cma::ConstructPatchString(123, 0, HackDataMode::header);
        EXPECT_TRUE(patch.empty());
    }
    {
        std::vector<char> out;
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        EXPECT_EQ(patch, ":cached(123,456)");
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
        ASSERT_TRUE(ret);
        std::string str(out.data(), out.size());
        EXPECT_EQ(
            str, "<<<a:cached(123,456)>>>\r\n***\r\r\n<<<b:cached(123,456)>>>");
    }

    {
        std::vector<char> out;
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        EXPECT_FALSE(patch.empty());
        auto ret =
            cma::HackDataWithCacheInfo(out, in, "", HackDataMode::header);
        ASSERT_TRUE(ret);
        std::string str(out.data(), out.size());
        EXPECT_EQ(str, "<<<a>>>\r\n***\r\r\n<<<b>>>");
    }

    {
        std::vector<char> out;
        in.clear();
        cma::tools::AddVector(in, std::string("<<<a\r\n***"));
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
        ASSERT_TRUE(ret);
        std::string str(out.data(), out.size());
        EXPECT_EQ(str, "<<<a\r\n***");
    }

    {
        std::vector<char> out;
        in.clear();
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
        EXPECT_FALSE(ret);
    }

    {
        std::vector<char> out;
        in.clear();
        cma::tools::AddVector(in, std::string(" <<<a>>>\n***\n"));
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
        ASSERT_TRUE(ret);
        std::string str(out.data(), out.size());
        EXPECT_EQ(str, " <<<a>>>\n***\n");
    }

    {
        std::vector<char> out;
        in.clear();
        cma::tools::AddVector(in, std::string("xxx xxx\nzzz zzz\n"));
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::line);
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::line);
        ASSERT_TRUE(ret);
        std::string str(out.data(), out.size());
        EXPECT_EQ(str, "cached(123,456) xxx xxx\ncached(123,456) zzz zzz\n");
    }
}

TEST(PluginTest, HackPluginWithPiggyBack) {
    std::vector<char> in;
    cma::tools::AddVector(in, std::string(
                                  //
                                  "<<<a>>>\r\n***\r\r\n<<<b>>>\n"
                                  "<<<<a>>>>\n"
                                  "aaaaa\r\n"
                                  "<<<<a>>>>\n"
                                  "<<<a>>>\r\n***\r\r\n<<<b>>>\n"
                                  "<<<<>>>>\n"
                                  "<<<<>>>>\n"
                                  "<<<a>>>\r\n***\r\r\n<<<b>>>\n"
                                  //
                                  ));

    {
        std::vector<char> out;
        auto patch = cma::ConstructPatchString(123, 456, HackDataMode::header);
        auto ret =
            cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
        ASSERT_TRUE(ret);
        std::string out_string(out.data(), out.size());
        std::string exp_string(
            //
            "<<<a:cached(123,456)>>>\r\n***\r\r\n<<<b:cached(123,456)>>>\n"
            "<<<<a>>>>\n"
            "aaaaa\r\n"
            "<<<<a>>>>\n"
            "<<<a>>>\r\n***\r\r\n<<<b>>>\n"
            "<<<<>>>>\n"
            "<<<<>>>>\n"
            "<<<a:cached(123,456)>>>\r\n***\r\r\n<<<b:cached(123,456)>>>\n"
            //
        );
        EXPECT_EQ(out_string, exp_string);
    }
}

TEST(PluginTest, FilesAndFolders) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    cma::OnStart(cma::AppType::test);
    {
        EXPECT_EQ(groups::localGroup.foldersCount(), 1);
        EXPECT_EQ(groups::plugins.foldersCount(), 2);
        PathVector pv;
        for (auto& folder : groups::plugins.folders()) {
            pv.emplace_back(folder);
        }
        auto files = cma::GatherAllFiles(pv);
        if (files.size() < 10) {
            auto f = groups::plugins.folders();
            XLOG::l(XLOG::kStdio | XLOG::kInfo)(
                "\n\nTEST IS SKIPPED> YOU HAVE NO PLUGINS {} {} {} {}\n\n\n ",
                wtools::ConvertToUTF8(f[0]), wtools::ConvertToUTF8(f[1]),
                wtools::ConvertToUTF8(f[2]), wtools::ConvertToUTF8(f[3]));
            return;
        }

        EXPECT_TRUE(files.size() > 20);

        auto execute = GetInternalArray(groups::kGlobal, vars::kExecute);

        cma::FilterPathByExtension(files, execute);
        EXPECT_TRUE(files.size() >= 6);
        cma::RemoveDuplicatedNames(files);

        auto yaml_units = GetArray<YAML::Node>(
            cma::cfg::groups::kPlugins, cma::cfg::vars::kPluginsExecution);
        std::vector<Plugins::ExeUnit> exe_units;
        cma::cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);
        ASSERT_EQ(exe_units.size(), 3);

        EXPECT_EQ(exe_units[2].async(), false);
        EXPECT_EQ(exe_units[2].cacheAge(), 0);

        EXPECT_EQ(exe_units[0].timeout(), 60);
        EXPECT_EQ(exe_units[0].cacheAge(), 0);
        EXPECT_EQ(exe_units[0].async(), false);
        EXPECT_EQ(exe_units[0].retry(), 0);
    }

    {
        EXPECT_EQ(groups::localGroup.foldersCount(), 1);
        PathVector pv;
        for (auto& folder : groups::localGroup.folders()) {
            pv.emplace_back(folder);
        }
        auto files = cma::GatherAllFiles(pv);
        auto yaml_units = GetArray<YAML::Node>(
            cma::cfg::groups::kLocal, cma::cfg::vars::kPluginsExecution);
        std::vector<Plugins::ExeUnit> exe_units;
        cma::cfg::LoadExeUnitsFromYaml(exe_units, yaml_units);
        // no local files
        PluginMap pm;
        UpdatePluginMap(pm, true, files, exe_units, true);
        EXPECT_TRUE(pm.size() == 0);
        // for (auto& entry : pm) EXPECT_TRUE(entry.second.local());
    }

    {
        auto pv = GetFolderStructure();
        ASSERT_TRUE(0 != pv.size());
        RemoveFolderStructure(pv);
        MakeFolderStructure(pv);
        ON_OUT_OF_SCOPE(RemoveFolderStructure(pv));
        auto files = cma::GatherAllFiles(pv);
        ASSERT_EQ(files.size(), 21);

        const auto files_base = files;

        cma::FilterPathByExtension(files, {"exe"});
        EXPECT_EQ(files.size(), 3);

        files = files_base;
        cma::FilterPathByExtension(files, {"cmd"});
        EXPECT_EQ(files.size(), 3);

        files = files_base;
        cma::FilterPathByExtension(files, {"bad"});
        EXPECT_EQ(files.size(), 0);

        files = files_base;
        cma::FilterPathByExtension(files, {"exe", "cmd", "ps1"});
        EXPECT_EQ(files.size(), 9);

        files = files_base;
        cma::RemoveDuplicatedNames(files);
        EXPECT_EQ(files.size(), 7);
    }
}

static const std::vector<cma::cfg::Plugins::ExeUnit> exe_units_base = {
    //
    {"*.ps1",
     "async: yes\ntimeout: 10\ncache_age: 0\nretry_count: 5\nrun: yes\n"},  //
    {"*.cmd",
     "async: no\ntimeout: 12\ncache_age: 500\nretry_count: 3\nrun: yes\n"},  //
    {"*", "run: no\n"},                                                      //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> x2_sync = {
    //
    {"*.ps1",
     "async: no\ntimeout: 13\ncache_age: 0\nretry_count: 9\nrun: yes\n"},  //
    {"*", "run: no\n"},                                                    //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> x2_async_0_cache_age = {
    //
    {"*.ps1",
     "async: yes\ntimeout: 13\ncache_age: 0\nretry_count: 9\nrun: yes\n"},  //
    {"*", "run: no\n"},                                                     //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> x2_async_low_cache_age = {
    //
    {"*.ps1",
     "async: yes\ntimeout: 13\ncache_age: 119\nretry_count: 9\nrun: yes\n"},  //
    {"*", "run: no\n"},                                                       //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> x3_cmd_with_group_user = {
    //
    {"???-?.cmd",
     "async: yes\n"
     "timeout: 10\n"
     "cache_age: 0\n"
     "retry_count: 5\n"
     "group: g\n"
     "user: u\n"
     "run: yes\n"},      //
    {"*", "run: no\n"},  //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> x4_all = {
    //
    {"*.cmd", "run: no\n"},  // disable all cmd
    {"*", "run: yes\n"},     //
};

static const cma::PathVector pv_main = {
    "c:\\z\\x\\asd.d.ps1",  // 0
    "c:\\z\\x\\1.ps2",      // 1
    "c:\\z\\x\\asd.d.exe",  // 2
    "c:\\z\\x\\asd.d.cmd",  // 3
    "c:\\z\\x\\asd.d.bat",  // 4
    "c:\\z\\x\\asd-d.cmd"   // 5
};

static const cma::PathVector pv_short = {
    "c:\\z\\x\\asd.d.cmd",  //
    "c:\\z\\x\\asd.d.bat",  //
    "c:\\z\\x\\asd-d.cmd"   //
};

TEST(PluginTest, GeneratePluginEntry) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    cma::OnStart(cma::AppType::test);
    {
        {
            auto pv = FilterPathVector(pv_main, exe_units_base, false);
            EXPECT_EQ(pv.size(), 3);
            EXPECT_EQ(pv[0], pv_main[0]);
            EXPECT_EQ(pv[1], pv_main[3]);
            EXPECT_EQ(pv[2], pv_main[5]);
        }

        {
            auto pv = FilterPathVector(pv_main, x2_sync, false);
            EXPECT_EQ(pv.size(), 1);
            EXPECT_EQ(pv[0], pv_main[0]);
        }

        {
            auto pv = FilterPathVector(pv_main, x4_all, false);
            EXPECT_EQ(pv.size(),
                      pv_main.size() - 2);  // two coms are excluded
        }

        {
            auto pv = FilterPathVector(pv_main, x4_all, true);
            EXPECT_EQ(pv.size(), 0);  // nothing
        }

        // Filter and Insert
        {
            PluginMap pm;
            InsertInPluginMap(pm, {});
            EXPECT_EQ(pm.size(), 0);

            auto pv = FilterPathVector(pv_main, exe_units_base, false);
            InsertInPluginMap(pm, pv);
            EXPECT_EQ(pm.size(), pv.size());
            for (auto& f : pv) {
                EXPECT_FALSE(nullptr == GetEntrySafe(pm, f.u8string()));
            }

            InsertInPluginMap(pm, pv);  // no changes(the same)
            EXPECT_EQ(pm.size(), pv.size());

            pv.pop_back();
            FilterPluginMap(pm, pv);
            EXPECT_EQ(pm.size(), pv.size());

            FilterPluginMap(pm, {});
            EXPECT_EQ(pm.size(), 0);

            InsertInPluginMap(pm, pv_main);
            EXPECT_EQ(pm.size(), pv_main.size());
            ApplyExeUnitToPluginMap(pm, exe_units_base, true);
            {
                int indexes[] = {0, 3, 5};
                for (auto i : indexes) {
                    auto e_5 = GetEntrySafe(pm, pv_main[i].u8string());
                    ASSERT_NE(nullptr, e_5) << "bad at index " << i << "\n";
                    EXPECT_FALSE(e_5->path().empty())
                        << "bad at index " << i << "\n";
                    EXPECT_EQ(e_5->local(), TRUE)
                        << "bad at index " << i << "\n";
                }
            }
            {
                // bad files
                int indexes[] = {1, 2, 4};
                for (auto i : indexes) {
                    auto e_5 = GetEntrySafe(pm, pv_main[i].u8string());
                    ASSERT_NE(nullptr, e_5) << "bad at index " << i << "\n";
                    EXPECT_TRUE(e_5->path().empty())
                        << "bad at index " << i << "\n";
                    EXPECT_EQ(e_5->local(), false)
                        << "bad at index " << i << "\n";
                }
            }
        }

        PluginMap pm;
        UpdatePluginMap(pm, false, pv_main, exe_units_base);
        EXPECT_EQ(pm.size(), 0);

        UpdatePluginMap(pm, false, pv_main, exe_units_base, true);
        EXPECT_EQ(pm.size(), 0);
        UpdatePluginMap(pm, false, pv_main, exe_units_base, false);
        EXPECT_EQ(pm.size(), 3);  // 1 ps1 and 2 cmd

        auto e = GetEntrySafe(pm, "c:\\z\\x\\asd.d.ps1");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd.d.ps1");
        EXPECT_EQ(e->timeout(), 10);
        EXPECT_EQ(e->cacheAge(), 0);
        EXPECT_EQ(e->retry(), 5);

        e = GetEntrySafe(pm, "c:\\z\\x\\asd.d.cmd");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd.d.cmd");
        EXPECT_EQ(e->timeout(), 12);
        EXPECT_EQ(e->cacheAge(), 500);
        EXPECT_EQ(e->retry(), 3);

        e = GetEntrySafe(pm, "c:\\z\\x\\asd-d.cmd");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd-d.cmd");
        EXPECT_EQ(e->timeout(), 12);
        EXPECT_EQ(e->cacheAge(), 500);
        EXPECT_EQ(e->retry(), 3);

        // Update
        UpdatePluginMap(pm, false, pv_main, x2_sync, false);
        EXPECT_EQ(pm.size(), 1);
        e = GetEntrySafe(pm, "c:\\z\\x\\asd.d.ps1");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), false);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd.d.ps1");
        EXPECT_EQ(e->timeout(), 13);
        EXPECT_EQ(e->cacheAge(), 0);
        EXPECT_EQ(e->retry(), 9);

        // Update, async+0
        UpdatePluginMap(pm, false, pv_main, x2_async_0_cache_age, false);
        EXPECT_EQ(pm.size(), 1);
        e = GetEntrySafe(pm, "c:\\z\\x\\asd.d.ps1");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd.d.ps1");
        EXPECT_EQ(e->timeout(), 13);
        EXPECT_EQ(e->cacheAge(), 0);
        EXPECT_EQ(e->retry(), 9);

        // Update, async+119
        UpdatePluginMap(pm, false, pv_main, x2_async_low_cache_age, false);
        EXPECT_EQ(pm.size(), 1);
        e = GetEntrySafe(pm, "c:\\z\\x\\asd.d.ps1");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd.d.ps1");
        EXPECT_EQ(e->timeout(), 13);
        EXPECT_EQ(e->cacheAge(), kMinimumCacheAge);
        EXPECT_EQ(e->retry(), 9);

        // Update
        UpdatePluginMap(pm, false, pv_short, x3_cmd_with_group_user, false);
        EXPECT_EQ(pm.size(), 1);
        e = GetEntrySafe(pm, "c:\\z\\x\\asd-d.cmd");
        ASSERT_NE(nullptr, e);
        EXPECT_EQ(e->async(), true);
        EXPECT_EQ(e->path(), "c:\\z\\x\\asd-d.cmd");
        EXPECT_EQ(e->timeout(), 10);
        EXPECT_EQ(e->cacheAge(), 0);
        EXPECT_EQ(e->retry(), 5);
        EXPECT_EQ(e->user(), "u");
        EXPECT_EQ(e->group(), "g");

        UpdatePluginMap(pm, false, pv_main, x4_all, false);
        EXPECT_EQ(pm.size(), 4);

        // two files are dropped
        e = GetEntrySafe(pm, pv_main[3].u8string());
        ASSERT_EQ(nullptr, e);
        e = GetEntrySafe(pm, pv_main[5].u8string());
        ASSERT_EQ(nullptr, e);

        // four files a left
        ASSERT_NE(nullptr, GetEntrySafe(pm, pv_main[0].u8string()));
        ASSERT_NE(nullptr, GetEntrySafe(pm, pv_main[1].u8string()));
        ASSERT_NE(nullptr, GetEntrySafe(pm, pv_main[2].u8string()));
        ASSERT_NE(nullptr, GetEntrySafe(pm, pv_main[4].u8string()));
        for (auto i : {0, 1, 2, 4}) {
            e = GetEntrySafe(pm, pv_main[i].u8string());
            ASSERT_NE(nullptr, e);
            EXPECT_EQ(e->async(), false);
            EXPECT_EQ(e->path(), pv_main[i].u8string());
            EXPECT_EQ(e->timeout(), cma::cfg::kDefaultPluginTimeout);
            EXPECT_EQ(e->cacheAge(), 0);
            EXPECT_EQ(e->retry(), 0);
        }
    }
}

static const std::vector<cma::cfg::Plugins::ExeUnit> typical_units = {
    //
    {"c:\\z\\user\\*.ps1",
     "async: yes\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: yes\n"},  // enable ps1 in
    // user
    {"c:\\z\\core\\*.ps1",
     "async: no\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: yes\n"},  // disable
                                                                           // ps1
    // in core
    {"*", "run: no\n"},  // enable all
                         // other
};

static const std::vector<cma::cfg::Plugins::ExeUnit> exe_units = {
    // enable exe
    {"*", "async: no\ncache_age: 0\nretry_count: 5\n"},
    {"*.exe", "run: yes\n"},
    {"*", "async: yes\ntimeout: 11\ncache_age: 100\n"},
    {"*", "run: no\n"},  // disable all other
};

static const std::vector<cma::cfg::Plugins::ExeUnit> all_units = {
    //
    // enable exe
    {"*.cmd",
     "async: yes\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: no\n"},
    {"*", "timeout: 13\n"},
    {"*", "run: yes\n"},  // ENABLE all other
};

static const std::vector<cma::cfg::Plugins::ExeUnit> none_units = {
    //
    {"*.cmd",
     "async: yes\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: yes\n"},
    {"*", "run: no\n"},  // DISABLE all other
};
static const cma::PathVector typical_files = {
    "c:\\z\\user\\0.ps1",  //
    "c:\\z\\user\\1.ps1",  //
    "c:\\z\\user\\2.exe",  //
    "c:\\z\\user\\3.ps1",  //
                           //
    "c:\\z\\core\\0.ps1",  //
    "c:\\z\\core\\1.ps1",  //
    "c:\\z\\core\\2.exe",  //
    "c:\\z\\core\\3.exe"   //
};

static const std::vector<cma::cfg::Plugins::ExeUnit> many_exe_units = {
    //
    // [+] 2*ps1: 0,1
    {"*.ps1",
     "async: no\ntimeout: 1\ncache_age: 0\nretry_count: 1\nrun: yes\n"},
    // [-] ignored
    {"c:\\z\\user\\0.ps1",
     "async: no\ntimeout: 99\ncache_age: 0\nretry_count: 99\nrun: yes\n"},
    // [-] ignored
    {"*.ps1",
     "async: no\ntimeout: 99\ncache_age: 0\nretry_count: 99\nrun: yes\n"},
    // [+] 1*bat: 3
    {"loc\\*.bat",
     "async: no\ntimeout: 1\ncache_age: 0\nretry_count: 1\nrun: yes\n"},
    // [-] ignored
    {"*.bat",
     "async: no\ntimeout: 99\ncache_age: 0\nretry_count: 99\nrun: yes\n"},
    // [+] 1*exe: 7
    {"\\\\srv\\p\\t\\*.exe",
     "async: no\ntimeout: 1\ncache_age: 0\nretry_count: 1\nrun: yes\n"},
    // [+] disabled 2
    {"*", "run: no\n"},  // DISABLE all other
};

static const cma::PathVector many_files = {
    "c:\\z\\user\\0.ps1",    //
    "c:\\z\\user\\1.ps1",    //
    "c:\\z\\user\\2.exe",    //
    "c:\\z\\user\\3.bat",    //
                             //
    "c:\\z\\core\\0.ps1",    //
    "c:\\z\\core\\1.ps1",    //
    "\\\\srv\\p\\t\\2.exe",  //
    "c:\\z\\core\\3.exe"     //
};

TEST(PluginTest, CtorWithSource) {
    for (const auto& e : many_exe_units) {
        EXPECT_TRUE(e.source().IsMap());
        EXPECT_FALSE(e.sourceText().empty());
    }
}
TEST(PluginTest, ApplyEverything) {
    {
        PluginMap pm;
        ApplyEverythingToPluginMap(pm, {}, {}, false);
        EXPECT_EQ(pm.size(), 0);

        ApplyEverythingToPluginMap(pm, {}, typical_files, false);
        EXPECT_EQ(pm.size(), 0);

        ApplyEverythingToPluginMap(pm, typical_units, typical_files, false);
        EXPECT_EQ(pm.size(), 3);
        RemoveDuplicatedPlugins(pm, false);
        EXPECT_EQ(pm.size(), 3);
        {
            int valid_entries[] = {0, 1, 3};
            int index = 0;
            for (auto& entry : pm) {
                auto expected_index = valid_entries[index++];
                auto end_path = entry.second.path();
                auto expected_path = typical_files[expected_index];
                EXPECT_EQ(end_path.u8string(), expected_path.u8string());
            }
        }

        ApplyEverythingToPluginMap(pm, exe_units, typical_files, false);
        ASSERT_EQ(pm.size(), 5);
        RemoveDuplicatedPlugins(pm, false);
        ASSERT_EQ(pm.size(), 2);
        {
            int valid_entries[] = {2, 7};
            int index = 0;
            for (auto& entry : pm) {
                auto expected_index = valid_entries[index++];
                auto end_path = entry.second.path();
                auto expected_path = typical_files[expected_index];
                EXPECT_EQ(end_path.u8string(), expected_path.u8string());
                EXPECT_EQ(entry.second.cacheAge(), 0);
                EXPECT_EQ(entry.second.retry(), 5);
                EXPECT_EQ(entry.second.async(), false);
                EXPECT_EQ(entry.second.timeout(), 11);
                EXPECT_EQ(entry.second.defined(), true);
            }
        }

        ApplyEverythingToPluginMap(pm, all_units, typical_files, false);
        EXPECT_EQ(pm.size(), 5);
        RemoveDuplicatedPlugins(pm, false);
        {
            int valid_entries[] = {2, 7, 0, 1, 3};
            int index = 0;
            for (auto& [name, unit] : pm) {
                auto expected_index = valid_entries[index++];
                auto end_path = unit.path();
                auto expected_path = typical_files[expected_index];
                EXPECT_EQ(end_path.u8string(), expected_path.u8string());
                EXPECT_EQ(unit.cacheAge(), 0);   // default
                EXPECT_EQ(unit.retry(), 0);      // default
                EXPECT_EQ(unit.async(), false);  // default
                EXPECT_EQ(unit.timeout(), 13);   // set
            }
        }

        ApplyEverythingToPluginMap(pm, none_units, typical_files, false);
        EXPECT_EQ(pm.size(), 5);
        RemoveDuplicatedPlugins(pm, false);
        EXPECT_EQ(pm.size(), 0);

        {
            PluginMap pm;
            ApplyEverythingToPluginMap(pm, many_exe_units, many_files, false);
            EXPECT_EQ(pm.size(), 4);
            RemoveDuplicatedPlugins(pm, false);
            {
                int valid_entries[] = {0, 1, 3, 6};
                int index = 0;
                for (auto& [name, unit] : pm) {
                    auto expected_index = valid_entries[index++];
                    auto end_path = unit.path();
                    auto expected_path = many_files[expected_index];
                    EXPECT_EQ(end_path.u8string(), expected_path.u8string());
                    EXPECT_EQ(unit.cacheAge(), 0);
                    EXPECT_EQ(unit.retry(), 1);
                    EXPECT_EQ(unit.async(), false);
                    EXPECT_EQ(unit.timeout(), 1);
                    EXPECT_EQ(unit.defined(), true);
                }
            }
        }
    }
}

TEST(PluginTest, DuplicatedFileRemove) {
    namespace fs = std::filesystem;
    //
    {
        std::vector<fs::path> found_files = {
            "c:\\t\\A.exe", "c:\\r\\a.exe", "c:\\v\\x\\a.exe",
            "c:\\t\\b.exe", "c:\\r\\a.exe", "c:\\v\\x\\a.exe",
            "c:\\t\\a.exe", "c:\\r\\a.exe", "c:\\v\\x\\c.cmd",
        };
        auto files = RemoveDuplicatedFilesByName(found_files, true);
        EXPECT_TRUE(files.size() == 3);
    }
    {
        std::vector<fs::path> found_files = {
            "c:\\t\\a.exe", "c:\\r\\a.exe",    "c:\\t\\a.exe",
            "c:\\r\\a.exe", "c:\\v\\x\\c.cmd",
        };
        auto files = RemoveDuplicatedFilesByName(found_files, true);
        EXPECT_TRUE(files.size() == 2);
    }
}

TEST(PluginTest, DuplicatedUnitsRemove) {
    namespace fs = std::filesystem;
    UnitMap um;
    const char* const paths[] = {
        "c:\\t\\1b\\abC", "c:\\t\\2b\\xxx", "c:\\t\\3b\\abc", "c:\\t\\4b\\XXX",
        "c:\\t\\5b\\abc", "c:\\t\\6b\\abc", "c:\\t\\7b\\ccc", "c:\\t\\8b\\abc"};

    for (auto name : paths) um[name] = cma::cfg::Plugins::ExeUnit(name, "");
    EXPECT_TRUE(um.size() == 8);
    RemoveDuplicatedEntriesByName(um, true);
    EXPECT_EQ(um.size(), 3);
    int count = 0;
    EXPECT_FALSE(um[paths[0]].pattern().empty());
    EXPECT_FALSE(um[paths[1]].pattern().empty());
    EXPECT_FALSE(um[paths[6]].pattern().empty());
}

TEST(PluginTest, SyncStartSimulationFuture_Long) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    std::vector<Plugins::ExeUnit> exe_units = {
        //
        {"*.cmd", false, 10, 0, 3, true},  //
        {"*", true, 10, 0, 3, false},      //
    };

    fs::path temp_folder = cma::cfg::GetTempDir();

    CreatePluginInTemp(temp_folder / "a.cmd", 5, "a");
    CreatePluginInTemp(temp_folder / "b.cmd", 0, "b");
    CreatePluginInTemp(temp_folder / "c.cmd", 3, "c");
    CreatePluginInTemp(temp_folder / "d.cmd", 120, "d");

    PathVector vp = {
        (temp_folder / "a.cmd").u8string(),  //
        (temp_folder / "b.cmd").u8string(),  //
        (temp_folder / "c.cmd").u8string(),  //
        (temp_folder / "d.cmd").u8string(),  //
    };

    std::vector<std::string> strings = {
        "<<<a>>>",  //
        "<<<b>>>",  //
        "<<<c>>>",  //
        "<<<d>>>",  // not delivered!
    };

    ON_OUT_OF_SCOPE(for (auto& f : vp) fs::remove(f););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, false, vp, exe_units, false);

    using namespace std;
    using DataBlock = vector<char>;

    vector<future<DataBlock>> results;
    int requested_count = 0;

    // sync part
    for (auto& entry_pair : pm) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;

        // C++ async black magic
        results.emplace_back(std::async(
            std::launch::async,  // first param

            [](cma::PluginEntry* Entry) -> DataBlock {  // lambda
                if (!Entry) return {};
                return Entry->getResultsSync(Entry->path().wstring());
            },  // lambda end

            &entry  // lambda parameter
            ));
        requested_count++;
    }
    EXPECT_TRUE(requested_count == 4);

    DataBlock out;
    int delivered_count = 0;
    for (auto& r : results) {
        auto result = r.get();
        if (result.size()) {
            ++delivered_count;
            cma::tools::AddVector(out, result);
        }
    }
    EXPECT_TRUE(delivered_count == 3);

    int found_headers = 0;
    std::string_view str(out.data(), out.size());
    for (int i = 0; i < 3; ++i) {
        if (str.find(strings[i]) != std::string_view::npos) ++found_headers;
    }
    EXPECT_EQ(found_headers, 3);
}

static auto GenerateCachedHeader(const std::string& UsualHeader,
                                 const cma::PluginEntry* Ready) {
    std::vector<char> out;
    std::vector<char> in;
    cma::tools::AddVector(in, UsualHeader);
    auto patch = cma::ConstructPatchString(
        Ready->legacyTime(), Ready->cacheAge(), HackDataMode::header);
    auto ret = cma::HackDataWithCacheInfo(out, in, patch, HackDataMode::header);
    if (ret) {
        std::string str(out.data(), out.size());
        return str;
    }

    return std::string();
}

static auto ParsePluginOut(const std::vector<char>& Data) {
    std::string out(Data.begin(), Data.end());
    auto table = cma::tools::SplitString(out, G_EndOfString);
    auto sz = table.size();
    auto first_line = sz > 0 ? table[0] : "";
    auto second_line = sz > 1 ? table[1] : "";

    return std::make_tuple(sz, first_line, second_line);
}

const std::vector<std::string> strings = {
    "<<<async2>>>",  //
    "<<<async30>>>"  //
};

std::vector<cma::cfg::Plugins::ExeUnit> exe_units_async_0 = {
    //
    {"*.cmd",
     "async: yes\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: yes\n"},
    {"*", "run: no\n"},  // DISABLE all other
};

PathVector as_files;

PathVector as_vp;

std::vector<cma::cfg::Plugins::ExeUnit> exe_units_async_121 = {
    //
    {"*.cmd",
     "async: yes\ntimeout: 10\ncache_age: 121\nretry_count: 3\nrun: yes\n"},
    {"*", "run: no\n"},  // DISABLE all other
};

std::vector<cma::cfg::Plugins::ExeUnit> exe_units_valid_SYNC = {
    //
    {"*.cmd",
     "async: no\ntimeout: 10\ncache_age: 0\nretry_count: 3\nrun: yes\n"},
    {"*", "run: no\n"},  // DISABLE all other
};

struct PluginDesc {
    int timeout_;
    const char* file_name_;
    const char* section_name;
};

using PluginDescVector = std::vector<PluginDesc>;

void PrepareStructures() {
    std::filesystem::path temp_folder = cma::cfg::GetTempDir();
    as_vp.clear();
    as_files.clear();
    struct PluginDesc {
        int timeout_;
        const char* file_name_;
        const char* section_name;
    } plugin_desc_arr[2] = {
        {2, "async2.cmd", "async2"},
        {30, "async30.cmd", "async30"},
    };

    for (auto& pd : plugin_desc_arr) {
        as_files.push_back(temp_folder / pd.file_name_);
        CreatePluginInTemp(as_files.back(), pd.timeout_, pd.section_name);
        as_vp.push_back(as_files.back());
    }
}

void PrepareFastStructures() {
    std::filesystem::path temp_folder = cma::cfg::GetTempDir();
    as_vp.clear();
    as_files.clear();
    struct PluginDesc {
        int timeout_;
        const char* file_name_;
        const char* section_name;
    } plugin_desc_arr[2] = {
        {2, "async2.cmd", "async2"},
        {3, "async3.cmd", "async3"},
    };

    for (auto& pd : plugin_desc_arr) {
        as_files.push_back(temp_folder / pd.file_name_);
        CreatePluginInTemp(as_files.back(), pd.timeout_, pd.section_name);
        as_vp.push_back(as_files.back());
    }
}

PluginDescVector async0_files = {{2, "async2.cmd", "async0"}};

[[nodiscard]] PathVector PrepareFilesAndStructures(
    const PluginDescVector& plugin_desc_arr, std::string_view code,
    cma::provider::PluginType type) {
    std::filesystem::path temp_folder = cma::cfg::GetTempDir();
    PathVector pv;
    for (auto& pd : plugin_desc_arr) {
        pv.emplace_back(temp_folder / pd.file_name_);
        CreatePluginInTemp(pv.back(), pd.timeout_, pd.section_name, code, type);
    }
    return pv;
}

TEST(PluginTest, RemoveDuplicatedPlugins) {
    PluginMap x;
    RemoveDuplicatedPlugins(x, false);
    EXPECT_TRUE(x.size() == 0);

    x.emplace(std::make_pair("c:\\123\\a.bb", "c:\\123\\a.bb"));
    EXPECT_TRUE(x.size() == 1);
    RemoveDuplicatedPlugins(x, false);
    EXPECT_TRUE(x.size() == 1);
    x.emplace(std::make_pair("c:\\123\\aa.bb", "c:\\123\\aa.bb"));
    EXPECT_TRUE(x.size() == 2);
    RemoveDuplicatedPlugins(x, false);
    EXPECT_TRUE(x.size() == 2);

    x.emplace(std::make_pair("c:\\123\\ax.bb", ""));
    EXPECT_TRUE(x.size() == 3);
    RemoveDuplicatedPlugins(x, false);
    EXPECT_TRUE(x.size() == 2);

    x.emplace(std::make_pair("c:\\123\\another\\a.bb", "c:\\123\a.bb"));
    x.emplace(std::make_pair("c:\\123\\another\\aa.bb", "c:\\123\\aa.bb"));
    x.emplace(std::make_pair("c:\\123\\aa.bb", "c:\\123\\aa.bb"));
    x.emplace(std::make_pair("c:\\123\\yy.bb", "c:\\123\\aa.bb"));
    EXPECT_TRUE(x.size() == 5);
    RemoveDuplicatedPlugins(x, false);
    EXPECT_TRUE(x.size() == 3);
}

TEST(PluginTest, AsyncStartSimulation_0) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    PrepareFastStructures();

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : as_vp) fs::remove(f, ec););
    {
        auto as_vp_0 = as_vp[0].u8string();
        auto as_vp_1 = as_vp[1].u8string();
        PluginMap pm;  // load from the groups::plugin
        UpdatePluginMap(pm, false, as_vp, exe_units_async_0, false);
        // async_0 means sync
        EXPECT_EQ(cma::provider::config::G_AsyncPluginWithoutCacheAge_RunAsync,
                  cma::provider::config::IsRunAsync(pm.at(as_vp_0)));
        EXPECT_EQ(cma::provider::config::G_AsyncPluginWithoutCacheAge_RunAsync,
                  cma::provider::config::IsRunAsync(pm.at(as_vp_1)));

        UpdatePluginMap(pm, false, as_vp, exe_units_valid_SYNC, false);
        EXPECT_FALSE(cma::provider::config::IsRunAsync(pm.at(as_vp_0)));
        EXPECT_FALSE(cma::provider::config::IsRunAsync(pm.at(as_vp_1)));

        UpdatePluginMap(pm, false, as_vp, exe_units_async_121, false);
        EXPECT_TRUE(cma::provider::config::IsRunAsync(pm.at(as_vp_0)));
        EXPECT_TRUE(cma::provider::config::IsRunAsync(pm.at(as_vp_1)));
    }

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, false, as_vp, exe_units_async_0, false);

    // async to sync part
    for (auto& entry_pair : pm) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;
        EXPECT_EQ(entry.failures(), 0);
        EXPECT_EQ(entry.failed(), 0);

        auto accu = entry.getResultsSync(L"id", -1);
        EXPECT_FALSE(accu.empty());
        EXPECT_FALSE(entry.running());
        entry.breakAsync();
        EXPECT_EQ(entry.failures(), 0);
    }
}

TEST(PluginTest, AsyncStartSimulation_Long) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    PrepareStructures();

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : as_vp) fs::remove(f, ec););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, false, as_vp, exe_units_async_121, false);

    // async part
    for (auto& entry_pair : pm) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;
        EXPECT_EQ(entry.failures(), 0);
        EXPECT_EQ(entry.failed(), 0);

        auto accu = entry.getResultsAsync(true);
        EXPECT_EQ(true, accu.empty());
        EXPECT_TRUE(entry.running());
    }

    ::Sleep(5000);  // funny windows
    {
        auto ready = GetEntrySafe(pm, as_files[0].u8string());
        ASSERT_NE(nullptr, ready);
        auto accu = ready->getResultsAsync(true);

        // something in result and running
        ASSERT_TRUE(!accu.empty());
        auto expected_header = GenerateCachedHeader(strings[0], ready);
        {
            auto [sz, ln1, ln2] = ParsePluginOut(accu);
            EXPECT_EQ(sz, 2);
            EXPECT_EQ(ln1, expected_header);
            EXPECT_EQ(ln2, SecondLine);
        }
        EXPECT_FALSE(ready->running());  // NOT restarted by getResultAsync
                                         // 121 sec cache age
    }

    {
        auto still_running = GetEntrySafe(pm, as_files[1].u8string());
        ASSERT_TRUE(nullptr != still_running) << ": " << pm.size();
        auto accu = still_running->getResultsAsync(true);

        // nothing but still running
        EXPECT_TRUE(accu.empty());
        EXPECT_TRUE(still_running->running());

        still_running->breakAsync();
        EXPECT_FALSE(still_running->running());
    }

    // pinging and restarting
    {
        auto ready = GetEntrySafe(pm, as_files[0].u8string());
        ASSERT_NE(nullptr, ready);
        auto accu1 = ready->getResultsAsync(true);
        ::Sleep(100);
        auto accu2 = ready->getResultsAsync(true);

        // something in result and running
        ASSERT_TRUE(!accu1.empty());
        ASSERT_TRUE(!accu2.empty());
        ASSERT_TRUE(accu1 == accu2);

        auto expected_header = GenerateCachedHeader(strings[0], ready);
        {
            auto [sz, ln1, ln2] = ParsePluginOut(accu1);
            EXPECT_EQ(sz, 2);
            EXPECT_EQ(ln1, expected_header);
            EXPECT_EQ(ln2, SecondLine);
        }
        {
            auto [sz, ln1, ln2] = ParsePluginOut(accu2);
            EXPECT_EQ(sz, 2);
            EXPECT_EQ(ln1, expected_header);
            EXPECT_EQ(ln2, SecondLine);
        }

        ready->breakAsync();
        EXPECT_FALSE(ready->running());

        // we have no more running process still we should get real data
        {
            auto accu_after_break = ready->getResultsAsync(true);
            ASSERT_TRUE(!accu_after_break.empty());
            ASSERT_TRUE(accu_after_break == accu2);
            EXPECT_FALSE(ready->running())
                << "should not run. Cache age is big enough\n";
        }

        ready->breakAsync();
        EXPECT_FALSE(ready->running());

        // we have no more running process still we should get real and good
        // data
        {
            auto accu_after_break = ready->getResultsAsync(false);
            ASSERT_TRUE(!accu_after_break.empty());
            ASSERT_TRUE(accu_after_break == accu2);
            EXPECT_FALSE(ready->running());
        }

        cma::srv::WaitForAsyncPluginThreads(5000ms);
        {
            auto accu_new = ready->getResultsAsync(false);
            ASSERT_TRUE(!accu_new.empty());
            EXPECT_EQ(accu_new, accu2)
                << "without RESTART and we have to have SAME data";
            auto expected_header_new = GenerateCachedHeader(strings[0], ready);
            {
                auto [sz, ln1, ln2] = ParsePluginOut(accu_new);
                EXPECT_EQ(sz, 2);
                EXPECT_EQ(ln1, expected_header_new);
                EXPECT_EQ(ln2, SecondLine);
            }

            // RESTART
            EXPECT_FALSE(ready->isGoingOld());  // not enough time to be old
            ready->restartAsyncThreadIfFinished(L"x");
            EXPECT_TRUE(ready->running());
            accu_new = ready->getResultsAsync(false);
            ASSERT_TRUE(!accu_new.empty());
            EXPECT_EQ(accu_new, accu2)
                << "IMMEDIATELY after RESTART and we have to have SAME data";
            expected_header_new = GenerateCachedHeader(strings[0], ready);
            {
                auto [sz, ln1, ln2] = ParsePluginOut(accu_new);
                EXPECT_EQ(sz, 2);
                EXPECT_EQ(ln1, expected_header_new);
                EXPECT_EQ(ln2, SecondLine);
            }
            ::Sleep(6000);
            accu_new = ready->getResultsAsync(false);
            ASSERT_TRUE(!accu_new.empty());
            EXPECT_NE(accu_new, accu2)
                << "late after RESTART and we have to have different data";
            expected_header_new = GenerateCachedHeader(strings[0], ready);
            {
                auto [sz, ln1, ln2] = ParsePluginOut(accu_new);
                EXPECT_EQ(sz, 2);
                EXPECT_EQ(ln1, expected_header_new);
                EXPECT_EQ(ln2, SecondLine);
            }
        }
    }

    // changing to local
    {
        auto ready = GetEntrySafe(pm, as_files[0].u8string());
        auto still = GetEntrySafe(pm, as_files[1].u8string());

        UpdatePluginMap(pm, true, as_vp, exe_units_async_121, true);
        EXPECT_EQ(pm.size(), 2);
        EXPECT_TRUE(ready->local());
        EXPECT_TRUE(still->local());
    }

    // changing to sync
    {
        auto ready = GetEntrySafe(pm, as_files[0].u8string());
        EXPECT_FALSE(ready->data().empty());

        auto still = GetEntrySafe(pm, as_files[1].u8string());
        EXPECT_FALSE(ready->running()) << "timeout 10 secs expired";
        still->restartAsyncThreadIfFinished(L"Id");

        UpdatePluginMap(pm, false, as_vp, exe_units_valid_SYNC, true);
        EXPECT_EQ(pm.size(), 2);
        EXPECT_FALSE(ready->running());
        EXPECT_TRUE(ready->data().empty());

        EXPECT_FALSE(still->running());
        EXPECT_TRUE(still->data().empty());

        auto data = ready->getResultsAsync(true);
        EXPECT_TRUE(data.empty());
    }
    // changing to local again
    {
        auto ready = GetEntrySafe(pm, as_files[0].u8string());
        auto still = GetEntrySafe(pm, as_files[1].u8string());

        UpdatePluginMap(pm, true, as_vp, exe_units_async_121, true);
        EXPECT_EQ(pm.size(), 2);
        EXPECT_TRUE(ready->local());
        EXPECT_TRUE(still->local());
        EXPECT_TRUE(ready->cacheAge() >= kMinimumCacheAge);
        EXPECT_TRUE(still->cacheAge() >= kMinimumCacheAge);

        auto data = ready->getResultsAsync(true);
        EXPECT_TRUE(data.empty());
        cma::srv::WaitForAsyncPluginThreads(5000ms);
        data = ready->getResultsAsync(true);
        EXPECT_TRUE(!data.empty());
        std::string out(data.begin(), data.end());
        auto table = cma::tools::SplitString(out, G_EndOfString);
        ASSERT_EQ(table.size(), 2);
        EXPECT_TRUE(table[0].find("<<<async2>>>") != std::string::npos)
            << "headers of local plugins shouldn't be patched";
    }
}

struct TestDateTime {
    bool invalid() const { return hour == 99; }
    uint32_t hour = 99;
    uint32_t min = 0;
    uint32_t sec = 0;
    uint32_t msec = 0;
};

TestDateTime StringToTime(const std::string& text) {
    TestDateTime tdt;

    auto table = cma::tools::SplitString(text, ":");
    if (table.size() != 3) return tdt;

    auto sec_table = cma::tools::SplitString(table[2], ".");
    if (sec_table.size() != 2) return tdt;

    tdt.hour = std::atoi(table[0].c_str());
    tdt.min = std::atoi(table[1].c_str());
    tdt.sec = std::atoi(sec_table[0].c_str());
    tdt.msec = std::atoi(sec_table[1].c_str());

    return tdt;
}

TEST(PluginTest, StringToTime) {
    {
        auto tdt = StringToTime("");
        EXPECT_TRUE(tdt.invalid());
    }
    {
        auto tdt = StringToTime("21:3:3.45");
        ASSERT_FALSE(tdt.invalid());
        EXPECT_EQ(tdt.hour, 21);
        EXPECT_EQ(tdt.min, 3);
        EXPECT_EQ(tdt.sec, 3);
        EXPECT_EQ(tdt.msec, 45);
    }
}

// waiter for the result. In fact polling with grane 500ms
template <typename T, typename B>
bool WaitForSuccess(std::chrono::duration<T, B> allowed_wait,
                    std::function<bool()> func) {
    using namespace std::chrono;

    constexpr auto grane = 500ms;
    auto wait_time = allowed_wait;

    while (wait_time >= 0ms) {
        auto success = func();
        if (success) return true;

        cma::tools::sleep(grane);
        wait_time -= grane;
    }

    return false;
}

std::string TestConvertToString(std::vector<char> accu) {
    std::string str(accu.begin(), accu.end());
    return str;
}

TEST(PluginTest, Async0DataPickup) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    auto files = PrepareFilesAndStructures(async0_files, R"(echo %time%)",
                                           provider::PluginType::normal);

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : files) fs::remove(f, ec););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, false, files, exe_units_async_0, false);

    // async part should provide nothing
    for (auto& entry_pair : pm) {
        auto& name = entry_pair.first;
        auto& entry = entry_pair.second;
        EXPECT_EQ(entry.failures(), 0);
        EXPECT_EQ(entry.failed(), 0);

        auto accu = entry.getResultsAsync(true);
        EXPECT_EQ(true, accu.empty());
        EXPECT_TRUE(entry.running());
    }

    {
        auto ready = GetEntrySafe(pm, files[0].u8string());
        ASSERT_NE(nullptr, ready);

        std::vector<char> accu;
        auto success = WaitForSuccess(5000ms, [&]() -> bool {
            accu = ready->getResultsAsync(true);
            return !accu.empty();
        });

        ASSERT_TRUE(success);
        // something in result and running
        std::string a = TestConvertToString(accu);
        ASSERT_TRUE(!a.empty());

        auto table = cma::tools::SplitString(a, G_EndOfString);
        auto tdt_1 = StringToTime(table[1]);
        ASSERT_TRUE(!tdt_1.invalid());

        // this is a bit artificial
        ready->resetData();

        accu.clear();
        success = WaitForSuccess(5000ms, [&]() -> bool {
            accu = ready->getResultsAsync(true);
            return !accu.empty();
        });

        ASSERT_TRUE(success);
        // something in result and running
        table = cma::tools::SplitString(a, G_EndOfString);
        a = TestConvertToString(accu);
        ASSERT_TRUE(!a.empty());

        table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_EQ(table.size(), 2);
        EXPECT_EQ(table[0] + "\n",
                  section::MakeHeader(async0_files[0].section_name));
        auto tdt_2 = StringToTime(table[1]);
        ASSERT_TRUE(!tdt_1.invalid());
        EXPECT_TRUE(tdt_2.hour != tdt_1.hour ||  //
                    tdt_2.min != tdt_1.min ||    //
                    tdt_2.sec != tdt_1.sec ||    //
                    tdt_2.msec != tdt_1.msec);
    }
}

static const int LocalUnitCacheAge = cma::cfg::kMinimumCacheAge;
std::vector<cma::cfg::Plugins::ExeUnit> local_units_async = {
    //       Async  Timeout CacheAge              Retry  Run
    // clang-format off
    {"*.cmd",
     "async: yes\ntimeout: 10\ncache_age: 120\nretry_count: 3\nrun: yes\n"},
    {"*",     "run: no"},
    // clang-format on
};

std::vector<cma::cfg::Plugins::ExeUnit> local_units_sync = {
    //       Async  Timeout CacheAge              Retry  Run
    // clang-format off
    {"*.cmd",
     "async: no\ntimeout: 10\ncache_age: 120\nretry_count: 3\nrun: yes\n"},
    {"*",     "run: no"},
    // clang-format on
};

static std::pair<uint64_t, uint64_t> ParseCached(const std::string& data) {
    // parse this string:
    //                  "cached(123456,1200) text anything here"
    // to get those two fields:
    //                          <-1--> <2->
    const std::regex pattern(R"(cached\((\d+),(\d+)\))");
    try {
        auto time_now = std::regex_replace(
            data, pattern, "$1", std::regex_constants::format_no_copy);
        auto cache_age = std::regex_replace(
            data, pattern, "$2", std::regex_constants::format_no_copy);
        return {std::stoull(time_now), std::stoull(cache_age)};
    } catch (const std::exception& e) {
        XLOG::SendStringToStdio(
            std::string("Exception during tests: ") + e.what(),
            XLOG::Colors::red);
        return {};
    }
}

PluginDescVector local_files_async = {{1, "local0.cmd", "local0"},
                                      {1, "local1.cmd", "local1"}};

PluginDescVector local_files_sync = {{1, "local0_s.cmd", "local0_s"},
                                     {1, "local1_s.cmd", "local1_s"}};

TEST(PluginTest, AsyncLocal) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    auto files = PrepareFilesAndStructures(local_files_async,
                                           R"(echo 1 name %time%)"
                                           "\n"
                                           R"(echo 2 name %time%)",
                                           provider::PluginType::local);

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : files) fs::remove(f, ec););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, true, files, local_units_async, false);

    // async part should provide nothing
    for (auto& entry_pair : pm) {
        auto& name = entry_pair.first;
        auto& entry = entry_pair.second;
        EXPECT_EQ(entry.failures(), 0);
        EXPECT_EQ(entry.failed(), 0);

        auto accu = entry.getResultsAsync(true);
        EXPECT_EQ(true, accu.empty());
        EXPECT_TRUE(entry.running());
    }

    cma::TestDateTime tdt[2];
    for (const auto& f : files) {
        auto ready = GetEntrySafe(pm, f.u8string());
        ASSERT_NE(nullptr, ready);

        std::vector<char> accu;
        auto success = WaitForSuccess(5000ms, [&]() -> bool {
            accu = ready->getResultsAsync(true);
            return !accu.empty();
        });

        ASSERT_TRUE(success);
        // something in result and running
        std::string a = TestConvertToString(accu);
        ASSERT_TRUE(!a.empty());

        auto base_table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_TRUE(base_table.size() == 2);
        int i = 0;
        for (auto& bt : base_table) {
            auto table = cma::tools::SplitString(bt, " ", 1);

            ASSERT_TRUE(table.size() == 2);
            auto [time_now, cache_age] = ParseCached(table[0]);

            ASSERT_TRUE(time_now != 0);
            EXPECT_EQ(cache_age, LocalUnitCacheAge);

            tdt[i] = StringToTime(table[1]);
            ASSERT_TRUE(!tdt[i].invalid());
            i++;
        }
    }
    for (const auto& f : files) {
        // this is a bit artificial
        auto ready = GetEntrySafe(pm, f.u8string());
        ASSERT_NE(nullptr, ready);
        ready->resetData();
    }

    for (const auto& f : files) {
        // this is a bit artificial
        auto ready = GetEntrySafe(pm, f.u8string());
        ASSERT_NE(nullptr, ready);

        std::vector<char> accu;
        auto success = WaitForSuccess(5000ms, [&]() -> bool {
            accu = ready->getResultsAsync(true);
            return !accu.empty();
        });

        ASSERT_TRUE(success);
        // something in result and running
        auto a = TestConvertToString(accu);

        auto base_table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_TRUE(base_table.size() == 2);
        int i = 0;
        for (auto& bt : base_table) {
            auto table = cma::tools::SplitString(bt, " ", 1);

            ASSERT_TRUE(table.size() == 2);
            auto [time, cache_age] = ParseCached(table[0]);

            auto tdt_2 = StringToTime(table[1]);
            ASSERT_TRUE(!tdt_2.invalid());
            EXPECT_TRUE(tdt_2.hour != tdt[i].hour ||  //
                        tdt_2.min != tdt[i].min ||    //
                        tdt_2.sec != tdt[i].sec ||    //
                        tdt_2.msec != tdt[i].msec);
            i++;
        }
    }
}  // namespace cma

TEST(PluginTest, SyncLocal) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    auto files = PrepareFilesAndStructures(local_files_sync,
                                           R"(echo 1 name %time%)"
                                           "\n"
                                           R"(echo 2 name %time%)",
                                           provider::PluginType::local);

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : files) fs::remove(f, ec););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, true, files, local_units_sync, false);

    // async part should provide nothing
    cma::TestDateTime tdt[2];
    for (const auto& f : files) {
        auto ready = GetEntrySafe(pm, f.u8string());
        ASSERT_NE(nullptr, ready);

        auto accu = ready->getResultsSync(L"");

        ASSERT_TRUE(!accu.empty());
        // something in result and running
        std::string a = TestConvertToString(accu);
        ASSERT_TRUE(!a.empty());

        auto base_table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_TRUE(base_table.size() == 2);
        int i = 0;
        for (auto& bt : base_table) {
            auto table = cma::tools::SplitString(bt, " ", 2);

            ASSERT_TRUE(table.size() == 3);

            tdt[i] = StringToTime(table[2]);
            ASSERT_TRUE(!tdt[i].invalid());
            i++;
        }
    }

    // this is a bit artificial
    for (const auto& f : files) {
        auto ready = GetEntrySafe(pm, f.u8string());
        ready->resetData();
    }

    for (const auto& f : files) {
        auto ready = GetEntrySafe(pm, f.u8string());
        auto accu = ready->getResultsSync(L"");

        ASSERT_TRUE(!accu.empty());
        // something in result and running
        auto a = TestConvertToString(accu);

        auto base_table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_TRUE(base_table.size() == 2);
        int i = 0;
        for (auto& bt : base_table) {
            auto table = cma::tools::SplitString(bt, " ", 2);

            auto tdt_2 = StringToTime(table[2]);
            ASSERT_TRUE(!tdt_2.invalid());
            EXPECT_TRUE(tdt_2.hour != tdt[i].hour ||  //
                        tdt_2.min != tdt[i].min ||    //
                        tdt_2.sec != tdt[i].sec ||    //
                        tdt_2.msec != tdt[i].msec);
            i++;
        }
    }
}

PluginDescVector plugins_file_group = {{1, "local0_s.cmd", "local0_s"}};

std::vector<cma::cfg::Plugins::ExeUnit> plugins_file_group_param = {
    //       Async  Timeout CacheAge              Retry  Run
    // clang-format off
    {"*.cmd",
     "async: no\ntimeout: 10\ncache_age: 120\nretry_count: 3\nrun: yes\ngroup: Users\n"},
    {"*",     "run: no"},
    // clang-format on
};

// Check that plugin is started from the valid user in group
TEST(PluginTest, SyncPluginsGroup) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    auto files = PrepareFilesAndStructures(plugins_file_group,
                                           R"(@echo 2 name %username%)",
                                           provider::PluginType::normal);

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : files) fs::remove(f, ec););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, true, files, plugins_file_group_param, false);

    // async part should provide nothing
    for (const auto& f : files) {
        auto ready = GetEntrySafe(pm, f.u8string());
        ASSERT_NE(nullptr, ready);

        auto accu = ready->getResultsSync(L"");

        ASSERT_TRUE(!accu.empty());
        // something in result and running
        std::string a = TestConvertToString(accu);
        ASSERT_TRUE(!a.empty());

        auto base_table = cma::tools::SplitString(a, G_EndOfString);
        ASSERT_TRUE(base_table.size() == 2);
        ASSERT_TRUE(base_table[1] == "2 name cmk_TST_Users");
    }
}

TEST(PluginTest, EmptyPlugins) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));

    {
        cma::provider::PluginsProvider plugins;
        auto yaml = GetLoadedConfig();
        yaml[groups::kGlobal][vars::kSectionsEnabled] = YAML::Load("[plugins]");

        groups::global.loadFromMainConfig();
        plugins.updateSectionStatus();
        auto result = plugins.generateContent("", true);
        ASSERT_TRUE(!result.empty());
        EXPECT_EQ(result, "<<<>>>\n<<<>>>\n");
    }

    // legacy behavior
    {
        cma::provider::LocalProvider plugins;
        auto yaml = GetLoadedConfig();
        yaml[groups::kGlobal][vars::kSectionsEnabled] = YAML::Load("[local]");

        groups::global.loadFromMainConfig();
        plugins.updateSectionStatus();
        auto result = plugins.generateContent(section::kLocal, true);
        ASSERT_TRUE(result.empty());
    }

    // new behavior
    {
        using namespace cma::provider;
        bool no_send_if_empty_body = config::G_LocalNoSendIfEmptyBody;
        bool send_empty_end = config::G_LocalSendEmptyAtEnd;
        ON_OUT_OF_SCOPE(config::G_LocalNoSendIfEmptyBody =
                            no_send_if_empty_body;
                        config::G_LocalSendEmptyAtEnd = send_empty_end;)

        config::G_LocalNoSendIfEmptyBody = false;
        config::G_LocalSendEmptyAtEnd = true;
        cma::provider::LocalProvider plugins;
        auto yaml = GetLoadedConfig();
        yaml[groups::kGlobal][vars::kSectionsEnabled] = YAML::Load("[local]");

        groups::global.loadFromMainConfig();
        plugins.updateSectionStatus();
        auto result = plugins.generateContent(section::kLocal, true);
        ASSERT_FALSE(result.empty());
        EXPECT_EQ(result, "<<<local:sep(0)>>>\n<<<>>>\n");
    }
}

TEST(PluginTest, SyncStartSimulation_Long) {
    using namespace cma::cfg;
    using namespace wtools;
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    std::vector<Plugins::ExeUnit> exe_units = {
        //
        {"*.cmd",
         "async: no\ntimeout: 10\ncache_age: 500\nretry_count: 3\nrun: yes\n"},  //
        {"*", "run: no\n"},  //

    };

    fs::path temp_folder = cma::cfg::GetTempDir();

    PathVector vp = {
        (temp_folder / "a.cmd").u8string(),  //
        (temp_folder / "b.cmd").u8string(),  //
        (temp_folder / "c.cmd").u8string(),  //
        (temp_folder / "d.cmd").u8string(),  //
    };
    CreatePluginInTemp(vp[0], 5, "a");
    CreatePluginInTemp(vp[1], 0, "b");
    CreatePluginInTemp(vp[2], 3, "c");
    CreatePluginInTemp(vp[3], 120, "d");

    std::vector<std::string> strings = {
        "<<<a>>>",  //
        "<<<b>>>",  //
        "<<<c>>>",  //
        "<<<d>>>",  //
    };

    ON_OUT_OF_SCOPE(for (auto& f : vp) fs::remove(f););

    PluginMap pm;  // load from the groups::plugin
    UpdatePluginMap(pm, false, vp, exe_units, false);

    // retry count test
    {
        PluginMap pm_1;  // load from the groups::plugin
        PathVector vp_1 = {vp[3]};

        UpdatePluginMap(pm_1, false, vp_1, exe_units, false);
        auto f = pm_1.begin();
        auto& entry = f->second;

        for (int i = 0; i < entry.retry(); ++i) {
            auto accu = entry.getResultsSync(L"id", 0);
            EXPECT_TRUE(accu.empty());
            EXPECT_EQ(entry.failures(), i + 1);
            EXPECT_FALSE(entry.failed());
        }

        auto accu = entry.getResultsSync(L"id", 0);
        EXPECT_TRUE(accu.empty());
        EXPECT_EQ(entry.failures(), 4);
        EXPECT_TRUE(entry.failed());
    }

    // sync part
    for (auto& entry_pair : pm) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;
        EXPECT_EQ(entry.failures(), 0);
        EXPECT_EQ(entry.failed(), 0);

        if (entry_name == vp[0]) {
            auto accu = entry.getResultsSync(L"id", 0);
            EXPECT_TRUE(accu.empty());  // wait precise 0 sec, nothing
                                        // should be presented
        }

        if (entry_name == vp[3]) {
            auto accu = entry.getResultsSync(L"id", 1);
            EXPECT_TRUE(accu.empty());  // wait precise 0 sec, nothing
                                        // should be presented
        }

        auto accu = entry.getResultsSync(L"id");

        if (vp[3] == entry_name) {
            EXPECT_EQ(true, accu.empty());
            EXPECT_EQ(entry.failures(), 2);
            EXPECT_EQ(entry.failed(), 0);
        } else {
            std::string result(accu.begin(), accu.end());
            EXPECT_TRUE(!accu.empty());
            accu.clear();
            auto table = cma::tools::SplitString(result, "\r\n");
            ASSERT_EQ(table.size(), 2);
            EXPECT_TRUE(table[0] == strings[0] ||  //
                        table[0] == strings[1] ||  //
                        table[0] == strings[2]);
            EXPECT_EQ(table[1], SecondLine);
        }
    }
}

TEST(CmaMain, Config) {
    EXPECT_EQ(TheMiniBox::StartMode::job, GetStartMode("abc.exe"));
    std::filesystem::path path = ".";

    EXPECT_EQ(TheMiniBox::StartMode::updater,
              GetStartMode(path / cfg::files::kAgentUpdater));
    auto str = (path / cfg::files::kAgentUpdater).wstring();
    cma::tools::WideUpper(str);

    EXPECT_EQ(TheMiniBox::StartMode::updater, GetStartMode(str));
}

TEST(CmaMain, MiniBoxStartMode) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [source, target] = tst::CreateInOut();
    auto path = target / "a.bat";

    CreatePluginInTemp(path, 0, "aaa");

    for (auto mode :
         {TheMiniBox::StartMode::job, TheMiniBox::StartMode::updater}) {
        TheMiniBox mb;

        auto started = mb.start(L"x", path, mode);
        ASSERT_TRUE(started);

        auto pid = mb.getProcessId();
        std::vector<char> accu;
        auto success = mb.waitForEnd(std::chrono::seconds(3));
        ASSERT_TRUE(success);
        // we have probably data, try to get and and store
        mb.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                              uint32_t Code, const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);

            cma::tools::AddVector(accu, data);
        });

        EXPECT_TRUE(!accu.empty());
    }
}

TEST(CmaMain, MiniBoxStartModeDeep) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    auto [source, target] = tst::CreateInOut();
    auto path = target / "a.bat";

    CreateComplicatedPluginInTemp(path, "aaa");
    {
        TheMiniBox mb;

        auto started = mb.start(L"x", path, TheMiniBox::StartMode::job);
        ASSERT_TRUE(started);

        auto pid = mb.getProcessId();
        std::vector<char> accu;
        auto success = mb.waitForEnd(std::chrono::seconds(3));
        ASSERT_TRUE(success);
        // we have probably data, try to get and and store
        mb.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                              uint32_t Code, const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);

            cma::tools::AddVector(accu, data);
        });

        EXPECT_TRUE(!accu.empty());
        EXPECT_EQ(accu.size(), 200);  // 200 is from complicated plugin
    }

    // this code is for testing vbs scripts, not usable
    if (1) {
        auto path = target / "a.vbs";
        CreateVbsPluginInTemp(path, "aaa");
        TheMiniBox mb;

        auto started = mb.start(L"x", path, TheMiniBox::StartMode::job);
        ASSERT_TRUE(started);

        auto pid = mb.getProcessId();
        std::vector<char> accu;
        auto success = mb.waitForEnd(std::chrono::seconds(30));
        ASSERT_TRUE(success);
        // we have probably data, try to get and and store
        mb.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                              uint32_t Code, const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);

            cma::tools::AddVector(accu, data);
        });

        EXPECT_TRUE(!accu.empty());
        EXPECT_TRUE(accu.size() > 38000);  // 38000 is from complicated plugin
    }

    {
        TheMiniBox mb;

        auto started = mb.start(L"x", path, TheMiniBox::StartMode::job);
        ASSERT_TRUE(started);

        auto pid = mb.getProcessId();
        std::vector<char> accu;
        auto success = mb.waitForEnd(std::chrono::milliseconds(20));
        EXPECT_FALSE(success);
        // we have probably data, try to get and and store
        mb.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                              uint32_t Code, const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);

            cma::tools::AddVector(accu, data);
        });

        EXPECT_TRUE(accu.size() < 200);  // 200 is from complicated plugin
    }
}
#if 0
static std::string s_user_config =
    "global:\n"
    "  enabled: true\n"
    "  async_script_execution: parallel\n"
    "  encrypted: yes\n"
    "  realtime:\n"
    "    encrypted: yes\n"
    "  passphrase: XXXXXXXXXX\n"
    "  port: 6556\n"
    "local:\n"
    "  enabled: true\n"
    "  execution:\n"
    "    - pattern: \"*\"\n"
    "      async: yes\n"
    "plugins:\n"
    "  enabled: true\n"
    "  execution:\n"
    "    - pattern: $CUSTOM_PLUGINS_PATH$\\*\n"
    "      async: yes\n"
    "    - pattern: $CUSTOM_PLUGINS_PATH$\\mssql.vbs\n"
    "      retry_count: 3\n"
    "      timeout: 45\n"
    "    - pattern: $CUSTOM_PLUGINS_PATH$\\mk_mysql.vbs\n"
    "      retry_count: 1\n"
    "      timeout: 45\n"
    "    - pattern: $CUSTOM_PLUGINS_PATH$\\msexch_database.ps1\n"
    "      retry_count: 1\n"
    "      timeout: 120\n";

TEST(PluginTest, CheckRules) {
    namespace fs = std::filesystem;

    ON_OUT_OF_SCOPE(cma::OnStart(AppType::test));
    tst::SafeCleanTmpxDir();
    {
        fs::path root = tst::very_temp;
        std::error_code ec;
        fs::create_directory(root, ec);
        tst::ConstructFile(root / cma::cfg::files::kDefaultMainConfig,
                           s_user_config);
        cma::tools::win::WithEnv we(std::wstring(kTemporaryRoot),
                                    root.wstring());
        cma::OnStart(AppType::exe);
        EXPECT_TRUE(false);
    }
}
#endif
TEST(PluginTest, DebugInit) {
    std::vector<cma::cfg::Plugins::ExeUnit> exe_units_valid_SYNC_local = {
        //       Async  Timeout CacheAge              Retry  Run
        // clang-format off
    {"*.cmd", false, 10,     0, 3,     true},
    {"*",     false, 10,     0, 3,     false},
        // clang-format on
    };
    EXPECT_EQ(0, exe_units_valid_SYNC_local[0].cacheAge());
    EXPECT_FALSE(exe_units_valid_SYNC_local[0].async());
}

static std::string MakeHeader(std::string_view left, std::string_view rght,
                              std::string_view name) {
    return std::string(left) + name.data() + rght.data();
}

TEST(PluginTest, HackingPiggyBack) {
    using namespace cma::section;
    {
        EXPECT_EQ(kFooter4Left, "<<<<");
        EXPECT_EQ(kFooter4Right, ">>>>");
    }

    const std::string_view name = "Name";

    {
        const auto normal = MakeHeader(kLeftBracket, kRightBracket, name);
        // find piggyback
        EXPECT_FALSE(GetPiggyBackName(normal));
    }

    {
        const auto pb = MakeHeader(kFooter4Left, kFooter4Right, name);
        // find piggyback
        ASSERT_TRUE(GetPiggyBackName(pb));
        EXPECT_EQ(*GetPiggyBackName(pb), name);
    }

    {
        auto pb = MakeHeader(kFooter4Left, "", name);
        EXPECT_FALSE(GetPiggyBackName(pb));

        pb = MakeHeader(kFooter4Right, kFooter4Left, name);
        EXPECT_FALSE(GetPiggyBackName(pb));

        pb = MakeHeader(kFooter4Left, kRightBracket, name);
        EXPECT_FALSE(GetPiggyBackName(pb));

        pb = MakeHeader(kLeftBracket, kFooter4Right, name);
        EXPECT_FALSE(GetPiggyBackName(pb));

        pb = MakeHeader(kFooter4Left, kFooter4Left, name);
        EXPECT_FALSE(GetPiggyBackName(pb));
        pb = MakeHeader(kFooter4Right, kFooter4Right, name);
        EXPECT_FALSE(GetPiggyBackName(pb));

        EXPECT_FALSE(GetPiggyBackName(" <<<<>>>>"));
        EXPECT_FALSE(GetPiggyBackName(" <<<<A>>>>"));

        pb = MakeHeader(kFooter4Left, "", name);
        // find piggyback
        EXPECT_FALSE(GetPiggyBackName(pb));
    }

    {
        const auto pb_empty = MakeHeader(kFooter4Left, kFooter4Right, "");
        // find piggyback
        ASSERT_TRUE(GetPiggyBackName(pb_empty));
        EXPECT_EQ(*GetPiggyBackName(pb_empty), "");
    }
}

TEST(PluginTest, Hacking) {
    using namespace cma::section;

    {
        EXPECT_EQ(kFooter4Left, "<<<<");
        EXPECT_EQ(kFooter4Right, ">>>>");
    }

    const std::string_view name = "Name";
    const std::string cached_info = ":cached(12344545, 600)";

    const auto normal = MakeHeader(kLeftBracket, kRightBracket, name);

    const auto normal_empty =
        MakeHeader(cma::section::kLeftBracket, kRightBracket, "");

    const auto normal_cached = MakeHeader(kLeftBracket, kRightBracket,
                                          std::string(name) + cached_info);
    {
        auto a = normal;
        auto success = cma::TryToHackStringWithCachedInfo(a, cached_info);
        EXPECT_TRUE(success);
        EXPECT_EQ(a, normal_cached);
    }

    {
        auto x = normal_empty;
        auto success = cma::TryToHackStringWithCachedInfo(x, cached_info);
        EXPECT_TRUE(success);
        EXPECT_EQ(x, MakeHeader(kLeftBracket, kRightBracket, cached_info));

        std::string arr[] = {"<<a>>>", "<<<a>>", "<<>>>", "<<<", "", ">>>"};
        for (auto& a : arr)
            EXPECT_FALSE(cma::TryToHackStringWithCachedInfo(a, cached_info));
    }
}

}  // namespace cma
