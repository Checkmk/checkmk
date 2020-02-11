// test-fileinfo.cpp

//
#include "pch.h"

#include <filesystem>

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

namespace cma::provider {

static void CheckString(std::string& x) {
    EXPECT_TRUE(!x.empty());
    ASSERT_EQ(x.back(), '\n');
    x.pop_back();
}

static void CheckTableMissing(std::vector<std::string>& table,
                              std::string_view name, FileInfo::Mode mode) {
    ASSERT_TRUE(table.size() >= 2);
    EXPECT_EQ(table[0], name.data());
    EXPECT_EQ(table[1], FileInfo::kMissing.data());
    if (mode == FileInfo::Mode::legacy) {
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(std::atoll(table[2].c_str()) > 0LL);
    }
}

static void CheckTablePresent(std::vector<std::string>& table,
                              std::string_view name, FileInfo::Mode mode) {
    auto shift =
        mode == FileInfo::Mode::modern ? 1 : 0;  // modern: we have OK column

    ASSERT_EQ(table.size(), 3 + shift);
    EXPECT_EQ(table[0], name);
    if (shift) EXPECT_EQ(table[1], FileInfo::kOk);

    EXPECT_TRUE(std::stoll(table[1 + shift]) > 0);
    EXPECT_TRUE(std::stoll(table[2 + shift]) > 0);
}

std::filesystem::path BuildTestUNC() {
    auto comp = cma::tools::win::GetEnv("COMPUTERNAME");
    if (comp.empty()) {
        XLOG::l("No COMPUTERNAME");
        return {};
    }

    std::string root_folder = "\\\\" + comp;
    std::filesystem::path p = root_folder;
    return p / "shared_public";
}

TEST(FileInfoTest, Split) {
    {
        const wchar_t* head = L"\\\\DEV\\";
        const wchar_t* body = L"path\\to*";

        std::wstring fname = head;
        fname += body;
        auto [head_out, body_out] = details::SplitFileInfoPathSmart(fname);
        EXPECT_EQ(head_out.wstring(), head);
        EXPECT_EQ(body_out.wstring(), body);
    }

    {
        const wchar_t* head = L"c:\\";
        const wchar_t* body = L"path\\to*";

        std::wstring fname = head;
        fname += body;
        auto [head_out, body_out] = details::SplitFileInfoPathSmart(fname);
        EXPECT_EQ(head_out.wstring(), head);
        EXPECT_EQ(body_out.wstring(), body);
    }

    {
        const wchar_t* head = L"c:";
        const wchar_t* body = L"path\\to*";

        std::wstring fname = head;
        fname += body;
        auto [head_out, body_out] = details::SplitFileInfoPathSmart(fname);
        EXPECT_TRUE(head_out.empty());
        EXPECT_TRUE(body_out.empty());
    }

    {
        const wchar_t* head = L"";
        const wchar_t* body = L"path\\to*";

        std::wstring fname = head;
        fname += body;
        auto [head_out, body_out] = details::SplitFileInfoPathSmart(fname);
        EXPECT_TRUE(head_out.empty());
        EXPECT_TRUE(body_out.empty());
    }
}

TEST(FileInfoTest, Globs) {
    using namespace cma::provider::details;
    {
        const wchar_t* test = L"**";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kRecursive);
    }
    {
        const wchar_t* test = L"*s*";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kSimple);
    }
    {
        const wchar_t* test = L"*s?";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kSimple);
    }
    {
        const wchar_t* test = L"?ssss";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kSimple);
    }
    {
        const wchar_t* test = L"*";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kSimple);
    }
    {
        const wchar_t* test = L"*s*";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kSimple);
    }
    {
        const wchar_t* test = L"";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kNone);
    }
    {
        const wchar_t* test = L"asefdef!.dfg";
        EXPECT_EQ(DetermineGlobType(test), GlobType::kNone);
    }
}

