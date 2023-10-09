// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TEST_TOOLS_H
#define TEST_TOOLS_H
//

#include <chrono>
#include <fstream>
#include <functional>
#include <vector>

#include "wnx/cfg.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogvista.h"
#include "iosfwd"                // for ofstream
#include "wnx/on_start.h"            // for OnStart, AppType, AppType::test
#include "system_error"          // for error_code
#include "xstring"               // for string, basic_string, wstring
#include "yaml-cpp/node/impl.h"  // for Node::Node, Node::~Node
namespace YAML {
class Node;
}

namespace tst {
// located in test_files/config
constexpr const wchar_t *kDefaultDevConfigUTF16 = L"check_mk_dev_utf16.yml";
constexpr const wchar_t *kDefaultDevMinimum = L"check_mk_dev_minimum.yml";
constexpr const wchar_t *kDefaultDevUt = L"check_mk_dev_unit_testing.yml";

std::filesystem::path GetSolutionRoot();
std::filesystem::path GetProjectRoot();
std::filesystem::path GetUnitTestFilesRoot();

std::filesystem::path MakePathToTestsFiles(const std::wstring &root);
std::filesystem::path MakePathToUnitTestFiles(const std::wstring &root);
inline std::filesystem::path MakePathToUnitTestFiles() {
    return MakePathToUnitTestFiles(GetSolutionRoot());
}
std::filesystem::path MakePathToConfigTestFiles(const std::wstring &root);
inline std::filesystem::path MakePathToConfigTestFiles() {
    return MakePathToConfigTestFiles(GetSolutionRoot());
}
std::filesystem::path MakePathToCapTestFiles(const std::wstring &root);
inline std::filesystem::path MakePathToCapTestFiles() {
    return MakePathToCapTestFiles(GetSolutionRoot());
}

std::string GetUnitTestName();

///  from the TestEnvironment
[[nodiscard]] std::filesystem::path GetTempDir();

class YamlLoader {
public:
    YamlLoader() {
        std::error_code ec;
        std::filesystem::remove(cma::cfg::GetBakeryFile(), ec);
        cma::OnStartTest();

        auto yaml = cma::cfg::GetLoadedConfig();
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();
    }
    YamlLoader(const YamlLoader &) = delete;
    YamlLoader &operator=(const YamlLoader &) = delete;
    ~YamlLoader() { cma::OnStartTest(); }
};

void SafeCleanTempDir();
void SafeCleanTempDir(std::string_view sub_dir);

inline void CreateTextFile(const std::filesystem::path &path,
                           std::string_view content) {
    std::ofstream ofs(path);

    ofs << content;
}

inline void CreateBinaryFile(const std::filesystem::path &path,
                             std::string_view data) {
    std::ofstream ofs(path, std::ios::binary);

    ofs.write(data.data(), static_cast<std::streamsize>(data.size()));
}

inline std::filesystem::path CreateIniFile(
    const std::filesystem::path &lwa_path, const std::string &content,
    const std::string &yaml_name) {
    auto ini_file = lwa_path / (yaml_name + ".ini");
    CreateTextFile(lwa_path / ini_file, content);
    return ini_file;
}

inline std::filesystem::path CreateWorkFile(const std::filesystem::path &path,
                                            const std::string &content) {
    CreateBinaryFile(path, content + "\n");
    return path;
}

// Storage for temporary in out dir
class TempDirPair {
public:
    explicit TempDirPair(const std::string &case_name);
    TempDirPair(const TempDirPair &) = delete;
    TempDirPair(TempDirPair &&) = delete;
    TempDirPair &operator=(const TempDirPair &) = delete;
    TempDirPair &operator=(TempDirPair &&) = delete;

