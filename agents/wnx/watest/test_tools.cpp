//
// test-tools.cpp :

#include "pch.h"

#include "test_tools.h"

#include <shellapi.h>

#include <filesystem>
#include <random>
#include <string>
#include <string_view>

#include "algorithm"  // for remove_if
#include "cfg.h"
#include "corecrt_terminate.h"  // for terminate
#include "exception"            // for terminate
#include "firewall.h"
#include "fmt/format.h"
#include "install_api.h"  // for terminate
#include "on_start.h"
#include "tools/_misc.h"
#include "tools/_tgt.h"          // for IsDebug
#include "yaml-cpp/emitter.h"    // for Emitter
#include "yaml-cpp/node/emit.h"  // for operator<<
#include "yaml-cpp/node/node.h"  // for Node

namespace fs = std::filesystem;

namespace tst {

void AllowReadWriteAccess(const std::filesystem::path& path,
                          std::vector<std::wstring>& commands) {
    constexpr std::wstring_view command_templates[] = {
        L"icacls \"{}\" /inheritance:d /c",  // disable inheritance
        L"icacls \"{}\" /grant:r *S-1-5-32-545:(OI)(CI)(RX) /c"};  // read/exec

    for (auto const t : command_templates) {
        auto cmd = fmt::format(t.data(), path.wstring());
        commands.emplace_back(cmd);
    }
    XLOG::l.i("Protect file from User write '{}'", path);
}

std::string GetFabricYmlContent() {
    static std::string fabric_yaml_content;
    static bool one_run{false};
    if (!one_run) {
        one_run = true;
        try {
            fabric_yaml_content = wtools::ReadWholeFile(GetFabricYml());
        } catch (const std::exception& e) {
            XLOG::l("Exception '{}' loading fabric yaml", e.what());
        }
    }

    return fabric_yaml_content;
}

class TestEnvironment : public ::testing::Environment {
public:
    static constexpr std::string_view temp_test_prefix_{"tmp_watest"};
    virtual ~TestEnvironment() = default;

    void SetUp() override {
        auto test_root = cma::tools::win::GetEnv(cma::env::test_root);
        if (!test_root.empty() && fs::exists(test_root)) {
            temp_dir_ = fs::path(test_root) / temp_test_prefix_;
        } else {
            auto folder_name = fmt::format("{}_{}", temp_test_prefix_,
                                           ::GetCurrentProcessId());
            temp_dir_ = fs::temp_directory_path() / folder_name;
        }
        fs::create_directories(temp_dir_);
    }

    void TearDown() override {
        if (temp_dir_.u8string().find(temp_test_prefix_)) {
            fs::remove_all(temp_dir_);
            fs::remove(temp_dir_);
        }
    }

