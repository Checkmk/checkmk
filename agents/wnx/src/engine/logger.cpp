#include "stdafx.h"

#include "logger.h"

#include "cfg.h"
#include "cma_core.h"
#include "common/cfg_info.h"

namespace XLOG {

Emitter l(LogType::log);
Emitter d(LogType::debug);
Emitter t(LogType::trace);
Emitter stdio(LogType::stdio);

Emitter bp(LogType::log, true);

bool Emitter::bp_allowed_ = tgt::IsDebug();

namespace details {

// this is to store latest parameters which may be
// distributed among loggers later
// static std::string LogFileName = cma::cfg::GetCurrentLogFileName();
// static std::wstring LogPrefix = cma::cfg::GetDefaultPrefixName();
static bool DebugLogEnabled = false;
static bool TraceLogEnabled = false;
static bool WinDbgEnabled = true;
static bool EventLogEnabled = true;  // real global for all

std::string g_log_context;

void WriteToWindowsEventLog(unsigned short type, int code,
                            std::string_view log_name, std::string_view text) {
    auto *event_source =
        ::RegisterEventSourceA(nullptr, cma::cfg::kDefaultEventLogName);
    if (event_source == nullptr) {
        return;
    }

    const char *strings[2] = {log_name.data(), text.data()};
    ::ReportEventA(event_source,  // Event log handle
                   type,          // Event type
                   0,             // Event category
                   code,          // Event identifier
                   nullptr,       // No security identifier
                   2,             // Size of lpszStrings array
                   0,             // No binary data
                   strings,       // Array of strings
                   nullptr);      // No binary data
    ::DeregisterEventSource(event_source);
}

unsigned short LoggerEventLevelToWindowsEventType(EventLevel level) {
    switch (level) {
        case EventLevel::success:
            return EVENTLOG_SUCCESS;
        case EventLevel::information:
            return EVENTLOG_INFORMATION_TYPE;
        case EventLevel::warning:
            return EVENTLOG_WARNING_TYPE;
        case EventLevel::error:
        case EventLevel::critical:
            return EVENTLOG_ERROR_TYPE;
        default:
            return EVENTLOG_INFORMATION_TYPE;
    }
}

static std::atomic<bool> g_log_duplicated_on_stdio = false;
static std::atomic<bool> g_log_colored_on_stdio = false;
static DWORD g_log_old_mode = -1;

bool IsDuplicatedOnStdio() { return details::g_log_duplicated_on_stdio; }
bool IsColoredOnStdio() { return details::g_log_colored_on_stdio; }
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

    void enable(LogType log_type) {
        auto cur_type = static_cast<int>(log_type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) arr_[cur_type].enabled_ = true;
    }

    void disable(LogType log_type) {
        auto cur_type = static_cast<int>(log_type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) arr_[cur_type].enabled_ = false;
    }