    ~TempDirPair();
    [[nodiscard]] std::filesystem::path in() const noexcept { return in_; }
    [[nodiscard]] std::filesystem::path out() const noexcept { return out_; }

private:
    std::filesystem::path path_;
    std::filesystem::path in_;
    std::filesystem::path out_;
};

inline std::tuple<std::filesystem::path, std::filesystem::path> CreateInOut() {
    if (std::filesystem::path temp_dir = cma::cfg::GetTempDir();
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos) {
        std::error_code ec;
        auto lwa_dir = temp_dir / "in";
        auto pd_dir = temp_dir / "out";
        std::filesystem::create_directories(lwa_dir, ec);
        std::filesystem::create_directories(pd_dir, ec);
        return {lwa_dir, pd_dir};
    }
    return {};
}

inline std::filesystem::path CreateDirInTemp(std::wstring_view Dir) {
    if (std::filesystem::path temp_dir = cma::cfg::GetTempDir();
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos) {
        std::error_code ec;
        auto lwa_dir = temp_dir / Dir;
        std::filesystem::create_directories(lwa_dir, ec);
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
    fs::path bakery_dir = cma::cfg::GetBakeryDir();
    if (bakery_dir.wstring().find(L"\\bakery", 0) != std::wstring::npos) {
        // clean
        fs::remove_all(bakery_dir);
        fs::create_directory(bakery_dir);
    } else {
        XLOG::l("attempt to delete suspicious dir {}", bakery_dir);
    }
}

std::vector<std::string> ReadFileAsTable(const std::string &name);
inline std::vector<std::string> ReadFileAsTable(
    const std::filesystem::path &name) {
    return ReadFileAsTable(wtools::ToUtf8(name.wstring()));
}

using CheckYamlVector =
    std::vector<std::pair<std::string_view, YAML::NodeType::value>>;
inline void CheckYaml(const YAML::Node &table, const CheckYamlVector &vec) {
    int pos = 0;
    for (auto t : table) {
        EXPECT_EQ(t.first.as<std::string>(), vec[pos].first);
        EXPECT_EQ(t.second.Type(), vec[pos].second);
        ++pos;
    }
}

constexpr std::string_view install_cab_to_test = "install_test.cab";
constexpr std::string_view cab_to_test = "uncab_test.cab";

/// \b creates temporary folder in temp and delete it on destruction
class TempFolder {
public:
    explicit TempFolder(std::string_view folder_name)
        : TempFolder(wtools::ConvertToUtf16(folder_name)) {}
    explicit TempFolder(std::wstring_view folder_name);
    TempFolder(const TempFolder &) = delete;
    TempFolder &operator=(const TempFolder &) = delete;
    TempFolder(TempFolder &&) = delete;
    TempFolder &operator=(TempFolder &&) = delete;
    ~TempFolder();

    [[nodiscard]] std::filesystem::path path() const { return folder_name_; }

private:
    std::filesystem::path folder_name_;
};

std::filesystem::path MakeTempFolderInTempPath(std::wstring_view folder_name);
std::wstring GenerateRandomFileName() noexcept;

/// RAII class to change folder structure in the config
class TempCfgFs {
public:
    using ptr = std::unique_ptr<TempCfgFs>;

    static TempCfgFs::ptr CreateNoIo() {
        return TempCfgFs::ptr(new TempCfgFs(Mode::no_io));
    }

    static TempCfgFs::ptr Create() {
        return TempCfgFs::ptr(new TempCfgFs(Mode::standard));
    }
    ~TempCfgFs();

    TempCfgFs(const TempCfgFs &) = delete;
    TempCfgFs(TempCfgFs &&) = delete;
    TempCfgFs &operator=(const TempCfgFs &) = delete;
    TempCfgFs &operator=(TempCfgFs &&) = delete;

    [[nodiscard]] bool loadConfig(const std::filesystem::path &yml);
    [[nodiscard]] bool reloadConfig() const;
    [[nodiscard]] bool loadFactoryConfig();
    [[nodiscard]] bool loadContent(std::string_view content);

    [[nodiscard]] bool createRootFile(const std::filesystem::path &filepath,
                                      const std::string &content) const;
    [[nodiscard]] bool createDataFile(const std::filesystem::path &filepath,
                                      const std::string &content) const;

    void removeRootFile(const std::filesystem::path &filepath) const;
    void removeDataFile(const std::filesystem::path &filepath) const;

    std::filesystem::path root() const { return root_; }
    std::filesystem::path data() const { return data_; }

    void allowUserAccess() const;

private:
    enum class Mode { standard, no_io };
    explicit TempCfgFs(Mode mode);
    [[nodiscard]] static bool createFile(
        const std::filesystem::path &filepath,
        const std::filesystem::path &filepath_base, const std::string &content);
    static void removeFile(const std::filesystem::path &filepath,
                           const std::filesystem::path &filepath_base);
    std::filesystem::path root_;
    std::filesystem::path data_;
    std::filesystem::path base_;
    Mode mode_;
    YAML::Node old_yaml_config_;
    bool content_loaded_{false};
};

std::filesystem::path GetFabricYml();
std::string GetFabricYmlContent();

bool WaitForSuccessSilent(std::chrono::milliseconds ms,
                          const std::function<bool()> &predicat);

bool WaitForSuccessIndicate(std::chrono::milliseconds ms,
                            const std::function<bool()> &predicat);

/// Usage:
///     FirewallOpener fwo
class FirewallOpener {
public:
    FirewallOpener();
    ~FirewallOpener();

    FirewallOpener(const FirewallOpener &) = delete;
    FirewallOpener(FirewallOpener &&) = delete;

    FirewallOpener &operator=(const FirewallOpener &) = delete;
    FirewallOpener &operator=(FirewallOpener &&) = delete;

private:
    std::wstring argv0_;
};

inline uint16_t TestPort() noexcept {
    static uint32_t r =
        static_cast<uint32_t>(::GetCurrentProcessId()) / 4U % 0xFFU + 22000;
    return static_cast<uint16_t>(r);
}

namespace misc {
void CopyFailedPythonLogFileToLog(const std::filesystem::path &data);

}  // namespace misc

struct EventRecordData {
    uint16_t event_id;
    uint16_t event_qualifiers;
    time_t time_generated;
    std::wstring source;
    std::wstring message;
    cma::evl::EventLogRecordBase::Level event_level;
};

const std::vector<EventRecordData> &SimpleLogData();

constexpr std::array g_terminal_services_indexes = {
    8154,  // windows 10, dev machine
    2066,  // windows server, build machine
    5090,  // windows 10, dev machine, late build
    6324,  // windows 10, 20h2
    8868,  // windows server build machine
};

}  // namespace tst

namespace cma::evl {
class EventLogRecordDebug final : public EventLogRecordBase {
public:
    EventLogRecordDebug(uint64_t record_id, const tst::EventRecordData &data)
        : record_id_{record_id}
        , event_id_{data.event_id}
        , event_qualifiers_{data.event_qualifiers}
        , time_generated_{data.time_generated}
        , source_(data.source)
        , message_(data.message)
        , event_level_{data.event_level} {}

