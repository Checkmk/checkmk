#include "stdafx.h"

#include "logger.h"

#include <filesystem>

#include "cfg.h"

namespace XLOG {

Emitter l(LogType::log);
Emitter d(LogType::debug);
Emitter t(LogType::trace);
Emitter stdio(LogType::stdio);

Emitter bp(LogType::log, true);

bool Emitter::bp_allowed_ = tgt::IsDebug();

namespace details {
static std::atomic<bool> LogDuplicatedOnStdio = false;
static std::atomic<bool> LogColoredOnStdio = false;
static DWORD LogOldMode = -1;

bool IsDuplicatedOnStdio() { return details::LogDuplicatedOnStdio; }
bool IsColoredOnStdio() { return details::LogColoredOnStdio; }
// keeps all configurable features
class GlobalLogSettings {
public:
    GlobalLogSettings() {
        enable(LogType::log);
        enable(LogType::debug);
        enable(LogType::trace);
        enable(LogType::stdio);
    }

    struct Info {
        bool enabled_;
    };

    void enable(LogType Type) {
        auto cur_type = static_cast<int>(Type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) arr_[cur_type].enabled_ = true;
    }

    void disable(LogType Type) {
        auto cur_type = static_cast<int>(Type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) arr_[cur_type].enabled_ = false;
    }

    const bool isEnabled(LogType Type) const {
        auto cur_type = static_cast<int>(Type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) return arr_[cur_type].enabled_;

        return false;
    }