TEST(FileInfoTest, Base) {
    using namespace cma::provider;
    using namespace cma::cfg;
    cma::OnStartTest();
    ON_OUT_OF_SCOPE(cma::OnStartTest());
    constexpr const char* hdr = "<<<fileinfo:sep(124)>>>\n";

    //
    {
        EXPECT_TRUE(!details::ValidFileInfoPathEntry("a\\x"));
        EXPECT_TRUE(!details::ValidFileInfoPathEntry("c:a\\x"));
        EXPECT_TRUE(!details::ValidFileInfoPathEntry("\\a\\x"));
        EXPECT_TRUE(details::ValidFileInfoPathEntry("\\\\a\\x"));
        EXPECT_TRUE(details::ValidFileInfoPathEntry("d:\\a\\x"));
        EXPECT_TRUE(details::ValidFileInfoPathEntry("D:\\a\\x"));

    }  // namespace cma::provider

    {
        auto cfg = cma::cfg::GetLoadedConfig();
        auto x = cfg[groups::kFileInfo];
        ASSERT_TRUE(x);
        x.remove(vars::kFileInfoPath);
        FileInfo fi;
        auto out = fi.makeBody();
        EXPECT_TRUE(!out.empty());
        EXPECT_EQ(out.back(), '\n');
        out.pop_back();
        auto val = std::stoll(out);
        EXPECT_TRUE(val > 100000);
        cfg.remove(groups::kFileInfo);
        out = fi.makeBody();
        EXPECT_TRUE(!out.empty());
    }
    // reload config
    cma::OnStartTest();

    {
        FileInfo fi;
        auto out_h = fi.makeHeader(cma::section::kUseEmbeddedName);
        ASSERT_TRUE(!out_h.empty());
        EXPECT_EQ(out_h, hdr);

        auto cfg = cma::cfg::GetLoadedConfig();
        auto x = cfg[groups::kFileInfo];
        ASSERT_TRUE(x);
        ASSERT_TRUE(x.IsMap());

        auto p = x[vars::kFileInfoPath];
        ASSERT_TRUE(p);
        ASSERT_TRUE(p.IsSequence());

        p.reset();
        p.push_back(groups::global.fullLogFileNameAsString());

        auto out = fi.makeBody();
        ASSERT_TRUE(!out.empty());
    }
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
    // boiler plating:

    namespace fs = std::filesystem;
    using namespace cma::cfg;
    tst::SafeCleanTempDir();
    auto [a, b] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test););

    std::tuple<fs::path, std::string_view> data[] = {{a / "a1.txt", "a1"},
                                                     {a / "a2.txt", "a2"}};

    for (const auto& [path, content] : data) tst::ConstructFile(path, content);

    auto cfg = cma::cfg::GetLoadedConfig();
    auto fileinfo_node = cfg[groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());
    auto value = a.u8string();
    value[0] = std::tolower(value[0]);
    auto str = fmt::format("['{}\\*.txt', 'c:\\weirdfile' ]", value);
    fileinfo_node[vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi;
        fi.mode_ = FileInfo::Mode::legacy;
        auto out = fi.makeBody();

        ASSERT_TRUE(!out.empty());
        auto table = cma::tools::SplitString(out, "\n");
        ASSERT_EQ(table.size(), 4);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        EXPECT_EQ(table[1][0], value[0]);
        EXPECT_EQ(table[2][0], value[0]);
        EXPECT_EQ(table[3][0], value[0]);
    }
    value[0] = std::toupper(value[0]);
    str = fmt::format("['{}\\*.txt', 'C:\\weirdfile']", value);
    fileinfo_node[vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi;
        fi.mode_ = FileInfo::Mode::legacy;
        auto out = fi.makeBody();

        ASSERT_TRUE(!out.empty());
        auto table = cma::tools::SplitString(out, "\n");
        ASSERT_EQ(table.size(), 4);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        EXPECT_EQ(table[1][0], value[0]);
        EXPECT_EQ(table[2][0], value[0]);
        EXPECT_EQ(table[3][0], value[0]);
    }
}