    [[nodiscard]] uint64_t recordId() const override { return record_id_; }

    [[nodiscard]] uint16_t eventId() const override { return event_id_; }

    [[nodiscard]] uint16_t eventQualifiers() const override {
        return event_qualifiers_;
    }

    [[nodiscard]] time_t timeGenerated() const override {
        return time_generated_;
    }

    [[nodiscard]] std::wstring source() const override { return source_; }

    [[nodiscard]] Level eventLevel() const override { return event_level_; }

    [[nodiscard]] std::wstring makeMessage() const override { return message_; }

private:
    uint64_t record_id_;
    uint16_t event_id_;
    uint16_t event_qualifiers_;
    time_t time_generated_;
    std::wstring source_;
    std::wstring message_;
    Level event_level_;
};

class EventLogDebug final : public EventLogBase {
public:
    explicit EventLogDebug(const std::vector<tst::EventRecordData> &data)
        : data_(data) {}

    [[nodiscard]] std::wstring getName() const override { return L"debug"; }
    void seek(uint64_t record_id) override { pos_ = record_id; }
    EventLogRecordBase *readRecord() override {
        if (pos_ < data_.size()) {
            const auto &d = data_[static_cast<size_t>(pos_)];
            return new EventLogRecordDebug(pos_++, d);
        }
        return nullptr;
    }
    uint64_t getLastRecordId() override { return 0; }
    [[nodiscard]] bool isLogValid() const override { return true; }

private:
    uint64_t pos_{0U};
    std::vector<tst::EventRecordData> data_;
};

}  // namespace cma::evl

#endif  // TEST_TOOLS_H
