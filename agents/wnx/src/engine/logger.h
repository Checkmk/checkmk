
// simple logging
// see logger.cpp to understand how it works

#pragma once
#include <mutex>
#include <string>
#include <string_view>
#include <strstream>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "fmt/color.h"
#include "fmt/format.h"
#include "tools/_xlog.h"

// User defined converter required to logging correctly data from wstring
template <>
struct fmt::formatter<std::wstring> {
    template <typename ParseContext>
    constexpr auto parse(ParseContext& ctx) {
        return ctx.begin();
    }

    template <typename FormatContext>
    auto format(const std::wstring& Ws, FormatContext& ctx) {
        return format_to(ctx.out(), "{}", wtools::ConvertToUTF8(Ws));
    }
};

// #TODO put it into internal/details
// support for windows event log
// implementation according to MSDN
// Windows doesn't support critical, so we have only limited possibilities to
// choose from: error, warning, info
#if defined(WIN32) && defined(FMT_FORMAT_H_)
namespace XLOG::details {
// SIMPLE LOG SUPPORT TO WINDOWS EVENT LOG
#if 0
    // example how to use
    XLOG::LogWindowsEventError(1, "Service Starting {}", "error!");
    XLOG::LogWindowsEventWarn(2, "My Warning {}", "warning!");
    XLOG::LogWindowsEventInfo(3, "My Information {}", "info!");
#endif

// converts "filename", 0 into "filename" and "filename", N into "filename.N"
std::string MakeBackupLogName(std::string_view filename,
                              unsigned int index) noexcept;

// internal engine to print text in file with optional backing up
// thread safe(no race condition)
void WriteToLogFileWithBackup(std::string_view filename, size_t max_size,
                              unsigned int max_backup_count,
                              std::string_view text) noexcept;

// check status of duplication
bool IsDuplicatedOnStdio();
bool IsColoredOnStdio();
template <typename... Args>
void LogWindowsEvent(EventLevel Level, int Code, const char* Format,
                     Args&&... args) {
    auto allowed_level = cma::cfg::GetCurrentEventLevel();
    if (Level > allowed_level) return;

    auto eventSource =
        RegisterEventSourceA(nullptr, cma::cfg::kDefaultEventLogName);
    if (eventSource) {
        unsigned short type = EVENTLOG_ERROR_TYPE;
        switch (Level) {
            case EventLevel::success:
                type = EVENTLOG_SUCCESS;
                break;
            case EventLevel::information:
                type = EVENTLOG_INFORMATION_TYPE;
                break;
            case EventLevel::warning:
                type = EVENTLOG_WARNING_TYPE;
                break;
            case EventLevel::error:
            case EventLevel::critical:
                type = EVENTLOG_ERROR_TYPE;
                break;
            default:
                type = EVENTLOG_INFORMATION_TYPE;
                break;
        }
        std::string x;
        try {
            x = fmt::format(Format, args...);
        } catch (...) {
            x = Format;
        }
        const char* strings[2] = {cma::cfg::kDefaultEventLogName, x.c_str()};
        ReportEventA(eventSource,  // Event log handle
                     type,         // Event type
                     0,            // Event category
                     Code,         // Event identifier
                     nullptr,      // No security identifier
                     2,            // Size of lpszStrings array
                     0,            // No binary data
                     strings,      // Array of strings
                     nullptr);     // No binary data
        DeregisterEventSource(eventSource);
    }
}

template <typename... Args>
void LogWindowsEventCritical(int Code, const char* Format, Args&&... args) {
    LogWindowsEvent(EventLevel::critical, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventError(int Code, const char* Format, Args&&... args) {
    LogWindowsEvent(EventLevel::error, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventSuccess(int Code, const char* Format, Args&&... args) {
    LogWindowsEvent(EventLevel::success, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventWarn(int Code, const char* Format, Args&&... args) {
    LogWindowsEvent(EventLevel::warning, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventInfo(int Code, const char* Format, Args&&... args) {
    LogWindowsEvent(EventLevel::information, Code, Format,
                    std::forward<Args>(args)...);
}

};  // namespace XLOG::details
#endif

#if defined(FMT_FORMAT_H_)
namespace xlog {

inline void AddCr(std::string& s) noexcept {
    if (s.empty() || s.back() != '\n') s.push_back('\n');
}

inline void RmCr(std::string& s) noexcept {
    if (!s.empty() && s.back() == '\n') s.pop_back();
}

inline bool IsNoCrFlag(int Flag) noexcept { return (Flag & kNoCr) != 0; }
inline bool IsAddCrFlag(int Flag) noexcept { return (Flag & kAddCr) != 0; }

// Public Engine to print all
inline std::string formatString(int Fl, const char* Prefix,
                                const char* String) {
    std::string s;
    auto length = String != nullptr ? strlen(String) : 0;
    auto prefix = Fl & Flags::kNoPrefix ? nullptr : Prefix;
    length += prefix != nullptr ? strlen(prefix) : 0;
    length++;

    try {
        s.reserve(length);
        if (prefix != nullptr) s = prefix;
        s += String;
    } catch (const std::exception&) {
        return {};
    }

    if (IsNoCrFlag(Fl)) {
        RmCr(s);
    } else if (IsAddCrFlag(Fl)) {
        AddCr(s);
    }

    return s;
}

namespace internal {
enum class Colors { dflt, red, green, yellow, pink, cyan, pink_light, white };

static uint16_t GetColorAttribute(Colors color) {
    switch (color) {
        case Colors::red:
            return FOREGROUND_RED;
        case Colors::green:
            return FOREGROUND_GREEN;
        case Colors::yellow:
            return FOREGROUND_RED | FOREGROUND_GREEN;
        case Colors::pink:
            return FOREGROUND_RED | FOREGROUND_BLUE;
        case Colors::pink_light:
            return FOREGROUND_RED | FOREGROUND_BLUE | FOREGROUND_INTENSITY;
        case Colors::cyan:
            return FOREGROUND_GREEN | FOREGROUND_BLUE;
        case Colors::white:
            return FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE |
                   FOREGROUND_INTENSITY;
        default:
            return 0;
    }
}

static int GetBitOffset(uint16_t color_mask) {
    if (color_mask == 0) return 0;

    int bit_offset = 0;
    while ((color_mask & 1) == 0) {
        color_mask >>= 1;
        ++bit_offset;
    }
    return bit_offset;
}

static uint16_t CalculateColor(Colors color, uint16_t OldColorAttributes) {
    // Let's reuse the BG
    static const uint16_t background_mask = BACKGROUND_BLUE | BACKGROUND_GREEN |
                                            BACKGROUND_RED |
                                            BACKGROUND_INTENSITY;
    static const uint16_t foreground_mask = FOREGROUND_BLUE | FOREGROUND_GREEN |
                                            FOREGROUND_RED |
                                            FOREGROUND_INTENSITY;
    const uint16_t existing_bg = OldColorAttributes & background_mask;

    uint16_t new_color =
        GetColorAttribute(color) | existing_bg | FOREGROUND_INTENSITY;
    static const int bg_bit_offset = GetBitOffset(background_mask);
    static const int fg_bit_offset = GetBitOffset(foreground_mask);

    if (((new_color & background_mask) >> bg_bit_offset) ==
        ((new_color & foreground_mask) >> fg_bit_offset)) {
        new_color ^= FOREGROUND_INTENSITY;  // invert intensity
    }
    return new_color;
}
}  // namespace internal

inline void sendStringToDebugger(const char* String) {
    internal_PrintStringDebugger(String);
}

inline void sendStringToStdio(const char* String,
                              internal::Colors Color = internal::Colors::dflt) {
    if (!XLOG::details::IsColoredOnStdio()) {
        internal_PrintStringStdio(String);
        return;
    }

    const HANDLE stdout_handle = GetStdHandle(STD_OUTPUT_HANDLE);

    // Gets the current text color.
    CONSOLE_SCREEN_BUFFER_INFO buffer_info;
    GetConsoleScreenBufferInfo(stdout_handle, &buffer_info);
    const uint16_t old_color_attrs = buffer_info.wAttributes;
    const uint16_t new_color = internal::CalculateColor(Color, old_color_attrs);

    // We need to flush the stream buffers into the console before each
    // SetConsoleTextAttribute call lest it affect the text that is
    // already printed but has not yet reached the console.
    fflush(stdout);
    SetConsoleTextAttribute(stdout_handle, new_color);

    internal_PrintStringStdio(String);

    fflush(stdout);
    // Restores the text color.
    SetConsoleTextAttribute(stdout_handle, old_color_attrs);
}

}  // namespace xlog
#endif

namespace XLOG {

namespace setup {
void DuplicateOnStdio(bool On);
void ColoredOutputOnStdio(bool On);

}  // namespace setup

using Colors = xlog::internal::Colors;

inline void SendStringToStdio(std::string_view string,
                              Colors Color = Colors::dflt) {
    return xlog::sendStringToStdio(string.data(), Color);
}

enum Mods : int {
    kCopy = 0,           // no changes in param`
    kDrop = 1,           // no output at all
    kForce = 2,          // always generate output
    kStdio = 4,          // force output to stdio TOO
    kNoStdio = 8,        // no output to stdio too
    kEvent = 0x10,       // force output to event log
    kNoEvent = 0x20,     // forbid output to event log
    kFile = 0x40,        // forced output to file
    kNoFile = 0x80,      // disabled output to file
    kBp = 0x100,         // breakpoint
    kNoPrefix = 0x0200,  // drop prefix

    // Error Markers. Used to "sign" log messages with predefined
    // text strings to make searching more light

    // we are disabling automatic formatting because we have to
    // see binaries well
    // clang-format off
    kMarkerMask= 0x1C00,   // mask for error

    kCritError = 0x0400,   // disaster:   Always in event
    kError     = 0x0800,   // serious:    Default XLOG::l
    kWarning   = 0x0C00,   // suspicious: Default XLOG::d
    kTrace     = 0x1000,   // function:   Default XLOG::t
    kInfo      = 0x1400,   // detailed info about state
    kRsrv1     = 0x1800,   //
    kRsrv2     = 0x1c00,   //
                      // clang-format on

    kNext = 0x2000,

};

// This is de-facto name
enum class LogType {
    log = 0,  // this is logger for user
    debug,    // this is logger for developer
    trace,    // this is TEMPORARY logger for developer
    stdio,
    last = stdio
};

class Emitter {
public:
    enum { kConstructedValue = 0xFFA1B2C0 };

    Emitter(XLOG::LogType t,
            bool Breakpoint = false)  // future use
        : type_(t), copy_(false), mods_(Mods::kCopy) {
        // setting up parameters for print in log_param_
        switch (t) {
            case LogType::log:
                log_param_.type_ = xlog::Type::kLogOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint |
                                         xlog::Directions::kFilePrint;
                // other
                break;
            case LogType::trace:
                log_param_.type_ = xlog::Type::kVerboseOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint;
                // other
                break;
            case LogType::debug:
                log_param_.type_ = xlog::Type::kDebugOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint;
                // other
                break;
            case LogType::stdio: {
                log_param_.type_ = xlog::Type::kVerboseOut;
                log_param_.mark_ = xlog::Marker::kTraceMark;
                log_param_.directions_ = xlog::Directions::kStdioPrint;
                log_param_.flags_ =
                    xlog::Flags::kAddCr | xlog::Flags::kNoPrefix;

                log_param_.setFileName(nullptr);
                log_param_.initPrefix(nullptr);
            } break;
            default:
                log_param_.type_ = xlog::Type::kDebugOut;
        }
        if (Breakpoint) mods_ |= Mods::kBp;
        constructed_ = kConstructedValue;
    }

    Emitter operator=(const Emitter& Rhs) = delete;

    ~Emitter() {
        if (copy_) flush();
    }

    // *****************************
    // STREAM OUTPUT
    template <typename T>
    std::ostream& operator<<(const T& Value) {
        return (os_ << Value);
    }

    template <>
    std::ostream& operator<<(const std::wstring& Value) {
        auto s_wide = fmt::format(L"{}", Value);
        std::string s(s_wide.begin(), s_wide.end());
        if (!constructed()) {
            xlog::l("Attempt to log too early '%s'", s.c_str());
            return os_;
        }

        std::lock_guard lk(lock_);
        return (os_ << s);
    }

    std::ostream& operator<<(const wchar_t* Value) {
        auto s_wide = fmt::format(L"{}", Value);
        std::string s(s_wide.begin(), s_wide.end());
        if (!constructed()) {
            xlog::l("Attempt to log too early '%s'", s.c_str());
            return os_;
        }
        std::lock_guard lk(lock_);
        return (os_ << s);
    }
    // **********************************

    // **********************************
    // STREAM OUTPUT
    template <typename... T>
    auto operator()(const std::string& Format, T... args) {
        try {
            auto s = fmt::format(Format, args...);
            if (!constructed()) {
                xlog::l("Attempt to log too early '%s'", s.c_str());
                return s;
            }

            std::lock_guard lk(lock_);
            postProcessAndPrint(s);
            return s;
        } catch (...) {
            auto s =
                fmt::format("Invalid parameters for log string \"{}\"", Format);
            auto e = *this;
            e.mods_ = XLOG::kCritError;
            e.postProcessAndPrint(s);
            return s;
        }
    }

    // #TODO make more versatile
    template <typename... T>
    auto operator()(int Flags, const std::string& Format, T... args) {
        try {
            auto s = fmt::format(Format, args...);
            if (!constructed()) {
                xlog::l("Attempt to log too early '%s'", s.c_str());
                return s;
            }

            auto e = (*this).operator()(Flags);
            std::lock_guard lk(lock_);
            e.postProcessAndPrint(s);
            return s;
        } catch (...) {
            auto s =
                fmt::format("Invalid parameters for log string \"{}\"", Format);
            auto e = *this;
            e.mods_ = XLOG::kCritError;
            e.postProcessAndPrint(s);
            return s;
        }
    }
    // **********************************

    // this if for stream operations
    void bp() {
        if (bp_allowed_) {
            xdbg::bp();
        }
    }

    XLOG::Emitter operator()(int Flags = kCopy) {
        auto e = *this;
        e.mods_ = Flags;

        return e;
    }

    // Bunch of functions to provide special output
    // Main use case
    // write to log important data, which are not error
    // XLOG::l.i("We have finished. Count {}", count);
    // or
    // XLOG::l.i()<< "We have finished. Count " << count;

    // Write to Debug "interesting" result
    // XLOG::d.t(XLOG_FUNC + " this shit is not implemented. WHADDAHEL??");
    // or
    // XLOG::d.t() << XLOG_FUNC + " this shit is not implemented.
    // WHADDAHEL??";

    // those functions are SHORTCUTTING those calls:
    // XLOG::l(XLOG::kInfo)(...);
    // XLOG::d(XLOG::kTrace)(...);

    // #TODO please, Sergey, this is copy-paste and copy-paste is streng
    // verboten by Check MK
    template <typename... T>
    auto exec(int Modifications, const std::string& Format,
              T... args) noexcept {
        try {
            auto s = fmt::format(Format, args...);
            // check construction
            if (this == nullptr || !this->constructed_) return s;
            auto e = *this;
            e.mods_ |= Modifications;
            e.postProcessAndPrint(s);
            return s;
        } catch (...) {
            // we do not want any exceptions during logging
            auto s =
                fmt::format("Invalid parameters for log string \"{}\"", Format);
            if (this == nullptr || !this->constructed_) return s;
            auto e = *this;
            e.mods_ |= XLOG::kCritError;
            e.postProcessAndPrint(s);
            return s;
        }
    }

    // [Trace]
    template <typename... T>
    auto t(const std::string& Format, T... args) {
        return exec(XLOG::kTrace, Format, args...);
    }

    // no prefix, just informational
    template <typename... T>
    auto i(const std::string& Format, T... args) {
        return exec(XLOG::kInfo, Format, args...);
    }

    template <typename... T>
    auto i(int Mods, const std::string& Format, T... args) {
        return exec(XLOG::kInfo | Mods, Format, args...);
    }

    // [Err  ]
    template <typename... T>
    auto e(const std::string& Format, T... args) {
        return exec(XLOG::kError, Format, args...);
    }

    // [Warn ]
    template <typename... T>
    auto w(const std::string& Format, T... args) {
        return exec(XLOG::kWarning, Format, args...);
    }

    template <typename... T>
    auto crit(const std::string& Format, T... args) {
        return exec(XLOG::kCritError, Format, args...);
    }
    // [ERROR:CRITICAL] +  breakpoint
    template <typename... T>
    auto bp(const std::string& Format, T... args) {
        return exec(XLOG::kCritError | XLOG::kBp, Format, args...);
    }

    Emitter t() {
        auto e = *this;
        e.mods_ = XLOG::kTrace;
        return e;
    }

    Emitter w() {
        auto e = *this;
        e.mods_ = XLOG::kWarning;
        return e;
    }

    Emitter i() {
        auto e = *this;
        e.mods_ = XLOG::kInfo;
        return e;
    }

    Emitter e() {
        auto e = *this;
        e.mods_ = XLOG::kError;
        return e;
    }

    Emitter crit() {
        auto e = *this;
        e.mods_ = XLOG::kCritError;
        return e;
    }

    // set filename to log
    void configFile(const std::string& LogFile) {
        if (LogFile.empty()) {
            log_param_.setFileName(nullptr);
        } else {
            log_param_.setFileName(LogFile.c_str());
        }
    }

    void configPrefix(const std::wstring& Prefix) {
        if (Prefix.empty()) {
            log_param_.initPrefix(nullptr);
        } else {
            log_param_.initPrefix(Prefix.c_str());
        }
    }

    void enableFileLog(bool Enable) {
        if (Enable)
            log_param_.directions_ |= xlog::Directions::kFilePrint;
        else
            log_param_.directions_ &= ~xlog::Directions::kFilePrint;
    }

    void enableEventLog(bool Enable) {
        if (type_ == LogType::log) {
            // only kLog has right to create event log entries
            if (Enable)
                log_param_.directions_ |= xlog::Directions::kEventPrint;
            else
                log_param_.directions_ &= ~xlog::Directions::kEventPrint;
        }
    }

    void enableWinDbg(bool Enable) {
        if (Enable)
            log_param_.directions_ |= xlog::Directions::kDebuggerPrint;
        else
            log_param_.directions_ &= ~xlog::Directions::kDebuggerPrint;
    }

    const xlog::LogParam& getLogParam() const { return log_param_; }

    bool constructed() const { return constructed_ == kConstructedValue; }

private:
    uint32_t constructed_;  // filled during construction
    // private, can be called only from operator ()
    Emitter(const Emitter& Rhs) {
        {
            std::lock_guard lk(Rhs.lock_);
            log_param_ = Rhs.log_param_;
            type_ = Rhs.type_;
            mods_ = Rhs.mods_;
            constructed_ = Rhs.constructed_;
        }
        copy_ = true;
    }

    // this if for stream operations
    // called from destructor
    void flush() {
        std::lock_guard lk(lock_);
        if (!os_.str().empty()) {
            postProcessAndPrint(os_.str());
            os_.str() = "";
        }
    }

    void postProcessAndPrint(const std::string& String);

    mutable std::mutex lock_;
    xlog::LogParam log_param_;  // this is fixed base
    std::ostringstream os_;     // stream storage
    XLOG::LogType type_;

    bool copy_;  // informs us that whole structure is temporary
    int mods_;   // here we keep modifications to fixed base

    static bool bp_allowed_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class LogTest;
    FRIEND_TEST(LogTest, All);
#endif

};  // namespace XLOG

// Global Log Engines

extern XLOG::Emitter l;      // Standard log from Check MK
extern XLOG::Emitter d;      // this is GLOBAL
extern XLOG::Emitter t;      // temporary log!
extern XLOG::Emitter stdio;  // only print

// API:
//

// bad example of engineering.
// #TODO fix this make one entry point(Global Object)
namespace setup {

// YOU DO NOT NEED ANYTHING EXCEPT THIS CALL
void ReConfigure();

void Configure(std::string LogFileName, int DebugLevel, bool WinDbg,
               bool EventLog);

// switch d to send output into the file
void EnableDebugLog(bool Enable);

// switch t to send output into the file
void EnableTraceLog(bool Enable);

// change file name for all loggers
void ChangeLogFileName(const std::string& Filename);

// change file name for all loggers
void ChangeDebugLogLevel(int Level);

// disable enable windbg for all loggers
void EnableWinDbg(bool Enable);

// disable enable event log GLOBALLY
bool IsEventLogEnabled();

}  // namespace setup

}  // namespace XLOG

namespace cma::tools {
// simple class to log time of execution, to be moved in separate header
// will be extended with dtor(to dump) and other functions
// Usage:
// TimeLog tl(name);
// .......
// tl.writeLog(data_count);
class TimeLog {
public:
    // time is set at the moment of creation
    explicit TimeLog(const std::string& object_name);
    // duration is measured here
    void writeLog(size_t processed_bytes) const noexcept;

private:
    std::chrono::time_point<std::chrono::steady_clock> start_;
    const std::string id_;
};

}  // namespace cma::tools