    bool isEnabled(LogType log_type) const {
        auto cur_type = static_cast<int>(log_type);
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
static bool CalcEnabled(int modifications, LogType log_type) {
    if ((modifications & Mods::kDrop) != 0) return false;  // output is dropped

    if ((modifications & Mods::kForce) == 0 &&              // output not forced
        !details::G_GlobalLogSettings.isEnabled(log_type))  // output is too low
        return false;
    return true;
}

namespace internal {
// converter from low level log type
// to some default mark
int Type2Marker(xlog::Type log_type) noexcept {
    switch (log_type) {
        case xlog::Type::kLogOut:
            return XLOG::kError;
        case xlog::Type::kVerboseOut:
            return XLOG::kTrace;
        case xlog::Type::kDebugOut:
            return XLOG::kWarning;
        case xlog::Type::kOtherOut:
        default:  // stupid, but VS requires default here
            return XLOG::kInfo;
    }
}

// converter from low level log type
// to some default mark
uint32_t Mods2Directions(const xlog::LogParam &lp, uint32_t mods) noexcept {
    int directions = lp.directions_;

    if (mods & Mods::kStdio) directions |= xlog::kStdioPrint;
    if (mods & Mods::kNoStdio) directions &= ~xlog::kStdioPrint;
    if (mods & Mods::kFile) directions |= xlog::kFilePrint;
    if (mods & Mods::kNoFile) directions &= ~xlog::kFilePrint;
    if (mods & Mods::kEvent) directions |= xlog::kEventPrint;
    if (mods & Mods::kNoEvent) directions &= ~xlog::kEventPrint;

    return directions;
}
}  // namespace internal

// get base global variable
// modifies it!
static std::tuple<int, int, std::string, std::string, xlog::internal::Colors>
CalcLogParam(const xlog::LogParam &lp, int mods) noexcept {
    using namespace xlog::internal;

    auto c = Colors::dflt;

    auto directions = internal::Mods2Directions(lp, mods);

    auto flags = lp.flags_;
    if (mods & Mods::kNoPrefix) flags |= xlog::kNoPrefix;

    std::string prefix = lp.prefixAscii();
    std::string marker = details::g_log_context;

    auto mark = mods & Mods::kMarkerMask;

    if (mark == 0)
        mark = internal::Type2Marker(lp.type_);  // using default when nothing

    switch (mark) {
        case Mods::kCritError:
            marker += "[ERROR:CRITICAL] ";
            flags &= ~xlog::kNoPrefix;
            directions |= xlog::kEventPrint;
            c = Colors::pink_light;
            break;

        case Mods::kError:
            marker += "[Err  ] ";
            c = Colors::red;
            break;

        case Mods::kWarning:
            marker += "[Warn ] ";
            c = Colors::yellow;
            break;

        case Mods::kTrace:
            marker += "[Trace] ";
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
constexpr unsigned int g_file_text_header_size = 24;

std::string MakeBackupLogName(std::string_view filename,
                              unsigned int index) noexcept {
    std::string name;
    if (!filename.empty()) {
        name += filename;
    }

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

    if (size + text.size() + g_file_text_header_size > max_size) {
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

    xlog::internal_PrintStringFile(filename, text);
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
    if (setup::IsEventLogEnabled() && ((dirs & xlog::kEventPrint) != 0)) {
        // we do not need to format string for the event
        auto windows_event_log_id = cma::GetModus() == cma::Modus::service
                                        ? EventClass::kSrvDefault
                                        : EventClass::kAppDefault;
        details::LogWindowsEventCritical(windows_event_log_id, text.c_str());
    }

    // USUAL
    if ((dirs & Directions::kDebuggerPrint) != 0) {
        auto normal = formatString(flags, (prefix_ascii + marker_ascii).c_str(),
                                   text.c_str());
        sendStringToDebugger(normal.c_str());
    }

    auto file_print = (dirs & Directions::kFilePrint) != 0;
    auto stdio_print = (dirs & Directions::kStdioPrint) != 0;

    if (stdio_print || (file_print && details::IsDuplicatedOnStdio())) {
        auto normal = formatString(flags, nullptr, text.c_str());
        sendStringToStdio(normal.c_str(), c);
    }

    // FILE
    if (file_print) {
        auto *fname = lp.filename();
        if (fname && fname[0] != 0) {
            auto for_file =
                formatString(flags, marker_ascii.c_str(), text.c_str());

            details::WriteToLogFileWithBackup(fname, getBackupLogMaxSize(),
                                              getBackupLogMaxCount(), for_file);
        }
    }

    // BREAK POINT
    if ((mods_ & Mods::kBp) != 0 && bp_allowed_) {
        xdbg::bp();
    }
}

namespace setup {
void DuplicateOnStdio(bool on) { details::g_log_duplicated_on_stdio = on; }
void ColoredOutputOnStdio(bool on) {
    auto old = details::g_log_colored_on_stdio.exchange(on);

    if (old == on) return;

    auto *std_input = ::GetStdHandle(STD_INPUT_HANDLE);
    if (on) {
        ::GetConsoleMode(std_input,
                         &details::g_log_old_mode);  // store old mode

        //  set color output
        DWORD old_mode =
            ENABLE_PROCESSED_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING;
        SetConsoleMode(std_input, old_mode);
    } else {
        if (details::g_log_old_mode != -1)
            SetConsoleMode(std_input, details::g_log_old_mode);
    }
}

void SetContext(std::string_view context) {
    if (context.empty()) {
        details::g_log_context.clear();
    } else {
        details::g_log_context =
            fmt::format("[{} {}] ", context, ::GetCurrentProcessId());
    }
}

void EnableDebugLog(bool enable) {
    details::DebugLogEnabled = enable;
    d.enableFileLog(enable);
}

void EnableTraceLog(bool enable) {
    details::TraceLogEnabled = enable;
    t.enableFileLog(enable);
}

void ChangeDebugLogLevel(int debug_level) {
    using cma::cfg::LogLevel;
    switch (debug_level) {
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
void ChangeLogFileName(const std::string &log_file_name) {
    l.configFile(log_file_name);
    d.configFile(log_file_name);
    t.configFile(log_file_name);
}

void ChangePrefix(const std::wstring &prefix) {
    l.configPrefix(prefix);
    d.configPrefix(prefix);
    t.configPrefix(prefix);
}

// #TODO I don't like the idea and look'n'feel
// for this case
void EnableWinDbg(bool enable) {
    details::WinDbgEnabled = enable;
    l.enableWinDbg(enable);
    d.enableWinDbg(enable);
    t.enableWinDbg(enable);
}

bool IsEventLogEnabled() { return details::EventLogEnabled; }

void EnableEventLog(bool enable) { details::EventLogEnabled = enable; }

// all parameters are set in config
void Configure(const std::string &log_file_name, int debug_level, bool windbg,
               bool event_log) {
    ChangeLogFileName(log_file_name);
    ChangeDebugLogLevel(debug_level);
    EnableWinDbg(windbg);
    EnableEventLog(event_log);
    ChangePrefix(cma::cfg::GetDefaultPrefixName());
}

// Standard API to reset to defaults
// Safe to use WITHOUT Config Loaded
void ReConfigure() {
    // this is to store latest parameters which may be
    // distributed among loggers later
    auto log_file_name = cma::cfg::GetCurrentLogFileName();
    auto level = cma::cfg::GetCurrentDebugLevel();
    auto windbg = cma::cfg::GetCurrentWinDbg();
    auto event_log = cma::cfg::GetCurrentEventLog();

    Configure(log_file_name, level, windbg, event_log);
}

}  // namespace setup

}  // namespace XLOG

namespace cma::tools {

TimeLog::TimeLog(const std::string &object_name)
    : start_{std::chrono::steady_clock::now()}, id_{object_name} {}

void TimeLog::writeLog(size_t processed_bytes) const noexcept {
    auto ended = std::chrono::steady_clock::now();
    auto lost = duration_cast<std::chrono::milliseconds>(ended - start_);

    if (processed_bytes == 0)
        XLOG::d.w("Object '{}' in {}ms sends NO DATA", id_, lost.count());
    else
        XLOG::d.i("Object '{}' in {}ms sends [{}] bytes", id_, lost.count(),
                  processed_bytes);
}

}  // namespace cma::tools
