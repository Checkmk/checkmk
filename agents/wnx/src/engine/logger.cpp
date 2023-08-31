#include "stdafx.h"

#include "wnx/logger.h"

#include "common/cfg_info.h"
#include "wnx/cma_core.h"
namespace fs = std::filesystem;

namespace XLOG {

Emitter l(LogType::log);         // NOLINT
Emitter d(LogType::debug);       // NOLINT
Emitter t(LogType::trace);       // NOLINT
Emitter stdio(LogType::stdio);   // NOLINT
Emitter bp(LogType::log, true);  // NOLINT

namespace details {
static bool g_event_log_enabled = true;

std::string g_log_context;

void WriteToWindowsEventLog(unsigned short type, int code,
                            std::string_view log_name,
                            std::string_view text) noexcept {
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

unsigned short LoggerEventLevelToWindowsEventType(EventLevel level) noexcept {
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
    }
    // unreachable
    return EVENTLOG_ERROR_TYPE;
}

static std::atomic g_log_duplicated_on_stdio = false;
static std::atomic g_log_colored_on_stdio = false;
static DWORD g_log_old_mode = static_cast<DWORD>(-1);

bool IsDuplicatedOnStdio() noexcept {
    return details::g_log_duplicated_on_stdio;
}
bool IsColoredOnStdio() noexcept { return details::g_log_colored_on_stdio; }

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
        if (cur_type >= 0 && cur_type <= last_) {
            arr_[cur_type].enabled_ = true;
        }
    }

    void disable(LogType log_type) {
        const auto cur_type = static_cast<int>(log_type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) {
            arr_[cur_type].enabled_ = false;
        }
    }

    bool isEnabled(LogType log_type) const {
        const auto cur_type = static_cast<int>(log_type);
        std::lock_guard lk(lock_);
        if (cur_type >= 0 && cur_type <= last_) {
            return arr_[cur_type].enabled_;
        }

        return false;
    }

    GlobalLogSettings(const GlobalLogSettings &) = delete;
    GlobalLogSettings &operator=(const GlobalLogSettings &) = delete;

private:
    constexpr static auto last_ = static_cast<int>(LogType::stdio);
    mutable std::mutex lock_;
    Info arr_[last_];
};

details::GlobalLogSettings G_GlobalLogSettings;
}  // namespace details

// check that parameters allow to print
static bool CalcEnabled(int modifications, LogType log_type) {
    return (modifications & Mods::kDrop) == 0 ||
           (modifications & Mods::kForce) != 0 ||
           details::G_GlobalLogSettings.isEnabled(log_type);
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
            return XLOG::kInfo;
    }
    // unreachable
    return XLOG::kInfo;
}

// converter from low level log type
// to some default mark
uint32_t Mods2Directions(const xlog::LogParam &lp, uint32_t mods) noexcept {
    auto directions = lp.directions_;

    if ((mods & Mods::kStdio) != 0) {
        directions |= xlog::Directions::kStdioPrint;
    }
    if ((mods & Mods::kNoStdio) != 0) {
        directions &= ~xlog::Directions::kStdioPrint;
    }
    if ((mods & Mods::kFile) != 0) {
        directions |= xlog::Directions::kFilePrint;
    }
    if ((mods & Mods::kNoFile) != 0) {
        directions &= ~xlog::Directions::kFilePrint;
    }
    if ((mods & Mods::kEvent) != 0) {
        directions |= xlog::Directions::kEventPrint;
    }
    if ((mods & Mods::kNoEvent) != 0) {
        directions &= ~xlog::Directions::kEventPrint;
    }

    return directions;
}
}  // namespace internal

