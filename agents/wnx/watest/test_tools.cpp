//
// test-tools.cpp :

#include "pch.h"

#include "test_tools.h"

#include <random>
#include <string>
#include <string_view>

#include "algorithm"  // for remove_if
#include "cfg.h"
#include "corecrt_terminate.h"  // for terminate
#include "exception"            // for terminate
#include "on_start.h"
#include "tools/_misc.h"
#include "tools/_tgt.h"          // for IsDebug
#include "yaml-cpp/emitter.h"    // for Emitter
#include "yaml-cpp/node/emit.h"  // for operator<<
#include "yaml-cpp/node/node.h"  // for Node

namespace tst {
const std::filesystem::path G_ProjectPath = PROJECT_DIR;
const std::filesystem::path G_SolutionPath = SOLUTION_DIR;
const std::filesystem::path G_TestPath =
    MakePathToUnitTestFiles(G_SolutionPath);

// below described the structure of the solution folder:
// solution root <--- Use SOLUTION_DIR define
//    \--- test_files
//            \--- unit_tests <--- MakePathToUnitTestFiles(SolutionRoot)
//            \--- config     <--- MakePathToConfigTestFiles(SolutionRoot)
constexpr std::wstring_view kSolutionTestFilesFolderName(L"test_files");
constexpr std::wstring_view kSolutionUnitTestsFolderName(L"unit_test");
constexpr std::wstring_view kSolutionConfigTestFilesFolderName(L"config");

std::filesystem::path MakePathToUnitTestFiles(const std::wstring& root) {
    std::filesystem::path r{root};
    r = r / kSolutionTestFilesFolderName / kSolutionUnitTestsFolderName;
    return r.lexically_normal();
}

std::filesystem::path MakePathToConfigTestFiles(const std::wstring& root) {
    std::filesystem::path r{root};
    r = r / kSolutionTestFilesFolderName / kSolutionConfigTestFilesFolderName;
    return r.lexically_normal();
}

void PrintNode(YAML::Node node, std::string_view S) {
    if (tgt::IsDebug()) {
        YAML::Emitter emit;
        emit << node;
        XLOG::l("{}:\n{}", S, emit.c_str());
    }
}

void SafeCleanTempDir() {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto really_temp_dir = temp_dir.find(L"\\tmp", 0) != std::wstring::npos;
    if (!really_temp_dir) return;

    // clean
    std::error_code ec;
    fs::remove_all(temp_dir, ec);
    if (ec)
        XLOG::l("error removing '{}' with {} ", wtools::ToUtf8(temp_dir),
                ec.message());
    fs::create_directory(temp_dir);
}

void SafeCleanTmpxDir() {
    namespace fs = std::filesystem;
    if (very_temp != "tmpx") {
        XLOG::l.crit(
            "Recursive folder remove is allowed only for very temporary folders");
        std::terminate();
        return;
    }

    // clean
    std::error_code ec;
    fs::remove_all(very_temp, ec);
    if (ec)
        XLOG::l("error removing '{}' with {} ", wtools::ToUtf8(very_temp),
                ec.message());
}

void SafeCleanTempDir(std::string_view sub_dir) {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto really_temp_dir = temp_dir.find(L"\\tmp", 0) != std::wstring::npos;
    if (!really_temp_dir) {
        XLOG::l("attempt to delete suspicious dir {}",
                wtools::ToUtf8(temp_dir));
        return;
    }

    // clean
    fs::path t_d = temp_dir;
    std::error_code ec;
    fs::remove_all(t_d / sub_dir, ec);
    if (ec)
        XLOG::l("error removing '{}' with {} ", t_d / sub_dir, ec.message());
    fs::create_directory(t_d / sub_dir);
}

template <typename T, typename V>
void RemoveElement(T& Container, const V& Str) {
    Container.erase(std::remove_if(Container.begin(), Container.end(),
                                   [Str](const std::string& Candidate) {
                                       return cma::tools::IsEqual(Str,
                                                                  Candidate);
                                   }),
                    Container.end());
}

void EnableSectionsNode(const std::string_view& Str, bool UpdateGlobal) {
    using namespace cma::cfg;

    auto enabled = GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);

    // add section name to internal array if not found
    if (std::end(enabled) == std::find(enabled.begin(), enabled.end(), Str)) {
        enabled.emplace_back(Str);
        PutInternalArray(groups::kGlobal, vars::kSectionsEnabled, enabled);
    }