TEST(FileInfoTest, CheckOutput) {
    // boiler plating:

    namespace fs = std::filesystem;
    using namespace cma::cfg;
    tst::SafeCleanTempDir();
    auto [a, b] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test););

    std::tuple<fs::path, std::string_view> data[] = {{a / "a1.txt", "a1"},
                                                     {b / "b1.cmd", "b1"},
                                                     {b / "b2.cmd", "b2"},
                                                     {b / "b3.txt", "b3"},
                                                     {a / "a2.cmd", "a2"}};

    for (const auto& [path, content] : data) tst::ConstructFile(path, content);

    auto cfg = cma::cfg::GetLoadedConfig();
    auto fileinfo_node = cfg[groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());
    std::string name_without_glob = "c:\\aaaaa.asdd";
    std::string name_with_glob = "c:\\Windows\\*.sdfcfdf";
    auto str =
        fmt::format("['{}\\*.txt', '{}\\*.cmd', '{}', '{}']", a.u8string(),
                    b.u8string(), name_without_glob, name_with_glob);
    fileinfo_node[vars::kFileInfoPath] = YAML::Load(str);
    ASSERT_TRUE(fileinfo_node[vars::kFileInfoPath].IsSequence());
    {
        FileInfo fi;
        fi.mode_ = FileInfo::Mode::legacy;
        auto out = fi.makeBody();

        ASSERT_TRUE(!out.empty());
        auto table = cma::tools::SplitString(out, "\n");
        ASSERT_EQ(table.size(), 6);
        EXPECT_TRUE(std::atoll(table[0].c_str()) > 0LL);
        table.erase(table.begin());

        auto missing = table.back();
        auto values = cma::tools::SplitString(missing, "|");
        CheckTableMissing(values, name_with_glob, fi.mode_);
        std::error_code ec;
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        missing = table.back();
        values = cma::tools::SplitString(missing, "|");
        CheckTableMissing(values, name_without_glob, fi.mode_);
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        for (auto line : table) {
            auto values = cma::tools::SplitString(line, "|");
            ASSERT_TRUE(values.size() == 3);
            EXPECT_TRUE(fs::exists(values[0], ec));
            EXPECT_TRUE(std::atoll(values[1].c_str()) == 2);
            EXPECT_TRUE(std::atoll(values[2].c_str()) > 0LL);
            auto f = std::any_of(
                std::begin(data), std::end(data),
                [values](std::tuple<fs::path, std::string_view> entry) {
                    auto const& [path, _] = entry;
                    return cma::tools::IsEqual(path.u8string(), values[0]);
                });
            EXPECT_TRUE(f);
        }
    }

    {
        FileInfo fi;
        ASSERT_TRUE(fi.mode_ == FileInfo::Mode::legacy)
            << "this value should be set by default";

        fi.mode_ = FileInfo::Mode::modern;
        auto out = fi.makeBody();

        ASSERT_TRUE(!out.empty());
        auto table = cma::tools::SplitString(out, "\n");
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
        auto values = cma::tools::SplitString(missing, "|");
        CheckTableMissing(values, name_with_glob, fi.mode_);
        std::error_code ec;
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        missing = table.back();
        values = cma::tools::SplitString(missing, "|");
        CheckTableMissing(values, name_without_glob, fi.mode_);
        EXPECT_FALSE(fs::exists(values[0], ec));
        table.pop_back();

        for (auto line : table) {
            auto values = cma::tools::SplitString(line, "|");
            ASSERT_TRUE(values.size() == 4);
            EXPECT_TRUE(fs::exists(values[0], ec));
            EXPECT_EQ(values[1], FileInfo::kOk);
            EXPECT_TRUE(std::atoll(values[2].c_str()) == 2);
            EXPECT_TRUE(std::atoll(values[2].c_str()) > 0LL);
            auto f = std::any_of(
                std::begin(data), std::end(data),
                [values](std::tuple<fs::path, std::string_view> entry) {
                    auto const& [path, _] = entry;
                    return cma::tools::IsEqual(path.u8string(), values[0]);
                });
            EXPECT_TRUE(f);
        }
    }
}

TEST(FileInfoTest, YmlCheck) {
    using namespace cma::cfg;
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();

    auto fileinfo_node = cfg[groups::kFileInfo];
    ASSERT_TRUE(fileinfo_node.IsDefined());
    ASSERT_TRUE(fileinfo_node.IsMap());

    auto enabled = GetVal(groups::kFileInfo, vars::kEnabled, false);
    EXPECT_TRUE(enabled);
    auto paths = GetArray<std::string>(groups::kFileInfo, vars::kFileInfoPath);
    EXPECT_EQ(paths.size(), 0);
}

