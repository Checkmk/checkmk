// test-fileinfo.cpp

//
#include "pch.h"
#define _SILENCE_EXPERIMENTAL_FILESYSTEM_DEPRECATION_WARNING
#include <experimental/filesystem>
#include <filesystem>
#include <ranges>

#include "cfg.h"
#include "common/wtools.h"
#include "glob_match.h"
#include "providers/fileinfo.h"
#include "providers/fileinfo_details.h"
#include "service_processor.h"
#include "test-utf-names.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace cma::provider {
namespace {
std::vector<std::string> MakeBody(FileInfo &fi) {
    auto table = tools::SplitString(fi.generateContent(), "\n");
    table.erase(table.begin());
    return table;
}

}  // namespace

static void CheckString(std::string &x) {
    EXPECT_TRUE(!x.empty());
    ASSERT_EQ(x.back(), '\n');
    x.pop_back();
}

static void CheckTableMissing(std::vector<std::string> &table,
                              std::string_view name, FileInfo::Mode mode) {
    ASSERT_TRUE(table.size() >= 2);
    EXPECT_EQ(table[0], name.data());
    EXPECT_EQ(table[1], FileInfo::kMissing.data());
    if (mode == FileInfo::Mode::legacy) {
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(std::atoll(table[2].c_str()) > 0LL);
    }
}

static void CheckTablePresent(std::vector<std::string> &table,
                              std::string_view name, FileInfo::Mode mode) {
    auto shift = mode == FileInfo::Mode::modern ? 1 : 0;

    ASSERT_EQ(table.size(), 3 + shift);
    EXPECT_NE(table[0], name);
    EXPECT_TRUE(tools::IsEqual(table[0], name));
    if (shift) {
        EXPECT_EQ(table[1], FileInfo::kOk);
    }

    EXPECT_TRUE(std::stoll(table[1 + shift]) > 0);
    EXPECT_TRUE(std::stoll(table[2 + shift]) > 0);
}

fs::path BuildTestUNC() {
    auto comp = tools::win::GetEnv("COMPUTERNAME");
    if (comp.empty()) {
        XLOG::l("No COMPUTERNAME");
        return {};
    }

    return fs::path{"\\\\" + comp} / "shared_public";
}

TEST(FileInfoTest, SplitOK) {
    std::pair<std::wstring, std::wstring> data[] = {
        {LR"(\\DEV\)", LR"(path\to*)"},
        {LR"(c:\)", LR"(path\to*)"},
    };

    for (const auto &[h, b] : data) {
        auto [head, body] =
            details::SplitFileInfoPathSmart(std::wstring{h} + b);
        EXPECT_EQ(head.wstring(), h);
        EXPECT_EQ(body.wstring(), b);
    }
}

TEST(FileInfoTest, SplitBad) {
    std::pair<std::wstring, std::wstring> data[] = {
        {L"", LR"(path\to*)"},
        {L"c:", LR"(path\to*)"},
    };

    for (const auto &[h, b] : data) {
        auto [head, body] =
            details::SplitFileInfoPathSmart(std::wstring{h} + b);
        EXPECT_TRUE(head.empty());
        EXPECT_TRUE(body.empty());
    }
}

TEST(FileInfoTest, Globs) {
    using details::GlobType;
    EXPECT_EQ(details::DetermineGlobType(L"**"), GlobType::kRecursive);
    EXPECT_EQ(details::DetermineGlobType(L"*s*"), GlobType::kSimple);
    EXPECT_EQ(details::DetermineGlobType(L"*s?"), GlobType::kSimple);
    EXPECT_EQ(details::DetermineGlobType(L"?ssss"), GlobType::kSimple);
    EXPECT_EQ(details::DetermineGlobType(L"*"), GlobType::kSimple);
    EXPECT_EQ(details::DetermineGlobType(L"*s*"), GlobType::kSimple);
    EXPECT_EQ(details::DetermineGlobType(L""), GlobType::kNone);
    EXPECT_EQ(details::DetermineGlobType(L"asefdef!.dfg"), GlobType::kNone);
}

TEST(FileInfoTest, ValidFileInfoPathEntry) {
    EXPECT_TRUE(!details::ValidFileInfoPathEntry("a\\x"));
    EXPECT_TRUE(!details::ValidFileInfoPathEntry("c:a\\x"));
    EXPECT_TRUE(!details::ValidFileInfoPathEntry("\\a\\x"));
    EXPECT_TRUE(details::ValidFileInfoPathEntry("\\\\a\\x"));
    EXPECT_TRUE(details::ValidFileInfoPathEntry("d:\\a\\x"));
    EXPECT_TRUE(details::ValidFileInfoPathEntry("D:\\a\\x"));
}

