// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef test_tools_h__
#define test_tools_h__
//

#include <chrono>
#include <functional>
#include <vector>

#include "cfg.h"
#include "common/yaml.h"
#include "iosfwd"                // for ofstream
#include "on_start.h"            // for OnStart, AppType, AppType::test
#include "system_error"          // for error_code
#include "xstring"               // for string, basic_string, wstring
#include "yaml-cpp/node/impl.h"  // for Node::Node, Node::~Node
namespace YAML {
class Node;
}

namespace tst {

std::filesystem::path MakePathToUnitTestFiles(const std::wstring& root);
std::filesystem::path MakePathToConfigTestFiles(const std::wstring& root);

///  from the TestEnvironment
[[nodiscard]] std::filesystem::path GetTempDir();

class YamlLoader {
public:
    YamlLoader() {
        using namespace cma::cfg;
        std::error_code ec;
        std::filesystem::remove(cma::cfg::GetBakeryFile(), ec);
        cma::OnStart(cma::AppType::test);

        auto yaml = GetLoadedConfig();
        ProcessKnownConfigGroups();
        SetupEnvironmentFromGroups();
    }
    ~YamlLoader() { OnStart(cma::AppType::test); }
};

void SafeCleanTempDir();
void SafeCleanTempDir(std::string_view sub_dir);

inline void CreateTextFile(const std::filesystem::path& path,
                           std::string_view content) {
    std::ofstream ofs(path);

    ofs << content;
}

inline void CreateBinaryFile(const std::filesystem::path& path,
                             std::string_view data) {
    std::ofstream ofs(path, std::ios::binary);

    ofs.write(data.data(), data.size());
}

inline std::filesystem::path CreateIniFile(
    const std::filesystem::path& lwa_path, const std::string content,
    const std::string yaml_name) {
    auto ini_file = lwa_path / (yaml_name + ".ini");
    CreateTextFile(lwa_path / ini_file, content);
    return ini_file;
}

inline std::filesystem::path CreateWorkFile(const std::filesystem::path& path,
                                            const std::string& content) {
    CreateBinaryFile(path, content + "\n");
    return path;
}

// Storage for temporary in out dir
class TempDirPair {
public:
    TempDirPair(const std::string& case_name);
    TempDirPair(const TempDirPair&) = delete;
    TempDirPair(TempDirPair&&) = delete;
    TempDirPair& operator=(const TempDirPair&) = delete;
    TempDirPair& operator=(TempDirPair&&) = delete;

    ~TempDirPair();
    std::filesystem::path in() const noexcept { return in_; }
    std::filesystem::path out() const noexcept { return out_; }

private:
    std::filesystem::path path_;
    std::filesystem::path in_;
    std::filesystem::path out_;
};

inline std::tuple<std::filesystem::path, std::filesystem::path> CreateInOut() {
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    auto normal_dir =
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos;
    if (normal_dir) {
        std::error_code ec;
        auto lwa_dir = temp_dir / "in";
        auto pd_dir = temp_dir / "out";
        fs::create_directories(lwa_dir, ec);
        fs::create_directories(pd_dir, ec);
        return {lwa_dir, pd_dir};
    }
    return {};
}

inline std::filesystem::path CreateDirInTemp(std::wstring_view Dir) {
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    auto normal_dir =
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos;
    if (normal_dir) {
        std::error_code ec;
        auto lwa_dir = temp_dir / Dir;
        fs::create_directories(lwa_dir, ec);
        return lwa_dir;
    }
    return {};
}

// add Str to enabled sections and remove from disabled
// optionally updates parameters in Config
void EnableSectionsNode(std::string_view value, bool update_global);
void DisableSectionsNode(std::string_view value, bool update_global);

inline void SafeCleanBakeryDir() {
    namespace fs = std::filesystem;
    auto bakery_dir = cma::cfg::GetBakeryDir();
    auto normal_dir = bakery_dir.find(L"\\bakery", 0) != std::wstring::npos;
    if (normal_dir) {
        // clean
        fs::remove_all(bakery_dir);
        fs::create_directory(bakery_dir);
    } else {
        XLOG::l("attempt to delete suspicious dir {}",
                wtools::ToUtf8(bakery_dir));
    }
}

const std::string_view very_temp = "tmpx";

void SafeCleanTmpxDir();

void PrintNode(YAML::Node node, std::string_view S);
std::vector<std::string> ReadFileAsTable(const std::string& Name);

using CheckYamlVector =
    std::vector<std::pair<std::string_view, YAML::NodeType::value>>;
inline void CheckYaml(YAML::Node table, const CheckYamlVector& vec) {
    int pos = 0;
    for (auto t : table) {
        EXPECT_EQ(t.first.as<std::string>(), vec[pos].first);
        EXPECT_EQ(t.second.Type(), vec[pos].second);
        ++pos;
    }
}

constexpr std::string_view zip_to_test = "unzip_test.zip";
constexpr std::string_view cab_to_test = "uncab_test.zip";  // cab! file

std::filesystem::path MakeTempFolderInTempPath(std::wstring_view folder_name);
std::wstring GenerateRandomFileName() noexcept;

/// \brief RAII class to change folder structure in the config
class TempCfgFs {
public:
    enum class Mode { standard, no_io };
    TempCfgFs() : TempCfgFs(Mode::standard) {}
    TempCfgFs(Mode mode);

    TempCfgFs(const TempCfgFs&) = delete;
    TempCfgFs(TempCfgFs&&) = delete;
    TempCfgFs& operator=(const TempCfgFs&) = delete;
    TempCfgFs& operator=(TempCfgFs&&) = delete;

    ~TempCfgFs();

    [[nodiscard]] bool loadConfig(const std::filesystem::path& yml);

    [[nodiscard]] bool loadContent(std::string_view config);

    [[nodiscard]] bool createRootFile(const std::filesystem::path& relative_p,
                                      const std::string& content) const;
    [[nodiscard]] bool createDataFile(const std::filesystem::path& relative_p,
                                      const std::string& content) const;

    void removeRootFile(const std::filesystem::path& relative_p) const;
    void removeDataFile(const std::filesystem::path& relative_p) const;

    const std::filesystem::path root() const { return root_; }
    const std::filesystem::path data() const { return data_; }

private:
    [[nodiscard]] static bool createFile(
        const std::filesystem::path& filepath,
        const std::filesystem::path& filepath_base, const std::string& content);
    static void removeFile(const std::filesystem::path& filepath,
                           const std::filesystem::path& filepath_base);
    std::filesystem::path root_;
    std::filesystem::path data_;
    std::filesystem::path base_;
    Mode mode_;
};

const extern std::filesystem::path G_SolutionPath;
std::filesystem::path GetFabricYml();
std::string GetFabricYmlContent();

bool WaitForSuccess(std::chrono::milliseconds ms,
                    std::function<bool()> predicat);

}  // namespace tst
#endif  // test_tools_h__