TEST(FileInfoTest, Reality) {
    namespace fs = std::filesystem;
    cma::OnStart(cma::AppType::test);
    ASSERT_TRUE(fs::exists("c:\\windows\\system32"))
        << "unit tests works for windows on c in windows folder";

    // invalid entry
    {
        auto files = details::FindFilesByMask(
            fs::path("c:windows\\notepad.exe").wstring());
        EXPECT_EQ(files.size(), 0);
    }

    // valid entry
    {
        auto files = details::FindFilesByMask(
            fs::path("c:\\windows\\notepad.exe").wstring());
        EXPECT_EQ(files.size(), 1);
    }

    // invalid relative entry
    {
        auto files = details::FindFilesByMask(
            fs::path("windows\\notepad.exe").wstring());
        EXPECT_EQ(files.size(), 0);
    }

    {
        auto files = details::FindFilesByMask(
            fs::path("c:\\windows\\*\\taskmgr.exe").wstring());
        EXPECT_EQ(files.size(), 2);  // syswow64 and system32
    }

    {
        auto files = details::FindFilesByMask(
            fs::path("c:\\windows\\??????32\\taskmgr.exe").wstring());
        EXPECT_EQ(files.size(), 1);  // syswow64 and system32
        EXPECT_EQ(files[0].u8string(), "c:\\windows\\System32\\taskmgr.exe");
    }

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

    {
        // Glob REcursive
        fs::path public_folder_path =
            cma::tools::win::GetSomeSystemFolder(FOLDERID_Public);
        std::error_code ec;
        ASSERT_TRUE(fs::exists(public_folder_path, ec));
        auto files =
            details::FindFilesByMask((public_folder_path / "**").wstring());
        XLOG::t("Found {}", files.size());
        EXPECT_TRUE(files.size() > 12);

        auto sorted = files;
        std::sort(sorted.begin(), sorted.end());
        EXPECT_TRUE(files == sorted) << "output should be sorted";
        for (auto& f : files) {
            EXPECT_TRUE(fs::is_regular_file(f));
        }
    }

    // Desktop.ini
    {
        fs::path public_folder_path =
            cma::tools::win::GetSomeSystemFolder(FOLDERID_Public);
        std::error_code ec;
        ASSERT_TRUE(fs::exists(public_folder_path, ec));
        auto files = details::FindFilesByMask(
            (public_folder_path / "*" / "desktop.ini").wstring());
        XLOG::t("Found {}", files.size());
        EXPECT_TRUE(files.size() == 8)
            << "Normal OS HAVE TO HAVE only 8 ini files in Public";
    }

    // Desktop.ini recursive
    {
        fs::path public_folder_path =
            cma::tools::win::GetSomeSystemFolder(FOLDERID_Public);
        std::error_code ec;
        ASSERT_TRUE(fs::exists(public_folder_path, ec));
        auto files = details::FindFilesByMask(
            (public_folder_path / "**" / "desktop.ini").wstring());
        XLOG::t("Found {}", files.size());
        EXPECT_TRUE(files.size() == 8)
            << "Normal OS HAVE TO HAVE only 8 ini files in Public";
    }

    // Desktop.ini recursive
    {
        fs::path win_res_path = "c:\\windows\\Resources\\";

        std::error_code ec;
        ASSERT_TRUE(fs::exists(win_res_path, ec));

        auto files = details::FindFilesByMask(
            (win_res_path / "**" / "aero" / "aero*.*").wstring());
        XLOG::t("Found {}", files.size());
        EXPECT_TRUE(files.size() == 2)
            << "Normal OS HAVE TO HAVE only 2 aero msstyles files in windows/resources";
    }

    // UNICODE checking
    {
        auto p = BuildTestUNC();
        std::error_code ec;
        if (fs::exists(p, ec)) {
            fs::path path = fs::u8path(test_u8_name);
            std::string path_string = path.u8string();
            auto w_string = path.wstring();

            try {
                auto files = details::FindFilesByMask(p.wstring() + L"\\*.*");
                EXPECT_TRUE(files.size() >= 2);  // syswow64 and system32
                EXPECT_TRUE(std::find(files.begin(), files.end(),
                                      p / "test.txt") != std::end(files));
                auto russian_file = p / test_russian_file;
                auto w_name = russian_file.wstring();
                auto ut8_name = russian_file.u8string();
                auto utf8_name_2 = wtools::ConvertToUTF8(w_name);
                EXPECT_TRUE(std::find(files.begin(), files.end(), w_name) !=
                            std::end(files));
            } catch (const std::exception& e) {
                XLOG::l("Error {} ", e.what());
            }
        } else {
            XLOG::l(XLOG::kStdio)("File '{}' doesn't exist. SKIPPING TEST/2",
                                  p.u8string());
        }
    }
}