constexpr const char *hdr = "<<<fileinfo:sep(124)>>>";
TEST(FileInfoTest, ValidateConfig) {
    auto test_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(test_fs->loadConfig(tst::GetFabricYml()));

    auto cfg = cfg::GetLoadedConfig();
    auto x = cfg[cfg::groups::kFileInfo];
    ASSERT_TRUE(x);
    ASSERT_TRUE(x.IsMap());

    auto p = x[cfg::vars::kFileInfoPath];
    ASSERT_TRUE(p);
    ASSERT_TRUE(p.IsSequence());
}

class FileInfoFixture : public ::testing::Test {
public:
    void loadFilesInConfig() {
        auto cfg = cfg::GetLoadedConfig();

        cfg[cfg::groups::kFileInfo][cfg::vars::kFileInfoPath] = YAML::Load(
            "['c:\\windows\\notepad.exe','c:\\windows\\explorer.exe']");
    }

    std::vector<std::string> generate() {
        FileInfo fi;
        auto result = fi.generateContent();

        EXPECT_EQ(result.back(), '\n');
        return tools::SplitString(result, "\n");
    }

protected:
    void SetUp() override {
        test_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(test_fs_->loadConfig(tst::GetFabricYml()));
    }

    void TearDown() override {}
    tst::TempCfgFs::ptr test_fs_;
};

TEST_F(FileInfoFixture, ValidateConfig) {
    auto cfg = cfg::GetLoadedConfig();

    auto fileinfo_node = cfg[cfg::groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());

    EXPECT_TRUE(
        cfg::GetVal(cfg::groups::kFileInfo, cfg::vars::kEnabled, false));

    auto paths = cfg::GetArray<std::string>(cfg::groups::kFileInfo,
                                            cfg::vars::kFileInfoPath);
    EXPECT_TRUE(paths.empty());
}

TEST_F(FileInfoFixture, ConfigWithoutFiles) {
    // we generate data using fabric config
    auto table = generate();

    // The expected Result
    // <<<fileinfo:sep(124)>>>\n
    // 123456788\n
    EXPECT_EQ(table[0], hdr);
    EXPECT_TRUE(!table[1].empty());

    auto val = std::stoll(table[1]);
    EXPECT_TRUE(val > 100000);

    // retry generation, results should be same
    table = generate();

    EXPECT_EQ(table[0], hdr);
    EXPECT_TRUE(!table[1].empty());
}

TEST_F(FileInfoFixture, ConfigWithFiles) {
    // we simulate changing in config
    loadFilesInConfig();
    // we generate data using changed config
    auto table = generate();

    // The expected Result
    // <<<fileinfo:sep(124)>>>\n
    // 123456788\n
    // c:\windows\notepad.exe|1345|123456788\n
    // c:\windows\explorer.exe|1345|123456788\n

    // check is simplified now
    EXPECT_EQ(table[0], hdr);
    EXPECT_EQ(table.size(), 4);
    EXPECT_TRUE(std::stoll(table[1]) > 100000);
}

TEST(FileInfoTest, Misc) {
    EXPECT_TRUE(FileInfo::ContainsGlobSymbols("ss*ddfff"));
    EXPECT_TRUE(FileInfo::ContainsGlobSymbols("*"));
    EXPECT_TRUE(FileInfo::ContainsGlobSymbols("?"));
    EXPECT_TRUE(FileInfo::ContainsGlobSymbols("ss*ddfff?"));
    EXPECT_FALSE(FileInfo::ContainsGlobSymbols("sddfff"));
    EXPECT_FALSE(FileInfo::ContainsGlobSymbols("s_fff"));
    EXPECT_FALSE(FileInfo::ContainsGlobSymbols(""));

    EXPECT_EQ(FileInfo::kMissing, "missing");
    EXPECT_EQ(FileInfo::kOk, "ok");
    EXPECT_EQ(FileInfo::kStatFailed, "stat failed");
}

