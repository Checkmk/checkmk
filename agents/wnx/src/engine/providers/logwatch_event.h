
// provides basic api to start and stop service

#pragma once
#ifndef logwatch_event_h__
#define logwatch_event_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "common/cfg_info.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {
const std::string kLogWatchEventStateFileName = "eventstate";
const std::string kLogWatchEventStateFileExt = ".txt";

// simple data structure to keep states internally
// name, value and new or not
struct State {
    State() : name_(""), pos_(0), presented_(false), in_config_(false) {
        setDefaults();
    }
    State(const std::string& Name, uint64_t Pos = 0, bool NewFound = true)
        : name_(Name), pos_(Pos), presented_(NewFound), in_config_(false) {
        setDefaults();
    }

    // #IMPORTANT default set of the level and context set MINIMAL
    void setDefaults() {
        level_ = cma::cfg::EventLevels::kCrit;  // #IMPORTANT
        hide_context_ = true;                   // #IMPORTANT
    }
    std::string name_;
    uint64_t pos_;
    bool presented_;  // either in registry or in config
    bool in_config_;  // config described

    cma::cfg::EventLevels level_ = cma::cfg::EventLevels::kAll;
    bool hide_context_ = false;
};

using StateVector = std::vector<State>;

// loaded normally from the yaml
struct LogWatchEntry {
public:
    LogWatchEntry()
        : loaded_(false)
        , context_(false)
        , level_(cma::cfg::EventLevels::kOff) {}

    LogWatchEntry(const LogWatchEntry& Rhs)
        : loaded_(Rhs.loaded_)
        , context_(Rhs.context_)
        , level_(Rhs.level_)
        , name_(Rhs.name_) {}

    LogWatchEntry& operator=(const LogWatchEntry& Rhs) {
        loaded_ = Rhs.loaded_;
        context_ = Rhs.context_;
        level_ = Rhs.level_;
        name_ = Rhs.name_;
    }

    LogWatchEntry(LogWatchEntry&& Rhs) = default;
    LogWatchEntry& operator=(LogWatchEntry&& Rhs) = default;
    ~LogWatchEntry() = default;

    // bool loadFrom(const YAML::Node Node) noexcept;
    bool loadFromMapNode(const YAML::Node Node) noexcept;
    bool loadFrom(std::string_view Line) noexcept;
    void init(std::string_view Name, std::string_view Param, bool Context);
    LogWatchEntry& withDefault() {
        init("*", ConvertLogWatchLevelToString(cfg::EventLevels::kWarn), true);
        return *this;
    }

    const std::string name() const noexcept {
        if (loaded_) return name_;
        return {};
    }
    const bool context() const noexcept { return context_; }
    const bool loaded() const noexcept { return loaded_; }
    const cma::cfg::EventLevels level() const noexcept { return level_; }

private:
    std::string name_;
    cma::cfg::EventLevels level_;
    bool context_;
    bool loaded_;
};

using LogWatchEntryVector = std::vector<LogWatchEntry>;

class LogWatchEvent : public Asynchronous {
public:
    LogWatchEvent()
        : Asynchronous(cma::section::kLogWatchEventName)
        , vista_api_(false)
        , send_all_(false)
        , default_entry_(0)

    {}

    LogWatchEvent(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator), vista_api_(true), send_all_(true) {}

    virtual void loadConfig();

    auto entries() const { return entries_; }
    const LogWatchEntry* defaultEntry() const {
        if (default_entry_ < entries().size()) return &entries_[default_entry_];
        XLOG::l.crit("This can't happen index is {} size is {} ",
                     default_entry_, entries().size());
        return nullptr;
    };
    std::vector<std::filesystem::path> makeStateFilesTable() const;

    bool sendAll() const { return send_all_; }

protected:
    std::string makeBody() override;

private:
    LogWatchEntryVector entries_;
    size_t default_entry_;
    bool send_all_;
    bool vista_api_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class LogWatchEventTest;
    FRIEND_TEST(LogWatchEventTest, Base);
    FRIEND_TEST(LogWatchEventTest, TestDefaultEntry);
#endif
};

// ***********************************************************************
// Internal API
// ***********************************************************************
// Read from registry registered sources and add them to the states vector
std::vector<std::string> GatherEventLogEntriesFromRegistry();
enum class SendMode { all, normal };

// Update States vector with log entries and Send All flags
// event logs are available
// returns count of processed Logs entries
int UpdateEventLogStates(StateVector& states, std::vector<std::string> logs,
                         SendMode send_mode);

LogWatchEntry GenerateDefaultValue();

// Fix Values in states according to the config
void UpdateStatesByConfig(StateVector& States,
                          const LogWatchEntryVector& Entries,
                          const LogWatchEntry* Default);
// manual adding: two things possible
// 1. added brand new
// 2. existing marked as presented_
void AddLogState(StateVector& states, bool from_config,
                 const std::string& log_name, SendMode send_mode);

// to use for load entries of config
void AddConfigEntry(StateVector& States, const LogWatchEntry&,
                    bool ResetToNull);

// returns output from log and set value validity
std::string ReadDataFromLog(bool VistaApi, State& St, bool& LogExists);

// used to check presence of some logs in registry
bool IsEventLogInRegistry(const std::string Name);

cma::cfg::EventLevels LabelToEventLevel(std::string_view LevelValue);

// used for a testing /analyzing
struct RawLogWatchData {
    bool loaded_;
    std::string_view name_;
    cma::cfg::EventLevels level_;
    bool context_;
};

}  // namespace provider

};  // namespace cma

#endif  // logwatch_event_h__