// get base global variable
// modifies it!
static std::tuple<int, int, std::string, std::string, xlog::internal::Colors>
CalcLogParam(const xlog::LogParam &lp, int mods) noexcept {
    auto c = Colors::dflt;

    auto directions = internal::Mods2Directions(lp, mods);

    auto flags = lp.flags_;
    if ((mods & Mods::kNoPrefix) != 0) {
        flags |= xlog::Flags::kNoPrefix;
    }

    std::string prefix = lp.prefixAscii();
    std::string marker = details::g_log_context;

    auto mark = mods & Mods::kMarkerMask;

    if (mark == 0) {
        mark = internal::Type2Marker(lp.type_);  // using default when nothing
    }

    switch (mark) {
        case Mods::kCritError:
            marker += "[ERROR:CRITICAL] ";
            flags &= ~xlog::Flags::kNoPrefix;
            directions |= xlog::Directions::kEventPrint;
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
    if (index == 0) {
        return std::string{filename};
    }
    try {
        return std::string{filename} + "." + std::to_string(index);
    } catch (const std::bad_alloc & /*e*/) {
        return {};
    }
}

namespace {
void UpdateLogFiles(std::string_view filename, size_t max_size,
                    unsigned int max_backup_count, std::string_view text) {
    fs::path log_file(filename);

    std::error_code ec;
    auto size = fs::file_size(log_file, ec);
    if (ec) {
        size = 0;
    }

    if (size + text.size() + g_file_text_header_size > max_size) {
        for (auto i = factory_max_file_count; i > max_backup_count; --i) {
            fs::remove(MakeBackupLogName(filename, i), ec);
        }
        // making chain of backups
        for (auto i = max_backup_count; i > 0; --i) {
            auto old_file = MakeBackupLogName(filename, i - 1);
            auto new_file = MakeBackupLogName(filename, i);
            fs::rename(old_file, new_file, ec);
        }

        // clean main file(may be required)
        fs::remove(filename, ec);
    }
}
}  // namespace

void WriteToLogFileWithBackup(std::string_view filename, size_t max_size,
                              unsigned int max_backup_count,
                              std::string_view text) {
    max_backup_count = std::clamp(max_backup_count, factory_min_file_count,
                                  factory_max_file_count);
    max_size = std::min(max_size, factory_max_file_size);
    std::lock_guard lk(g_backup_lock_mutex);
    UpdateLogFiles(filename, max_size, max_backup_count, text);

    xlog::internal_PrintStringFile(filename, text);
}
}  // namespace details

XLOG::Emitter Emitter::copyAndModify(ModData data) const noexcept {
    auto e = *this;
    switch (data.type) {
        case ModData::ModType::assign:
            e.mods_ = data.mods;
            break;
        case ModData::ModType::modify:
            e.mods_ |= data.mods;
            break;
    }
    return e;
}

std::string Emitter::sendToLogModding(std::optional<ModData> data,
                                      std::string_view format,
                                      fmt::format_args args) const noexcept {
    try {
        auto s = fmt::vformat(format, args);
        if (!this->constructed_) {
            return s;
        }
        if (data.has_value()) {
            copyAndModify(*data).postProcessAndPrint(s);
        } else {
            postProcessAndPrint(s);
        }
        return s;
    } catch (const std::exception & /*e*/) {
        return SafePrintToDebuggerAndEventLog(std::string{format});
    }
}

// output string in different directions
void Emitter::postProcessAndPrint(const std::string &text) const {
    if (!CalcEnabled(mods_, type_)) {
        return;
    }

    auto lp = getLogParam();
    auto [dirs, flags, prefix_ascii, marker_ascii, c] = CalcLogParam(lp, mods_);

    // EVENT
    if (setup::IsEventLogEnabled() &&
        (dirs & xlog::Directions::kEventPrint) != 0) {
        // we do not need to format string for the event
        const auto windows_event_log_id = cma::GetModus() == cma::Modus::service
                                              ? EventClass::kSrvDefault
                                              : EventClass::kAppDefault;
        details::LogWindowsEventCritical(windows_event_log_id, text.c_str());
    }

    // USUAL
    if ((dirs & xlog::Directions::kDebuggerPrint) != 0) {
        const auto normal =
            xlog::formatString(flags, prefix_ascii + marker_ascii, text);
        xlog::sendStringToDebugger(normal.c_str());
    }

    const auto file_print = (dirs & xlog::Directions::kFilePrint) != 0;
    const auto stdio_print = (dirs & xlog::Directions::kStdioPrint) != 0;

    if (stdio_print || file_print && details::IsDuplicatedOnStdio()) {
        const auto normal = xlog::formatString(flags, "", text);
        xlog::sendStringToStdio(normal.c_str(), c);
    }

    // FILE
    if (file_print && !lp.filename().empty()) {
        auto for_file = xlog::formatString(flags, marker_ascii, text);

        details::WriteToLogFileWithBackup(lp.filename(), getBackupLogMaxSize(),
                                          getBackupLogMaxCount(), for_file);
    }

    // BREAK POINT
    if ((mods_ & Mods::kBp) != 0 && bp_allowed_) {
        xdbg::bp();
    }
}