    GlobalLogSettings(const GlobalLogSettings &) = delete;
    GlobalLogSettings &operator=(const GlobalLogSettings &) = delete;

private:
    constexpr static auto last_ = static_cast<int>(LogType::last);
    mutable std::mutex lock_;
    Info arr_[last_];
};

details::GlobalLogSettings
    G_GlobalLogSettings;  // this is temporary solution to enable disable all
}  // namespace details

// check that parameters allow to print
static bool CalcEnabled(int Modifications, LogType Type) {
    if (Modifications & Mods::kDrop) return false;  // output is dropped

    if (!(Modifications & Mods::kForce) &&              // output not forced
        !details::G_GlobalLogSettings.isEnabled(Type))  // output is too low
        return false;
    return true;
}

// converter from low level log type
// to some default mark
static int XLogType2Marker(xlog::Type Lt) {
    switch (Lt) {
        case xlog::Type::kLogOut:
            return XLOG::kError;
        case xlog::Type::kVerboseOut:
            return XLOG::kTrace;
        case xlog::Type::kDebugOut:
            return XLOG::kWarning;
        case xlog::Type::kOtherOut:
            return XLOG::kInfo;
        default:
            return XLOG::kInfo;
    }
}

// get base global variable
// modifies it!
static std::tuple<int, int, std::string, std::string, xlog::internal::Colors>
CalcLogParam(const xlog::LogParam &Param, int Modifications) {
    using namespace xlog::internal;

    auto &lp = Param;
    auto directions = lp.directions_;
    auto flags = lp.flags_;
    using namespace fmt::v5;
    auto c = Colors::dflt;

    if (Modifications & Mods::kStdio) directions |= xlog::kStdioPrint;
    if (Modifications & Mods::kNoStdio) directions &= ~xlog::kStdioPrint;
    if (Modifications & Mods::kFile) directions |= xlog::kFilePrint;
    if (Modifications & Mods::kNoFile) directions &= ~xlog::kFilePrint;
    if (Modifications & Mods::kEvent) directions |= xlog::kEventPrint;
    if (Modifications & Mods::kNoEvent) directions &= ~xlog::kEventPrint;
    if (Modifications & Mods::kNoPrefix) flags |= xlog::kNoPrefix;

    std::string prefix = lp.prefixAscii();
    std::string marker = "";

    auto mark = Modifications & Mods::kMarkerMask;

    if (mark == 0)
        mark = XLogType2Marker(lp.type_);  // using default when nothing

    switch (mark) {
        case Mods::kCritError:
            marker = "[ERROR:CRITICAL] ";
            flags &= ~xlog::kNoPrefix;
            directions |= xlog::kEventPrint;
            c = Colors::pink_light;
            break;

        case Mods::kError:
            marker = "[Err  ] ";
            c = Colors::red;
            break;

        case Mods::kWarning:
            marker = "[Warn ] ";
            c = Colors::yellow;
            break;

        case Mods::kTrace:
            marker = "[Trace] ";
            break;
        case Mods::kInfo:
        default:
            // nothing here, empty.
            c = xlog::internal::Colors::green;
            break;
    }

    return std::make_tuple(directions, flags, prefix, marker, c);
}

namespace details {
static std::mutex g_backup_lock_mutex;  // intentionally global
constexpr unsigned int file_text_header_size = 24;

std::string MakeBackupLogName(std::string_view filename,
                              unsigned int index) noexcept {
    std::string name;
    if (filename.data()) name += filename;

    if (index == 0) return name;
    return name + "." + std::to_string(index);
}

constexpr unsigned int kMaxAllowedBackupCount = 32;
constexpr size_t kMaxAllowedBackupSize = 1024 * 1024 * 256;

void WriteToLogFileWithBackup(std::string_view filename, size_t max_size,
                              unsigned int max_backup_count,
                              std::string_view text) noexcept {
    // sanity check
    if (max_backup_count > kMaxAllowedBackupCount)
        max_backup_count = kMaxAllowedBackupCount;

    if (max_size > kMaxAllowedBackupSize) max_size = kMaxAllowedBackupSize;

    namespace fs = std::filesystem;
    std::lock_guard lk(g_backup_lock_mutex);

    fs::path log_file(filename);

    std::error_code ec;
    auto size = fs::file_size(log_file, ec);
    if (ec.value() != 0) size = 0;

    if (size + text.size() + file_text_header_size > max_size) {
        // required backup

        // making chain of backups
        for (auto i = max_backup_count; i > 0; --i) {
            auto old_file = MakeBackupLogName(filename, i - 1);
            auto new_file = MakeBackupLogName(filename, i);
            fs::rename(old_file, new_file, ec);
        }

        // clean main file(may be required)
        fs::remove(filename, ec);
    }

    xlog::internal_PrintStringFile(filename.data(), text.data());
}
}  // namespace details

// output string in different directions
void Emitter::postProcessAndPrint(const std::string &text) {
    using namespace cma::cfg;
    using namespace xlog;
    if (!CalcEnabled(mods_, type_)) return;

    auto lp = getLogParam();
    auto [dirs, flags, prefix_ascii, marker_ascii, c] = CalcLogParam(lp, mods_);

    // EVENT
    if (setup::IsEventLogEnabled() && (dirs & xlog::kEventPrint)) {
        // we do not need to format string for the event
        auto windows_event_log_id = cma::IsService() ? EventClass::kSrvDefault
                                                     : EventClass::kAppDefault;
        details::LogWindowsEventCritical(windows_event_log_id, text.c_str());
    }

    // USUAL
    if (dirs & Directions::kDebuggerPrint) {
        auto normal = formatString(flags, (prefix_ascii + marker_ascii).c_str(),
                                   text.c_str());
        sendStringToDebugger(normal.c_str());
    }

    auto file_print = (dirs & Directions::kFilePrint) != 0 ? true : false;
    auto stdio_print = (dirs & Directions::kStdioPrint) != 0 ? true : false;

    if (stdio_print || (file_print && details::IsDuplicatedOnStdio())) {
        auto normal = formatString(flags, nullptr, text.c_str());
        sendStringToStdio(normal.c_str(), c);
    }

    // FILE
    if (file_print) {
        auto fname = lp.filename();
        if (fname && fname[0]) {
            auto for_file =
                formatString(flags, marker_ascii.c_str(), text.c_str());

            details::WriteToLogFileWithBackup(fname, GetBackupLogMaxSize(),
                                              GetBackupLogMaxCount(), for_file);
        }
    }

    // BREAK POINT
    if (mods_ & Mods::kBp && bp_allowed_) {
        xdbg::bp();
    }
}

namespace details {

// this is to store latest parameters which may be
// distributed among loggers later
// static std::string LogFileName = cma::cfg::GetCurrentLogFileName();
// static std::wstring LogPrefix = cma::cfg::GetDefaultPrefixName();
static bool DebugLogEnabled = false;
static bool TraceLogEnabled = false;
static bool WinDbgEnabled = true;
static bool EventLogEnabled = true;  // real global for all

}  // namespace details

namespace setup {
void DuplicateOnStdio(bool On) { details::LogDuplicatedOnStdio = On; }
void ColoredOutputOnStdio(bool On) {
    auto old = details::LogColoredOnStdio.exchange(On);

    if (old == On) return;

    auto hStdin = GetStdHandle(STD_INPUT_HANDLE);
    DWORD old_mode = 0;
    if (On) {
        GetConsoleMode(hStdin, &details::LogOldMode);  // store old mode

        //  set color output
        old_mode = 0;  // details::LogOldMode;
        old_mode |= ENABLE_PROCESSED_OUTPUT | ENABLE_PROCESSED_OUTPUT |
                    ENABLE_VIRTUAL_TERMINAL_PROCESSING;
        SetConsoleMode(hStdin, old_mode);
    } else {
        if (details::LogOldMode != -1)
            SetConsoleMode(hStdin, details::LogOldMode);
    }
}

void EnableDebugLog(bool Enable) {
    details::DebugLogEnabled = Enable;
    d.enableFileLog(Enable);
}

void EnableTraceLog(bool Enable) {
    details::TraceLogEnabled = Enable;
    t.enableFileLog(Enable);
}

void ChangeDebugLogLevel(int Level) {
    using namespace cma::cfg;
    switch (Level) {
        case LogLevel::kLogAll:
            setup::EnableTraceLog(true);
            setup::EnableDebugLog(true);
            XLOG::t("Enabled All");
            break;
        case LogLevel::kLogDebug:
            setup::EnableTraceLog(false);
            setup::EnableDebugLog(true);
            XLOG::d.t("Enabled Debug");
            break;
        case LogLevel::kLogBase:
        default:
            setup::EnableTraceLog(false);
            setup::EnableDebugLog(false);
            XLOG::l.t("Enabled Base");
            break;
    }
}

//
void ChangeLogFileName(const std::string &Filename) {
    l.configFile(Filename);
    d.configFile(Filename);
    t.configFile(Filename);
}

void ChangePrefix(const std::wstring &Prefix) {
    l.configPrefix(Prefix);
    d.configPrefix(Prefix);
    t.configPrefix(Prefix);
}

// #TODO I don't like the idea and look'n'feel
// for this case
void EnableWinDbg(bool Enable) {
    details::WinDbgEnabled = Enable;
    l.enableWinDbg(Enable);
    d.enableWinDbg(Enable);
    t.enableWinDbg(Enable);
}

bool IsEventLogEnabled() { return details::EventLogEnabled; }

void EnableEventLog(bool Enable) { details::EventLogEnabled = Enable; }

// all parameters are set in config
void Configure(std::string LogFileName, int DebugLevel, bool WinDbg,
               bool EventLog) {
    ChangeLogFileName(LogFileName);
    ChangeDebugLogLevel(DebugLevel);
    EnableWinDbg(WinDbg);
    ChangePrefix(cma::cfg::GetDefaultPrefixName());
}

// Standard API to reset to defaults
// Safe to use WITHOUT Config Loaded
void ReConfigure() {
    using namespace details;

    // this is to store latest parameters which may be
    // distributed among loggers later
    auto log_file_name = cma::cfg::GetCurrentLogFileName();
    auto LogPrefix = cma::cfg::GetDefaultPrefixName();
    auto level = cma::cfg::GetCurrentDebugLevel();
    auto windbg = cma::cfg::GetCurrentWinDbg();
    auto event_log = cma::cfg::GetCurrentEventLog();

    Configure(log_file_name, level, windbg, event_log);
}

}  // namespace setup

}  // namespace XLOG

namespace cma::tools {
// time is set at the moment of creation
TimeLog::TimeLog(const std::string &object_name) : id_(object_name) {
    start_ = std::chrono::steady_clock::now();
}

void TimeLog::writeLog(size_t processed_bytes) const noexcept {
    using namespace std::chrono;
    auto ended = steady_clock::now();
    auto lost = duration_cast<milliseconds>(ended - start_);

    if (processed_bytes == 0)
        XLOG::d.w("Object '{}' in {}ms sends NO DATA", id_, lost.count());
    else
        XLOG::d.i("Object '{}' in {}ms sends [{}] bytes", id_, lost.count(),
                  processed_bytes);
}

}  // namespace cma::tools