TEST(FileInfoTest, MakeFileInfoMissing) {
    static constexpr std::string_view names[] = {"aaa.aaa",
                                                 "c:\\Windows\\notepad.EXEs"};
    static constexpr FileInfo::Mode modes[] = {FileInfo::Mode::legacy,
                                               FileInfo::Mode::modern};

    for (auto& n : names) {
        for (auto m : modes) {
            SCOPED_TRACE(
                fmt::format("'{}' mode is {}", n, static_cast<int>(m)));
            auto x = details::MakeFileInfoStringMissing(n.data(), m);
            CheckString(x);

            auto table = cma::tools::SplitString(x, "|");
            CheckTableMissing(table, n, m);
        }
    }
}

TEST(FileInfoTest, MakeFileInfoPresented) {
    // EXPECTED strings
    // "fname|ok|500|153334455\n"
    // "fname|500|153334455\n"

    const std::string fname = "c:\\Windows\\noTepad.exE";
    FileInfo::Mode modes[] = {FileInfo::Mode::legacy, FileInfo::Mode::modern};

    for (auto mode : modes) {
        SCOPED_TRACE(fmt::format("Mode is {}", static_cast<int>(mode)));
        static const std::string name = "c:\\Windows\\notepad.EXE";
        auto x = details::MakeFileInfoStringPresented(name, mode);
        CheckString(x);

        auto table = cma::tools::SplitString(x, "|");
        CheckTablePresent(table, name, mode);
    }
}

TEST(FileInfoTest, MakeFileInfo) {
    namespace fs = std::filesystem;

    // check that file is present
    {
        auto ret1 = details::GetOsPathWithCase(L"c:\\Windows\\notepad.EXE");
        EXPECT_EQ(ret1.wstring(), L"C:\\Windows\\notepad.exe");

        auto ret2 = details::GetOsPathWithCase(L"c:\\WIndows\\ZZ\\notepad.EXE");
        EXPECT_EQ(ret2.wstring(), L"C:\\Windows\\ZZ\\notepad.EXE");
    }

    static constexpr std::string_view names[] = {
        "aaa", "C:\\Windows\\notepad.EXEs", "C:\\Windows\\*.EXEs"};
    static constexpr FileInfo::Mode modes[] = {FileInfo::Mode::legacy,
                                               FileInfo::Mode::modern};

    for (auto& n : names) {
        for (auto m : modes) {
            SCOPED_TRACE(
                fmt::format("'{}' mode is {}", n, static_cast<int>(m)));

            auto x = details::MakeFileInfoString(n.data(), m);
            CheckString(x);

            auto table = cma::tools::SplitString(x, "|");
            CheckTableMissing(table, n, m);
        }
    }

    static constexpr std::string_view names_2[] = {"C:\\Windows\\notepad.exe"};
    for (auto& n : names_2) {
        for (auto m : modes) {
            SCOPED_TRACE(
                fmt::format("'{}' mode is {}", n, static_cast<int>(m)));

            auto x = details::MakeFileInfoString(n.data(), m);
            CheckString(x);

            auto table = cma::tools::SplitString(x, "|");
            CheckTablePresent(table, n, m);
        }
    }

    if (0) {
        auto x = details::MakeFileInfoString(
            "we do not know how to test this case in Windows",
            FileInfo::Mode::modern);

        CheckString(x);

        auto table = cma::tools::SplitString(x, "|");
        CheckTablePresent(table, "C:\\Windows\\notepad.exe",
                          FileInfo::Mode::modern);
    }
}

}  // namespace cma::provider