TEST(FileInfoTest, CheckDriveLetter) {
    auto test_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(test_fs->loadFactoryConfig());
    auto [a, b] = tst::CreateInOut();

    std::tuple<fs::path, std::string_view> data[] = {{a / "a1.txt", "a1"},
                                                     {a / "a2.txt", "a2"}};

    for (const auto &[path, content] : data) {
        tst::CreateTextFile(path, content);
    }

    auto cfg = cfg::GetLoadedConfig();
    auto fileinfo_node = cfg[cfg::groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());
    auto value = a.u8string();
    value[0] = std::tolower(value[0]);
    auto str = fmt::format("['{}\\*.txt', 'c:\\weirdfile' ]", value);
    fileinfo_node[cfg::vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[cfg::vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi{FileInfo::Mode::legacy};
        auto table = MakeBody(fi);
        ASSERT_EQ(table.size(), 4);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        EXPECT_EQ(table[1][0], value[0]);
        EXPECT_EQ(table[2][0], value[0]);
        EXPECT_EQ(table[3][0], value[0]);
    }
    value[0] = std::toupper(value[0]);
    str = fmt::format("['{}\\*.txt', 'C:\\weirdfile']", value);
    fileinfo_node[cfg::vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[cfg::vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi{FileInfo::Mode::legacy};
        auto table = MakeBody(fi);
        ASSERT_EQ(table.size(), 4);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        EXPECT_EQ(table[1][0], value[0]);
        EXPECT_EQ(table[2][0], value[0]);
        EXPECT_EQ(table[3][0], value[0]);
    }
}

TEST(FileInfoTest, CheckOutput) {
    auto test_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(test_fs->loadFactoryConfig());
    auto [a, b] = tst::CreateInOut();

    std::tuple<fs::path, std::string_view> data[] = {{a / "a1.txt", "a1"},
                                                     {b / "b1.cmd", "b1"},
                                                     {b / "b2.cmd", "b2"},
                                                     {b / "b3.txt", "b3"},
                                                     {a / "a2.cmd", "a2"}};

    for (const auto &[path, content] : data) tst::CreateTextFile(path, content);

    auto cfg = cfg::GetLoadedConfig();
    auto fileinfo_node = cfg[cfg::groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());
    std::string name_without_glob{"c:\\aaaaa.asdd"};
    std::string name_with_glob{"c:\\Windows\\*.sdfcfdf"};
    auto str =
        fmt::format("['{}\\*.txt', '{}\\*.cmd', '{}', '{}']", a.u8string(),
                    b.u8string(), name_without_glob, name_with_glob);
    fileinfo_node[cfg::vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[cfg::vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi{FileInfo::Mode::legacy};
        auto table = MakeBody(fi);
        ASSERT_EQ(table.size(), 6);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        table.erase(table.begin());

        auto missing = table.back();
        auto values = tools::SplitString(missing, "|");
        CheckTableMissing(values, name_with_glob, FileInfo::Mode::legacy);
        std::error_code ec;
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        missing = table.back();
        values = tools::SplitString(missing, "|");
        CheckTableMissing(values, name_without_glob, FileInfo::Mode::legacy);
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        for (auto line : table) {
            auto values = tools::SplitString(line, "|");
            ASSERT_TRUE(values.size() == 3);
            EXPECT_TRUE(fs::exists(values[0], ec));
            EXPECT_TRUE(std::atoll(values[1].c_str()) == 2);
            EXPECT_TRUE(std::atoll(values[2].c_str()) > 0LL);
            auto f = std::any_of(
                std::begin(data), std::end(data),
                [values](std::tuple<fs::path, std::string_view> entry) {
                    auto const &[path, _] = entry;
                    return tools::IsEqual(path.u8string(), values[0]);
                });
            EXPECT_TRUE(f);
        }
    }

    {
        FileInfo fi{FileInfo::Mode::modern};
        auto table = MakeBody(fi);
        ASSERT_EQ(table.size(), 9);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0);
        table.erase(table.begin());
        EXPECT_EQ(table[0], "[[[header]]]");
        table.erase(table.begin());
        EXPECT_EQ(table[0], "name|status|size|time");
        table.erase(table.begin());
        EXPECT_EQ(table[0], "[[[content]]]");
        table.erase(table.begin());

        auto missing = table.back();
        auto values = tools::SplitString(missing, "|");
        CheckTableMissing(values, name_with_glob, FileInfo::Mode::modern);
        std::error_code ec;
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        missing = table.back();
        values = tools::SplitString(missing, "|");
        CheckTableMissing(values, name_without_glob, FileInfo::Mode::modern);
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        for (auto line : table) {
            auto values = tools::SplitString(line, "|");
            ASSERT_TRUE(values.size() == 4);
            EXPECT_TRUE(fs::exists(values[0], ec));
            EXPECT_EQ(values[1], FileInfo::kOk);
            EXPECT_TRUE(std::atoll(values[2].c_str()) == 2);
            EXPECT_TRUE(std::atoll(values[2].c_str()) > 0LL);
            auto f = std::any_of(
                std::begin(data), std::end(data),
                [values](std::tuple<fs::path, std::string_view> entry) {
                    auto const &[path, _] = entry;
                    return tools::IsEqual(path.u8string(), values[0]);
                });
            EXPECT_TRUE(f);
        }
    }
}

TEST(FileInfoTest, FindFileByMask) {
    using details::FindFilesByMask;
    ASSERT_TRUE(fs::exists("c:\\windows\\system32"))
        << "unit tests works for windows on c in windows folder";

    // invalid entry
    EXPECT_TRUE(FindFilesByMask(L"c:indows\\notepad.exe").empty());
    // valid entry
    EXPECT_EQ(FindFilesByMask(L"c:\\windows\\notepad.exe").size(), 1U);
    // invalid relative entry
    EXPECT_TRUE(FindFilesByMask(L"windows\\notepad.exe").empty());
    // more than one file
    EXPECT_EQ(FindFilesByMask(L"c:\\windows\\*\\taskmgr.exe").size(), 2U);
    // search for one file
    auto files = FindFilesByMask(L"c:\\windows\\??????32\\taskmgr.exe");
    EXPECT_EQ(files.size(), 1);  // syswow64 and system32
    EXPECT_EQ(files[0].u8string(), "c:\\windows\\System32\\taskmgr.exe");
}
TEST(FileInfoTest, Unc) {
    // UNC
    fs::path p = BuildTestUNC();
    std::error_code ec;
    if (fs::exists(p, ec)) {
        auto files = details::FindFilesByMask(p.wstring() + L"\\*.*");
        EXPECT_TRUE(files.size() >= 2);  //
        EXPECT_EQ(files[0].u8string(), p / "test.txt");
    } else {
        XLOG::l(XLOG::kStdio)("File '{}' doesn't exist. SKIPPING TEST",
                              p.u8string());
    }
}

class FileInfoTestFixture : public ::testing::Test {
public:
    void SetUp() override {
        work_dir_ = tst::GetTempDir() / "file_info_test";
        fs::create_directories(work_dir_ / "1\\2\\3");
        fs::create_directories(work_dir_ / "3");
        fs::create_directories(work_dir_ / "4");
        fs::create_directories(work_dir_ / "5");
        // create 6 files to be found by "**"
        v_.emplace_back(work_dir_ / "1" / "2" / "x.txt");  // **/x.txt
        v_.emplace_back(work_dir_ / "3" / "x.txt");        // */x.txt **/x.txt
        v_.emplace_back(work_dir_ / "4" / "x.txt");        // */x.txt **/x.txt
        v_.emplace_back(work_dir_ / "a.txt");
        v_.emplace_back(work_dir_ / "b.txt");
        v_.emplace_back(work_dir_ / "x.txt");
        rs::for_each(v_, [&](const auto &x) { tst::CreateTextFile(x, "x"); });
    }
    void TearDown() override {
        std::error_code ec;
        fs::remove_all(work_dir_, ec);
    }

    fs::path work_dir_;
    std::vector<fs::path> v_;
};

TEST_F(FileInfoTestFixture, Glob) {
    auto files = details::FindFilesByMask((work_dir_ / "**").wstring());
    EXPECT_EQ(files.size(), 6);

    auto sorted = files;
    rs::sort(sorted);
    EXPECT_EQ(files, sorted);
    EXPECT_EQ(files, v_);
    files = details::FindFilesByMask((work_dir_ / "*" / "x.txt").wstring());
    EXPECT_EQ(files.size(), 2);

    files = details::FindFilesByMask((work_dir_ / "**" / "x.txt").wstring());
    EXPECT_EQ(files.size(), 3);
}

TEST(FileInfoTest, WindowsResources) {
    fs::path win_res_path = "c:\\windows\\Resources\\";
    auto files = details::FindFilesByMask(
        (win_res_path / "**" / "aero" / "aero*.*").wstring());
    EXPECT_TRUE(files.size() == 2)
        << "Normal OS HAVE TO HAVE only 2 aero msstyles files in windows/resources";
}

TEST(FileInfoTest, Unicode) {
    auto p = BuildTestUNC();
    std::error_code ec;
    if (fs::exists(p, ec)) {
        fs::path path{test_u8_name};
        try {
            auto files = details::FindFilesByMask(p.wstring() + L"\\*.*");
            EXPECT_TRUE(files.size() >= 2);  // syswow64 and system32
            EXPECT_TRUE(std::find(files.begin(), files.end(), p / "test.txt") !=
                        std::end(files));
            auto russian_file = p / test_russian_file;
            auto w_name = russian_file.wstring();
            auto ut8_name = russian_file.u8string();
            auto utf8_name_2 = wtools::ToUtf8(w_name);
            EXPECT_TRUE(std::find(files.begin(), files.end(), w_name) !=
                        std::end(files));
        } catch (const std::exception &e) {
            XLOG::l("Error {} ", e.what());
        }
    } else {
        XLOG::l(XLOG::kStdio)("File '{}' doesn't exist. SKIPPING TEST/2", p);
    }
}

constexpr FileInfo::Mode modes[] = {FileInfo::Mode::legacy,
                                    FileInfo::Mode::modern};

TEST(FileInfoTest, MakeFileInfoMissing) {
    for (auto &n : {
             "aaa",
             "C:\\Windows\\notepad.EXEs",
             "C:\\Windows\\*.EXEs",
         }) {
        for (auto m : modes) {
            SCOPED_TRACE(
                fmt::format("'{}' mode is {}", n, static_cast<int>(m)));
            auto x = details::MakeFileInfoStringMissing(n, m);
            CheckString(x);

            auto table = tools::SplitString(x, "|");
            CheckTableMissing(table, n, m);
        }
    }
}

namespace {
/// \brief - returns Unix time of the file
///
/// function which was valid in 1.6 and still valid
/// because experimental is deprecated we can't it use anymore, but we can test
int64_t SecondsSinceEpoch(const std::string &name) {
    namespace fs = std::experimental::filesystem::v1;
    fs::path fp{name};

    auto write_time = fs::last_write_time(fp);
    auto time_since_epoch = std::chrono::duration_cast<std::chrono::seconds>(
        write_time.time_since_epoch());
    return time_since_epoch.count();
}
}  // namespace

TEST(FileInfoTest, MakeFileInfoExisting) {
    // EXPECTED strings
    // "fname|ok|500|153334455\n"
    // "fname|500|153334455\n"

    const std::string fname{"c:\\Windows\\noTepad.exE"};
    auto expected_time = SecondsSinceEpoch(fname);

    for (auto mode : modes) {
        SCOPED_TRACE(fmt::format("Mode is {}", static_cast<int>(mode)));
        static const std::string name = "c:\\Windows\\notepad.EXE";
        auto x = details::MakeFileInfoString(name, mode);
        CheckString(x);

        auto table = cma::tools::SplitString(x, "|");
        CheckTablePresent(table, name, mode);
        auto ftime = std::atoll(table[table.size() - 1].c_str());
        auto cur_time = std::chrono::system_clock::to_time_t(
            std::chrono::system_clock::now());
        EXPECT_GT(cur_time, ftime);
        EXPECT_EQ(expected_time, ftime);
    }
}

TEST(FileInfoTest, MakeFileInfoPagefile) {
    for (auto mode : modes) {
        static const std::string name{"c:\\pagefile.sys"};
        auto x = details::MakeFileInfoString(name, mode);
        x.pop_back();
        auto table = tools::SplitString(x, "|");
        auto ftime = std::atoll(table[table.size() - 1].c_str());
        auto cur_time = std::chrono::system_clock::to_time_t(
            std::chrono::system_clock::now());
        EXPECT_GT(cur_time, ftime);
        auto sz = std::atoll(table[table.size() - 2].c_str());
        EXPECT_GT(sz, 0);
    }
}

TEST(FileInfoTest, GetOsPathWithCase) {
    auto good = details::GetOsPathWithCase(L"c:\\Windows\\notepad.EXE");
    EXPECT_EQ(good.wstring(), L"C:\\Windows\\notepad.exe");

    auto bad = details::GetOsPathWithCase(L"c:\\WIndows\\ZZ\\notepad.EXE");
    EXPECT_EQ(bad.wstring(), L"C:\\Windows\\ZZ\\notepad.EXE");
}

}  // namespace cma::provider
