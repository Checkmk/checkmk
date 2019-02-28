#include "stdafx.h"

#include "logger.h"

namespace XLOG {

XLOG::Emitter l(XLOG::LogType::kLog);
XLOG::Emitter d(XLOG::LogType::kDebug);
XLOG::Emitter t(XLOG::LogType::kTrace);
XLOG::Emitter stdio(XLOG::LogType::kStdio);

XLOG::Emitter bp(XLOG::LogType::kLog, true);

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
        enable(LogType::kLog);
        enable(LogType::kDebug);
        // enable(LogType::kTrace);
        enable(LogType::kStdio);
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

    GlobalLogSettings(const GlobalLogSettings&) = delete;
    GlobalLogSettings& operator=(const GlobalLogSettings&) = delete;

private:
    constexpr static auto last_ = static_cast<int>(LogType::kLast);
    mutable std::mutex lock_;
    Info arr_[last_];
};

XLOG::details::GlobalLogSettings
    G_GlobalLogSettings;  // this is temporary solution to enable disable all
}  // namespace details

// check that parameters allow to print
static bool CalcEnabled(int Modifications, XLOG::LogType Type) {
    if (Modifications & Mods::kDrop) return false;  // output is dropped

    if (!(Modifications & Mods::kForce) &&  // output not forced
        !XLOG::details::G_GlobalLogSettings.isEnabled(
            Type))  // output is too low
        return false;
    return true;
}

// convertor from low level log type
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
static auto CalcLogParam(const xlog::LogParam& Param, int Modifications) {
    auto& lp = Param;
    auto directions = lp.directions_;
    auto flags = lp.flags_;
    using namespace fmt::v5;
    xlog::internal::Colors c = xlog::internal::Colors::kColorDefault;

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
            c = xlog::internal::Colors::kColorRed;
            break;

        case Mods::kError:
            marker = "[Err  ] ";
            c = xlog::internal::Colors::kColorRed;
            break;

        case Mods::kWarning:
            marker = "[Warn ] ";
            c = xlog::internal::Colors::kColorYellow;
            break;

        case Mods::kTrace:
            marker = "[Trace] ";
            break;
        case Mods::kInfo:
        default:
            // nothing here, empty.
            c = xlog::internal::Colors::kColorGreen;
            break;
    }

    return std::make_tuple(directions, flags, prefix, marker, c);
}

// output string in different directions
void Emitter::postProcessAndPrint(const std::string& String) {
    using namespace xlog;
    if (!CalcEnabled(mods_, type_)) return;

    auto lp = getLogParam();
    auto [directions, flags, prefix_ascii, marker_ascii, c] =
        CalcLogParam(lp, mods_);

    // EVENT
    if (setup::IsEventLogEnabled() && (directions & xlog::kEventPrint)) {
        // we do not need to format string for the event
        details::LogWindowsEventCritical(XLOG::EventClass::kDefault,
                                         String.c_str());
    }

    // USUAL
    auto normal = formatString(flags, (prefix_ascii + marker_ascii).c_str(),
                               String.c_str());
    if (XLOG::details::IsDuplicatedOnStdio())
        directions |= Directions::kStdioPrint;
    sendString(directions, normal.c_str(), c);

    // FILE
    if (directions & xlog::kFilePrint) {
        if (lp.filename() && lp.filename()[0]) {
            auto for_file =
                xlog::formatString(flags, marker_ascii.c_str(), String.c_str());
            xlog::internal_PrintStringFile(lp.filename(), for_file.c_str());
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
            XLOG::setup::EnableTraceLog(true);
            XLOG::setup::EnableDebugLog(true);
            break;
        case LogLevel::kLogDebug:
            XLOG::setup::EnableTraceLog(false);
            XLOG::setup::EnableDebugLog(true);
            break;
        case LogLevel::kLogBase:
        default:
            XLOG::setup::EnableTraceLog(false);
            XLOG::setup::EnableDebugLog(false);
            break;
    }
}

//
void ChangeLogFileName(const std::string& Filename) {
    l.configFile(Filename);
    d.configFile(Filename);
    t.configFile(Filename);
}

void ChangePrefix(const std::wstring& Prefix) {
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
