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
    cma::OnStart(cma::AppType::test);
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
    cma::OnStart(cma::AppType::test);

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
    EXPECT_EQ(paths.size(), 2);
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
            cma::tools::win::GetSomeSystemFolderA(FOLDERID_Public);
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
            cma::tools::win::GetSomeSystemFolderA(FOLDERID_Public);
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
            cma::tools::win::GetSomeSystemFolderA(FOLDERID_Public);
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

TEST(FileInfoTest, MakeFileInfo) {
    namespace fs = std::filesystem;
    {
        auto ret = details::GetOsPathWithCase(L"c:\\Windows\\notepad.EXE");
        EXPECT_EQ(ret.wstring(), L"C:\\Windows\\notepad.exe");
    }  // namespace fs=std::filesystem;

    {
        auto x = details::MakeFileInfoString("c:\\Windows\\notepad.EXE");
        EXPECT_TRUE(!x.empty());
        ASSERT_EQ(x.back(), '\n');
        x.pop_back();

        auto table = cma::tools::SplitString(x, "|");
        EXPECT_EQ(table.size(), 3);
        EXPECT_EQ(table[0], "C:\\Windows\\notepad.exe");
        EXPECT_TRUE(std::stoll(table[1]) > 0);
        EXPECT_TRUE(std::stoll(table[2]) > 0);
    }

    {
        auto x = details::MakeFileInfoString("c:\\Windows\\notepad.EXEs");
        EXPECT_TRUE(!x.empty());
        ASSERT_EQ(x.back(), '\n');
        x.pop_back();

        auto table = cma::tools::SplitString(x, "|");
        EXPECT_EQ(table.size(), 3);
        EXPECT_EQ(table[0], "C:\\Windows\\notepad.EXEs");
        EXPECT_TRUE(std::stoll(table[1]) == 0);
        EXPECT_TRUE(std::stoll(table[2]) == 0);
    }
}

}  // namespace cma::provider