    // pattern to remove INternalArray element
    auto disabled = GetInternalArray(groups::kGlobal, vars::kSectionsDisabled);
    RemoveElement(disabled, Str);
    PutInternalArray(groups::kGlobal, vars::kSectionsDisabled, disabled);

    if (UpdateGlobal) groups::global.loadFromMainConfig();
}
std::vector<std::string> ReadFileAsTable(const std::string& Name) {
    std::ifstream in(Name.c_str());
    std::stringstream sstr;
    sstr << in.rdbuf();
    auto content = sstr.str();
    return cma::tools::SplitString(content, "\n");
}

std::filesystem::path MakeTempFolderInTempPath(std::wstring_view folder_name) {
    namespace fs = std::filesystem;
    // Find Temporary Folder
    fs::path temp_folder{cma::tools::win::GetTempFolder()};
    std::error_code ec;
    if (!fs::exists(temp_folder, ec)) {
        XLOG::l("Updating is NOT possible, temporary folder not found [{}]",
                ec.value());
        return {};
    }

    return temp_folder / folder_name;
}

std::wstring GenerateRandomFileName() noexcept {
    std::wstring possible_characters(
        L"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz");

    std::random_device rd;
    std::mt19937 generator(rd());

    std::uniform_int_distribution<> dist(
        0, static_cast<int>(possible_characters.size()) - 1);
    std::wstring ret;
    constexpr size_t kMaxLen{12};
    for (size_t i = 0; i < kMaxLen; i++) {
        int random_index = dist(generator);  // get index between 0 and
                                             // possible_characters.size()-1
        ret += possible_characters[random_index];
    }

    return ret;
}

TempCfgFs::TempCfgFs() {
    namespace fs = std::filesystem;
    base_ = MakeTempFolderInTempPath(std::wstring(L"test_") +
                                     GenerateRandomFileName());
    root_ = base_ / "r";
    fs::create_directories(root_);
    data_ = base_ / "d";
    fs::create_directories(base_);
    cma::cfg::GetCfg().pushFolders(root_, base_);
}

TempCfgFs ::~TempCfgFs() {
    cma::cfg::GetCfg().popFolders();
    std::filesystem::remove_all(base_);
}

bool TempCfgFs::loadConfig(const std::filesystem::path& yml) {
    std::filesystem::copy_file(yml,
                               root() / cma::cfg::files::kDefaultMainConfig);

    std::vector<std::wstring> cfg_files;
    cfg_files.emplace_back(cma::cfg::files::kDefaultMainConfig);

    auto ret =
        cma::cfg::InitializeMainConfig(cfg_files, cma::YamlCacheOp::nothing);
    if (ret) {
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }

    return ret;
}

[[nodiscard]] bool TempCfgFs::createFile(
    const std::filesystem::path& filepath,
    const std::filesystem::path& filepath_base, const std::string& content) {
    std::error_code ec;
    auto p = filepath_base / filepath;
    std::filesystem::remove(p, ec);
    if (ec.value() != 0 && ec.value() != 2) return false;
    std::filesystem::create_directories(p.parent_path());

    std::ofstream ofs(p);
    ofs << content;
    return true;
}

[[nodiscard]] bool TempCfgFs::createRootFile(
    const std::filesystem::path& filepath, const std::string& content) const {
    return TempCfgFs::createFile(filepath, root_, content);
}

[[nodiscard]] bool TempCfgFs::createDataFile(
    const std::filesystem::path& filepath, const std::string& content) const {
    return TempCfgFs::createFile(filepath, data_, content);
}

[[nodiscard]] void TempCfgFs::removeFile(
    const std::filesystem::path& filepath,
    const std::filesystem::path& filepath_base) {
    std::error_code ec;
    auto p = filepath_base / filepath;
    std::filesystem::remove(p, ec);
}

[[nodiscard]] void TempCfgFs::removeRootFile(
    const std::filesystem::path& filepath) const {
    TempCfgFs::removeFile(filepath, root_);
}

[[nodiscard]] void TempCfgFs::removeDataFile(
    const std::filesystem::path& filepath) const {
    TempCfgFs::removeFile(filepath, data_);
}

std::filesystem::path GetFabricYml() {
    return G_SolutionPath / "install" / "resources" /
           cma::cfg::files::kDefaultMainConfig;
}
}  // namespace tst
