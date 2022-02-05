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
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogstd.h"
#include "eventlog/eventlogvista.h"
#include "iosfwd"                // for ofstream
#include "on_start.h"            // for OnStart, AppType, AppType::test
#include "system_error"          // for error_code
#include "xstring"               // for string, basic_string, wstring
#include "yaml-cpp/node/impl.h"  // for Node::Node, Node::~Node
namespace YAML {
class Node;
}

namespace tst {
std::filesystem::path GetSolutionRoot();
std::filesystem::path GetProjectRoot();
std::filesystem::path GetUnitTestFilesRoot();

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

inline void CreateTextFile(const std::filesystem::path &path,
                           std::string_view content) {
    std::ofstream ofs(path);

    ofs << content;
}

inline void CreateBinaryFile(const std::filesystem::path &path,
                             std::string_view data) {
    std::ofstream ofs(path, std::ios::binary);

    ofs.write(data.data(), data.size());
}

inline std::filesystem::path CreateIniFile(
    const std::filesystem::path &lwa_path, const std::string content,
    const std::string yaml_name) {
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
    TempDirPair(const std::string &case_name);
    TempDirPair(const TempDirPair &) = delete;
    TempDirPair(TempDirPair &&) = delete;
    TempDirPair &operator=(const TempDirPair &) = delete;
    TempDirPair &operator=(TempDirPair &&) = delete;

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

std::vector<std::string> ReadFileAsTable(const std::string &Name);
inline std::vector<std::string> ReadFileAsTable(
    const std::filesystem::path &name) {
    return ReadFileAsTable(name.u8string());
}

using CheckYamlVector =
    std::vector<std::pair<std::string_view, YAML::NodeType::value>>;
inline void CheckYaml(YAML::Node table, const CheckYamlVector &vec) {
    int pos = 0;
    for (auto t : table) {
        EXPECT_EQ(t.first.as<std::string>(), vec[pos].first);
        EXPECT_EQ(t.second.Type(), vec[pos].second);
        ++pos;
    }
}

constexpr std::string_view install_cab_to_test = "install_test.cab";
constexpr std::string_view cab_to_test = "uncab_test.cab";

/// \b creates temporary folder in temp and delete it on desctruction
class TempFolder {
public:
    explicit TempFolder(std::string_view folder_name)
        : TempFolder(wtools::ConvertToUTF16(folder_name)) {}
    explicit TempFolder(std::wstring_view folder_name);
    TempFolder(const TempFolder &) = delete;
    TempFolder &operator=(const TempFolder &) = delete;
    ~TempFolder();

    std::filesystem::path path() const { return folder_name_; }

private:
    std::filesystem::path folder_name_;
};

std::filesystem::path MakeTempFolderInTempPath(std::wstring_view folder_name);
std::wstring GenerateRandomFileName() noexcept;

/// \brief RAII class to change folder structure in the config
class TempCfgFs {
private:
    enum class Mode { standard, no_io };

public:
    using ptr = std::unique_ptr<TempCfgFs>;

    static std::unique_ptr<TempCfgFs> CreateNoIo() {
        return std::unique_ptr<TempCfgFs>(new TempCfgFs(Mode::no_io));
    }

    static std::unique_ptr<TempCfgFs> Create() {
        return std::unique_ptr<TempCfgFs>(new TempCfgFs(Mode::standard));
    }
    ~TempCfgFs();

    TempCfgFs(const TempCfgFs &) = delete;
    TempCfgFs(TempCfgFs &&) = delete;
    TempCfgFs &operator=(const TempCfgFs &) = delete;
    TempCfgFs &operator=(TempCfgFs &&) = delete;

    [[nodiscard]] bool loadConfig(const std::filesystem::path &yml);
    [[nodiscard]] bool reloadConfig();
    [[nodiscard]] bool loadFactoryConfig();
    [[nodiscard]] bool loadContent(std::string_view config);

    [[nodiscard]] bool createRootFile(const std::filesystem::path &relative_p,
                                      const std::string &content) const;
    [[nodiscard]] bool createDataFile(const std::filesystem::path &relative_p,
                                      const std::string &content) const;

    void removeRootFile(const std::filesystem::path &relative_p) const;
    void removeDataFile(const std::filesystem::path &relative_p) const;

    const std::filesystem::path root() const { return root_; }
    const std::filesystem::path data() const { return data_; }

    void allowUserAccess();

private:
    TempCfgFs(Mode mode);
    [[nodiscard]] static bool createFile(
        const std::filesystem::path &filepath,
        const std::filesystem::path &filepath_base, const std::string &content);
    static void removeFile(const std::filesystem::path &filepath,
                           const std::filesystem::path &filepath_base);
    std::filesystem::path root_;
    std::filesystem::path data_;
    std::filesystem::path base_;
    Mode mode_;
    YAML::Node yaml_;
};

std::filesystem::path GetFabricYml();
std::string GetFabricYmlContent();

bool WaitForSuccessSilent(std::chrono::milliseconds ms,
                          std::function<bool()> predicat);

bool WaitForSuccessIndicate(std::chrono::milliseconds ms,
                            std::function<bool()> predicat);

// Usage FirewallOpener fwo;
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

constexpr inline int TestPort() { return 64531; }

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
}  // namespace tst

namespace cma::evl {
class EventLogRecordDebug : public EventLogRecordBase {
public:
    EventLogRecordDebug(uint64_t record_id, const tst::EventRecordData &data)
        : record_id_{record_id}
        , event_id_{data.event_id}
        , event_qualifiers_{data.event_qualifiers}
        , time_generated_{data.time_generated}
        , source_(data.source)
        , message_(data.message)
        , event_level_{data.event_level} {}

    virtual uint64_t recordId() const override { return record_id_; }

    uint16_t eventId() const override { return event_id_; }

    uint16_t eventQualifiers() const override { return event_qualifiers_; }

    time_t timeGenerated() const override { return time_generated_; }

    std::wstring source() const override { return source_; }

    Level eventLevel() const override { return event_level_; }

    std::wstring makeMessage() const override { return message_; }

private:
    uint64_t record_id_;
    uint16_t event_id_;
    uint16_t event_qualifiers_;
    time_t time_generated_;
    std::wstring source_;
    std::wstring message_;
    Level event_level_;
};

class EventLogDebug : public EventLogBase {
public:
    EventLogDebug(const std::vector<tst::EventRecordData> &data)
        : data_(data) {}
    ~EventLogDebug() {}

    std::wstring getName() const override { return L"debug"; }
    void seek(uint64_t record_id) override { pos_ = record_id; }
    EventLogRecordBase *readRecord() override {
        if (pos_ < data_.size()) {
            const auto &d = data_[static_cast<size_t>(pos_)];
            return new EventLogRecordDebug(pos_++, d);
        }
        return nullptr;
    }
    uint64_t getLastRecordId() override { return 0; }
    bool isLogValid() const override { return true; }

private:
    uint64_t pos_{0U};
    std::vector<tst::EventRecordData> data_;
    bool seek_possible_{true};
};

}  // namespace cma::evl

#endif  // test_tools_h__