    [[nodiscard]] fs::path getTempDir() const noexcept { return temp_dir_; }

private:
    fs::path temp_dir_;
};

::testing::Environment* const g_env =
    ::testing::AddGlobalTestEnvironment(new TestEnvironment);

fs::path GetTempDir() {
    return dynamic_cast<TestEnvironment*>(g_env)->getTempDir();
}

TempDirPair::TempDirPair(const std::string& case_name) {
    path_ = GetTempDir() / case_name;
    in_ = path_ / "in";
    out_ = path_ / "out";
    fs::create_directories(path_);
    fs::create_directories(in_);
    fs::create_directories(out_);
}

TempDirPair::~TempDirPair() {
    try {
        fs::remove_all(path_);
    } catch (const std::filesystem::filesystem_error& e) {
        XLOG::l("Failure deleting '{}' exception '{}'", path_, e.what());
    }
}

fs::path GetProjectRoot() { return fs::path{PROJECT_DIR}; }
fs::path GetSolutionRoot() { return fs::path{SOLUTION_DIR}; }
fs::path GetUnitTestFilesRoot() {
    return MakePathToUnitTestFiles(GetSolutionRoot());
}

// below described the structure of the solution folder:
// solution root <--- Use SOLUTION_DIR define
//    \--- test_files
//            \--- unit_tests <--- MakePathToUnitTestFiles(SolutionRoot)
//            \--- config     <--- MakePathToConfigTestFiles(SolutionRoot)
constexpr std::wstring_view kSolutionTestFilesFolderName(L"test_files");
constexpr std::wstring_view kSolutionUnitTestsFolderName(L"unit_test");
constexpr std::wstring_view kSolutionConfigTestFilesFolderName(L"config");
constexpr std::wstring_view kSolutionCapTestFilesFolderName(L"cap");

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

std::filesystem::path MakePathToCapTestFiles(const std::wstring& root) {
    std::filesystem::path r{root};
    r = r / kSolutionTestFilesFolderName / kSolutionCapTestFilesFolderName;
    return r.lexically_normal();
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

namespace {
template <typename T, typename V>
void RemoveElement(T& Container, const V& Str) {
    Container.erase(std::remove_if(Container.begin(), Container.end(),
                                   [Str](const std::string& Candidate) {
                                       return cma::tools::IsEqual(Str,
                                                                  Candidate);
                                   }),
                    Container.end());
}

template <typename T, typename V>
bool AddElement(T& container, const V& value) {
    // add section name to internal array if not found
    if (std::end(container) ==
        std::find(container.begin(), container.end(), value)) {
        container.emplace_back(value);
        return true;
    }
    return false;
}

enum class SectionMode { enable, disable };

void ChangeSectionMode(std::string_view value, bool update_global,
                       SectionMode mode) {
    using cma::cfg::GetInternalArray;
    using cma::cfg::PutInternalArray;
    namespace groups = cma::cfg::groups;
    namespace vars = cma::cfg::vars;

    auto section_add = mode == SectionMode::enable ? vars::kSectionsEnabled
                                                   : vars::kSectionsDisabled;
    auto section_del = mode == SectionMode::disable ? vars::kSectionsEnabled

                                                    : vars::kSectionsDisabled;
    auto add = GetInternalArray(groups::kGlobal, section_add);
    auto del = GetInternalArray(groups::kGlobal, section_del);

    if (AddElement(add, value)) {
        PutInternalArray(groups::kGlobal, section_add, add);
    }

    RemoveElement(del, value);
    PutInternalArray(groups::kGlobal, section_del, del);

    if (update_global) {
        groups::global.loadFromMainConfig();
    }
}

}  // namespace

void EnableSectionsNode(std::string_view value, bool update_global) {
    return ChangeSectionMode(value, update_global, SectionMode::enable);
}

void DisableSectionsNode(std::string_view value, bool update_global) {
    return ChangeSectionMode(value, update_global, SectionMode::disable);
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
    fs::path temp_folder{GetTempDir()};
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

TempCfgFs::TempCfgFs(Mode mode) : mode_{mode} {
    namespace fs = std::filesystem;
    base_ = MakeTempFolderInTempPath(std::wstring(L"test_") +
                                     GenerateRandomFileName());
    root_ = base_ / "r";
    data_ = base_ / "d";
    if (mode_ == Mode::standard) {
        fs::create_directories(root_);
        fs::create_directories(data_);
        cma::cfg::GetCfg().pushFolders(root_, data_);
    } else {
        cma::cfg::GetCfg().pushFoldersNoIo(root_, data_);
    }
    yaml_ = YAML::Clone(cma::cfg::GetLoadedConfig());
}

TempCfgFs ::~TempCfgFs() {
    cma::cfg::GetCfg().popFolders();
    if (mode_ == Mode::standard) {
        std::filesystem::remove_all(base_);
    }
    cma::cfg::GetCfg().setConfig(yaml_);
}

bool TempCfgFs::loadConfig(const std::filesystem::path& yml) {
    std::vector<std::wstring> cfg_files;
    if (mode_ == Mode::standard) {
        std::filesystem::copy_file(
            yml, root() / cma::cfg::files::kDefaultMainConfig);

        cfg_files.emplace_back(cma::cfg::files::kDefaultMainConfig);
    } else {
        cfg_files.emplace_back(yml);
    }

    auto ret = cma::LoadConfigBase(cfg_files, cma::YamlCacheOp::nothing);
    if (ret) {
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }

    return ret;
}

bool TempCfgFs::reloadConfig() {
    std::vector<std::wstring> cfg_files;
    if (mode_ == Mode::standard) {
        cfg_files.emplace_back(cma::cfg::files::kDefaultMainConfig);
    } else {
        XLOG::l("No io mode doesnt allow reloading");
        return false;
    }

    auto ret = cma::LoadConfigBase(cfg_files, cma::YamlCacheOp::update);
    if (ret) {
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }

    return ret;
}

bool TempCfgFs::loadFactoryConfig() { return loadConfig(tst::GetFabricYml()); }

bool TempCfgFs::loadContent(std::string_view content) {
    auto ret = cma::cfg::GetCfg().loadDirect(content);
    if (ret) {
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }

    return ret;
}

void TempCfgFs::allowUserAccess() {
    std::vector<std::wstring> commands;
    tst::AllowReadWriteAccess(base_, commands);
    wtools::ExecuteCommandsSync(L"all", commands);
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
    return tst::GetSolutionRoot() / "install" / "resources" /
           cma::cfg::files::kDefaultMainConfig;
}

namespace {
enum class WaitForSuccessMode { silent, indicate };

bool WaitForSuccess(std::chrono::milliseconds ms, WaitForSuccessMode mode,
                    std::function<bool()> predicat) {
    using namespace std::chrono_literals;
    auto count = ms / 20ms;

    auto success = false;

    for (int i = 0; i < count; i++) {
        if (mode == WaitForSuccessMode::indicate) {
            if (i % 10 == 9) {
                xlog::sendStringToStdio(".", xlog::internal::Colors::yellow);
            }
        }
        if (predicat()) {
            success = true;
            break;
        }
        cma::tools::sleep(20ms);
    }

    if (mode == WaitForSuccessMode::indicate) {
        xlog::sendStringToStdio("\n", xlog::internal::Colors::yellow);
    }
    return success;
}
}  // namespace

bool WaitForSuccessIndicate(std::chrono::milliseconds ms,
                            std::function<bool()> predicat) {
    return WaitForSuccess(ms, WaitForSuccessMode::indicate, predicat);
}

bool WaitForSuccessSilent(std::chrono::milliseconds ms,
                          std::function<bool()> predicat) {
    return WaitForSuccess(ms, WaitForSuccessMode::silent, predicat);
}

namespace {
constexpr std::wstring_view firewall_test_rule_name = L"CMK_TEST_RULE";
}

FirewallOpener::FirewallOpener() {
    int count = 0;
    auto res = ::CommandLineToArgvW(::GetCommandLineW(), &count);
    if (res == nullptr) {
        XLOG::l("can't read argv");
        ::abort();
    }
    argv0_ = res[0];

    if (!cma::fw::CreateInboundRule(firewall_test_rule_name, argv0_, -1)) {
        XLOG::l("can't read argv");
        ::abort();
    }
}

FirewallOpener::~FirewallOpener() {
    if (!argv0_.empty()) {
        cma::fw::RemoveRule(firewall_test_rule_name, argv0_);
    }
}

namespace misc {
void CopyFailedPythonLogFileToLog(const std::filesystem::path& data) {
    const auto& the_file =
        tst::MakePathToUnitTestFiles() / "agent_msi.failed.python.log";
    fs::create_directories(data / cma::cfg::dirs::kLog);
    fs::copy_file(the_file, fs::path{cma::cfg::GetLogDir()} /
                                cma::install::kMsiLogFileName);
}
}  // namespace misc

}  // namespace tst