namespace setup {
void DuplicateOnStdio(bool on) noexcept {
    details::g_log_duplicated_on_stdio = on;
}
void ColoredOutputOnStdio(bool on) noexcept {
    if (details::g_log_colored_on_stdio.exchange(on) == on) {
        return;
    }

    auto *std_input = ::GetStdHandle(STD_INPUT_HANDLE);
    if (on) {
        ::GetConsoleMode(std_input, &details::g_log_old_mode);

        constexpr DWORD old_mode =
            ENABLE_PROCESSED_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING;
        ::SetConsoleMode(std_input, old_mode);
    } else if (details::g_log_old_mode != static_cast<DWORD>(-1)) {
        ::SetConsoleMode(std_input, details::g_log_old_mode);
    }
}

void SetContext(std::string_view context) noexcept {
    if (context.empty()) {
        details::g_log_context.clear();
    } else {
        details::g_log_context =
            fmt::format("[{} {}] ", context, ::GetCurrentProcessId());
    }
}

void EnableDebugLog(bool enable) noexcept { d.enableFileLog(enable); }

void EnableTraceLog(bool enable) noexcept { t.enableFileLog(enable); }

void SetLogRotation(unsigned int max_count, size_t max_size) {
    l.setLogRotation(max_count, max_size);
    d.setLogRotation(max_count, max_size);
    t.setLogRotation(max_count, max_size);
}

void ChangeDebugLogLevel(int debug_level) noexcept {
    switch (debug_level) {
        case static_cast<int>(cma::cfg::LogLevel::kLogAll):
            setup::EnableTraceLog(true);
            setup::EnableDebugLog(true);
            XLOG::t("Enabled All");
            break;
        case static_cast<int>(cma::cfg::LogLevel::kLogDebug):
            setup::EnableTraceLog(false);
            setup::EnableDebugLog(true);
            XLOG::d.t("Enabled Debug");
            break;
        default:
            setup::EnableTraceLog(false);
            setup::EnableDebugLog(false);
            XLOG::l.t("Enabled Base");
            break;
    }
}

//
void ChangeLogFileName(const std::string &log_file_name) noexcept {
    l.configFile(log_file_name);
    d.configFile(log_file_name);
    t.configFile(log_file_name);
}

void ChangePrefix(const std::wstring &prefix) noexcept {
    l.configPrefix(prefix);
    d.configPrefix(prefix);
    t.configPrefix(prefix);
}

// #TODO I don't like the idea and look'n'feel
// for this case
void EnableWinDbg(bool enable) noexcept {
    l.enableWinDbg(enable);
    d.enableWinDbg(enable);
    t.enableWinDbg(enable);
}

bool IsEventLogEnabled() noexcept { return details::g_event_log_enabled; }

void EnableEventLog(bool enable) noexcept {
    details::g_event_log_enabled = enable;
}

// all parameters are set in config
void Configure(const std::string &log_file_name, int debug_level, bool windbg,
               bool event_log) {
    ChangeLogFileName(log_file_name);
    ChangeDebugLogLevel(debug_level);
    EnableWinDbg(windbg);
    EnableEventLog(event_log);
    ChangePrefix(cma::cfg::GetDefaultPrefixName());
}

void ReConfigure() {
    const auto log_file_name = cma::cfg::GetCurrentLogFileName();
    const auto level = cma::cfg::GetCurrentDebugLevel();
    const auto windbg = cma::cfg::GetCurrentWinDbg();
    const auto event_log = cma::cfg::GetCurrentEventLog();

    Configure(log_file_name, level, windbg, event_log);
}

}  // namespace setup

}  // namespace XLOG

namespace cma::tools {

TimeLog::TimeLog(const std::string &object_name)
    : start_{std::chrono::steady_clock::now()}, id_{object_name} {}

void TimeLog::writeLog(size_t processed_bytes) const noexcept {
    const auto ended = std::chrono::steady_clock::now();
    const auto lost = duration_cast<std::chrono::milliseconds>(ended - start_);

    if (processed_bytes == 0) {
        XLOG::d.w("Object '{}' in {}ms sends NO DATA", id_, lost.count());
    } else {
        XLOG::d.i("Object '{}' in {}ms sends [{}] bytes", id_, lost.count(),
                  processed_bytes);
    }
}

}  // namespace cma::tools
