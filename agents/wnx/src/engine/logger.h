// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// simple logging
// see logger.cpp to understand how it works

#pragma once
#include <fmt/format.h>

#include <algorithm>
#include <mutex>
#include <string>
#include <string_view>
#include <strstream>

#include "common/cfg_info.h"
#include "common/fmt_ext.h"
#include "common/wtools.h"
#include "fmt/color.h"
#include "tools/_xlog.h"

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

unsigned short LoggerEventLevelToWindowsEventType(EventLevel level);

void WriteToWindowsEventLog(unsigned short type, int code,
                            std::string_view log_name, std::string_view text);

// main engine to write something in the Windows Event Log
template <typename... Args>
void LogWindowsEventAlways(EventLevel Level, int Code, const char *Format,
                           Args &&...args) {
    auto type = LoggerEventLevelToWindowsEventType(Level);
    std::string x;
    try {
        x = fmt::format(Format, args...);
    } catch (...) {
        x = Format;
    }

    WriteToWindowsEventLog(type, Code, cma::cfg::kDefaultEventLogName, x);
}

template <typename... Args>
void LogWindowsEvent(EventLevel Level, int Code, const char *Format,
                     Args &&...args) {
    auto allowed_level = cma::cfg::GetCurrentEventLevel();
    if (Level > allowed_level) {
        return;
    }

    LogWindowsEventAlways(Level, Code, Format, std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventCritical(int Code, const char *Format, Args &&...args) {
    LogWindowsEvent(EventLevel::critical, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventError(int Code, const char *Format, Args &&...args) {
    LogWindowsEvent(EventLevel::error, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventSuccess(int Code, const char *Format, Args &&...args) {
    LogWindowsEvent(EventLevel::success, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventWarn(int Code, const char *Format, Args &&...args) {
    LogWindowsEvent(EventLevel::warning, Code, Format,
                    std::forward<Args>(args)...);
}

template <typename... Args>
void LogWindowsEventInfo(int Code, const char *Format, Args &&...args) {
    LogWindowsEvent(EventLevel::information, Code, Format,
                    std::forward<Args>(args)...);
}

};  // namespace XLOG::details
#endif

#if defined(FMT_FORMAT_H_)
namespace xlog {

inline void AddCr(std::string &s) noexcept {
    if (s.empty() || s.back() != '\n') {
        s.push_back('\n');
    }
}

inline void RmCr(std::string &s) noexcept {
    if (!s.empty() && s.back() == '\n') {
        s.pop_back();
    }
}

inline bool IsNoCrFlag(int Flag) noexcept { return (Flag & kNoCr) != 0; }
inline bool IsAddCrFlag(int Flag) noexcept { return (Flag & kAddCr) != 0; }

// Public Engine to print all
inline std::string formatString(int Fl, const char *Prefix,
                                const char *String) {
    std::string s;
    auto length = String != nullptr ? strlen(String) : 0;
    const auto *prefix = (Fl & Flags::kNoPrefix) != 0 ? nullptr : Prefix;
    length += prefix != nullptr ? strlen(prefix) : 0;
    length++;

    try {
        s.reserve(length);
        if (prefix != nullptr) {
            s = prefix;
        }
        if (String != nullptr) {
            s += String;
        }
    } catch (const std::exception &) {
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

constexpr uint16_t GetColorAttribute(Colors color) {
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

constexpr int GetBitOffset(uint16_t color_mask) {
    if (color_mask == 0) {
        return 0;
    }

    int bit_offset = 0;
    while ((color_mask & 1) == 0) {
        color_mask >>= 1;
        ++bit_offset;
    }
    return bit_offset;
}

constexpr uint16_t CalculateColor(Colors color, uint16_t OldColorAttributes) {
    // Let's reuse the BG
    constexpr uint16_t background_mask = BACKGROUND_BLUE | BACKGROUND_GREEN |
                                         BACKGROUND_RED | BACKGROUND_INTENSITY;
    constexpr uint16_t foreground_mask = FOREGROUND_BLUE | FOREGROUND_GREEN |
                                         FOREGROUND_RED | FOREGROUND_INTENSITY;
    uint16_t existing_bg = OldColorAttributes & background_mask;

    uint16_t new_color =
        GetColorAttribute(color) | existing_bg | FOREGROUND_INTENSITY;
    constexpr const int bg_bit_offset = GetBitOffset(background_mask);
    constexpr const int fg_bit_offset = GetBitOffset(foreground_mask);

    if (((new_color & background_mask) >> bg_bit_offset) ==
        ((new_color & foreground_mask) >> fg_bit_offset)) {
        new_color ^= FOREGROUND_INTENSITY;  // invert intensity
    }
    return new_color;
}
}  // namespace internal

inline void sendStringToDebugger(const char *String) {
    internal_PrintStringDebugger(String);
}

inline void sendStringToStdio(const char *str, internal::Colors color) {
    if (!XLOG::details::IsColoredOnStdio()) {
        internal_PrintStringStdio(str);
        return;
    }

    const HANDLE stdout_handle = GetStdHandle(STD_OUTPUT_HANDLE);

    // Gets the current text color.
    CONSOLE_SCREEN_BUFFER_INFO buffer_info;
    GetConsoleScreenBufferInfo(stdout_handle, &buffer_info);
    const uint16_t old_color_attrs = buffer_info.wAttributes;
    const uint16_t new_color = internal::CalculateColor(color, old_color_attrs);

    // We need to flush the stream buffers into the console before each
    // SetConsoleTextAttribute call lest it affect the text that is
    // already printed but has not yet reached the console.
    fflush(stdout);
    SetConsoleTextAttribute(stdout_handle, new_color);

    internal_PrintStringStdio(str);

    fflush(stdout);
    // Restores the text color.
    SetConsoleTextAttribute(stdout_handle, old_color_attrs);
}

inline void sendStringToStdio(const char *str) {
    return sendStringToStdio(str, internal::Colors::dflt);
}

}  // namespace xlog
#endif

namespace XLOG {
constexpr unsigned int min_file_count = 0;
constexpr unsigned int max_file_count = 64;
constexpr size_t min_file_size = 256 * 1024;
constexpr size_t max_file_size = 256 * 1024 * 1024;

namespace setup {
void DuplicateOnStdio(bool on);
void ColoredOutputOnStdio(bool On);
void SetContext(std::string_view context);

}  // namespace setup

using Colors = xlog::internal::Colors;

inline void SendStringToStdio(std::string_view string, Colors color) {
    return xlog::sendStringToStdio(string.data(), color);
}

inline void SendStringToStdio(std::string_view string) {
    return xlog::sendStringToStdio(string.data());
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

    explicit Emitter(XLOG::LogType t) : Emitter(t, false) {}

    Emitter(XLOG::LogType t, bool breakpoint)
        : type_(t), copy_(false), mods_(Mods::kCopy) {
        // setting up parameters for print in log_param_
        switch (t) {
            case LogType::log:
                log_param_.type_ = xlog::Type::kLogOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint |
                                         xlog::Directions::kFilePrint;
                break;
            case LogType::trace:
                log_param_.type_ = xlog::Type::kVerboseOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint;
                break;
            case LogType::debug:
                log_param_.type_ = xlog::Type::kDebugOut;
                log_param_.directions_ = xlog::Directions::kDebuggerPrint;
                break;
            case LogType::stdio:
                log_param_.type_ = xlog::Type::kVerboseOut;
                log_param_.mark_ = xlog::Marker::kTraceMark;
                log_param_.directions_ = xlog::Directions::kStdioPrint;
                log_param_.flags_ =
                    xlog::Flags::kAddCr | xlog::Flags::kNoPrefix;

                log_param_.setFileName(nullptr);
                log_param_.initPrefix(nullptr);
                break;
            default:
                log_param_.type_ = xlog::Type::kDebugOut;
        }
        if (breakpoint) {
            mods_ |= Mods::kBp;
        }
        constructed_ = kConstructedValue;
    }

    Emitter operator=(const Emitter &Rhs) = delete;

    ~Emitter() {
        if (copy_) {
            flush();
        }
    }

    // *****************************
    // STREAM OUTPUT
    template <typename T>
    std::ostream &operator<<(const T &value) {
        return (os_ << value);
    }

    template <>
    std::ostream &operator<<(const std::wstring &value) {
        auto s = wtools::ToUtf8(value);
        if (!constructed()) {
            xlog::l("Attempt to log too early '%s'", s.c_str());
            return os_;
        }

        std::lock_guard lk(lock_);
        return (os_ << s);
    }

    std::ostream &operator<<(const wchar_t *value) {
        auto s = wtools::ToUtf8(value);
        if (!constructed()) {
            xlog::l("Attempt to log too early '%s'", s.c_str());
            return os_;
        }
        std::lock_guard lk(lock_);
        return (os_ << s);
    }
    // **********************************

    static inline std::string SafePrintToDebuggerAndEventLog(
        const std::string &text) noexcept {
        try {
            return fmt::format(
                "[ERROR] [CRITICAL] Invalid parameters for log string \"{}\"\n",
                text);
        } catch (...) {
            xlog::internal_PrintStringDebugger(
                "[ERROR] [CRITICAL] Failed Print\n");
        }
        return "";
    }

    // **********************************
    // STREAM OUTPUT
    template <typename... Args>
    auto operator()(const std::string &format, Args &&...args) noexcept {
        try {
            auto s = fmt::format(format, std::forward<Args>(args)...);
            if (!constructed()) {
                xlog::l("Attempt to log too early '%s'", s.c_str());
                return s;
            }

            std::lock_guard lk(lock_);
            postProcessAndPrint(s);
            return s;
        } catch (...) {
            return SafePrintToDebuggerAndEventLog(format);
        }
    }

    // #TODO make more versatile
    template <typename... Args>
    auto operator()(int flags, const std::string &format,
                    Args &&...args) noexcept {
        try {
            auto s = fmt::format(format, std::forward<Args>(args)...);
            if (!constructed()) {
                xlog::l("Attempt to log too early '%s'", s.c_str());
                return s;
            }

            auto e = (*this).operator()(flags);
            std::lock_guard lk(lock_);
            e.postProcessAndPrint(s);
            return s;
        } catch (...) {
            return SafePrintToDebuggerAndEventLog(format);
        }
    }
    // **********************************

    static void bp() {
        if (bp_allowed_) {
            xdbg::bp();
        }
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

    template <typename... Args>
    auto exec(int modifications, const std::string &format,
              Args &&...args) noexcept {
        try {
            auto s = fmt::format(format, std::forward<Args>(args)...);
            // check construction
            if (!this->constructed_) {
                return s;
            }
            auto e = *this;
            e.mods_ |= modifications;
            e.postProcessAndPrint(s);
            return s;
        } catch (...) {
            return SafePrintToDebuggerAndEventLog(format);
        }
    }

#pragma warning(push)
#pragma warning(disable : 26444)
    // [Trace]
    template <typename... Args>
    [[maybe_unused]] auto t(const std::string &format,
                            Args &&...args) noexcept {
        return exec(XLOG::kTrace, format, std::forward<Args>(args)...);
    }

    // no prefix, just informational
    template <typename... Args>
    [[maybe_unused]] auto i(const std::string &format,
                            Args &&...args) noexcept {
        return exec(XLOG::kInfo, format, std::forward<Args>(args)...);
    }

    template <typename... Args>
    [[maybe_unused]] auto i(int Mods, const std::string &format,
                            Args &&...args) noexcept {
        return exec(XLOG::kInfo | Mods, format, std::forward<Args>(args)...);
    }

    // [Err  ]
    template <typename... Args>
    [[maybe_unused]] auto e(const std::string &format,
                            Args &&...args) noexcept {
        return exec(XLOG::kError, format, std::forward<Args>(args)...);
    }

    // [Warn ]
    template <typename... Args>
    [[maybe_unused]] auto w(const std::string &format,
                            Args &&...args) noexcept {
        return exec(XLOG::kWarning, format, std::forward<Args>(args)...);
    }

    template <typename... Args>
    [[maybe_unused]] auto crit(const std::string &format,
                               Args &&...args) noexcept {
        return exec(XLOG::kCritError, format, std::forward<Args>(args)...);
    }
    // [ERROR:CRITICAL] +  breakpoint
    template <typename... Args>
    [[maybe_unused]] auto bp(const std::string &format,
                             Args &&...args) noexcept {
        return exec(XLOG::kCritError | XLOG::kBp, format,
                    std::forward<Args>(args)...);
    }

    // this if for stream operations
    [[maybe_unused]] XLOG::Emitter operator()(int Flags) const noexcept {
        auto e = *this;
        e.mods_ = Flags;

        return e;
    }

    [[maybe_unused]] XLOG::Emitter operator()() const noexcept {
        return operator()(kCopy);
    }

    [[maybe_unused]] Emitter t() noexcept {
        auto e = *this;
        e.mods_ = XLOG::kTrace;
        return e;
    }

    [[maybe_unused]] Emitter w() noexcept {
        auto e = *this;
        e.mods_ = XLOG::kWarning;
        return e;
    }

    [[maybe_unused]] Emitter i() noexcept {
        auto e = *this;
        e.mods_ = XLOG::kInfo;
        return e;
    }

    [[maybe_unused]] Emitter e() noexcept {
        auto e = *this;
        e.mods_ = XLOG::kError;
        return e;
    }

    [[maybe_unused]] Emitter crit() noexcept {
        auto e = *this;
        e.mods_ = XLOG::kCritError;
        return e;
    }
#pragma warning(pop)
    // set filename to log
    void configFile(const std::string &log_file) {
        if (log_file.empty()) {
            log_param_.setFileName(nullptr);
        } else {
            log_param_.setFileName(log_file.c_str());
        }
    }

    void configPrefix(const std::wstring &prefix) {
        if (prefix.empty()) {
            log_param_.initPrefix(nullptr);
        } else {
            log_param_.initPrefix(prefix.c_str());
        }
    }

    void setLogRotation(unsigned int count, size_t size) {
        backup_log_max_count_ =
            std::clamp(count, min_file_count, max_file_count);
        backup_log_max_size_ = std::clamp(size, min_file_size, max_file_size);
    }

    void enableFileLog(bool enable) {
        if (enable) {
            log_param_.directions_ |= xlog::Directions::kFilePrint;
        } else {
            log_param_.directions_ &= ~xlog::Directions::kFilePrint;
        }
    }

    void enableEventLog(bool enable) {
        if (type_ == LogType::log) {
            // only kLog has right to create event log entries
            if (enable) {
                log_param_.directions_ |= xlog::Directions::kEventPrint;
            } else {
                log_param_.directions_ &= ~xlog::Directions::kEventPrint;
            }
        }
    }

    void enableWinDbg(bool enable) {
        if (enable) {
            log_param_.directions_ |= xlog::Directions::kDebuggerPrint;
        } else {
            log_param_.directions_ &= ~xlog::Directions::kDebuggerPrint;
        }
    }

    bool isWinDbg() const {
        return (log_param_.directions_ | xlog::Directions::kDebuggerPrint) != 0;
    }

    bool isFileDbg() const {
        return (log_param_.directions_ | xlog::Directions::kFilePrint) != 0;
    }

    const xlog::LogParam &getLogParam() const noexcept { return log_param_; }

    bool constructed() const noexcept {
        return constructed_ == kConstructedValue;
    }

    int getBackupLogMaxCount() const noexcept { return backup_log_max_count_; }

    size_t getBackupLogMaxSize() const noexcept { return backup_log_max_size_; }

private:
    uint32_t constructed_;  // filled during construction
    // private, can be called only from operator ()
    Emitter(const Emitter &rhs) {
        {
            std::lock_guard lk(rhs.lock_);
            log_param_ = rhs.log_param_;
            type_ = rhs.type_;
            mods_ = rhs.mods_;
            constructed_ = rhs.constructed_;
        }
        copy_ = true;
    }

    // this if for stream operations
    // called from destructor
    void flush() {
        std::lock_guard lk(lock_);
        if (!os_.str().empty()) {
            postProcessAndPrint(os_.str());
            os_.clear();
        }
    }

    void postProcessAndPrint(const std::string &text);

    mutable std::mutex lock_;
    xlog::LogParam log_param_;  // this is fixed base
    std::atomic<unsigned int> backup_log_max_count_{cma::cfg::kLogFileMaxCount};
    std::atomic<size_t> backup_log_max_size_{cma::cfg::kLogFileMaxSize};
    std::ostringstream os_;  // stream storage
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

// #TODO fix this make one entry point(Global Object)
namespace setup {

// YOU DO NOT NEED ANYTHING EXCEPT THIS CALL
void ReConfigure();

void Configure(const std::string &log_file_name, int debug_level, bool windbg,
               bool event_log);

/// \brief switch d to send output into the file
void EnableDebugLog(bool enable);

/// \brief switch t to send output into the file
void EnableTraceLog(bool enable);

/// \brief change file name for all loggers
void ChangeLogFileName(const std::string &log_file_name);

/// \brief change debug level
void ChangeDebugLogLevel(int level);

/// \brief disable enable windbg for all loggers
void EnableWinDbg(bool enable);

/// \brief reports log status
bool IsEventLogEnabled();

}  // namespace setup

namespace internal {
int Type2Marker(xlog::Type log_type) noexcept;
uint32_t Mods2Directions(const xlog::LogParam &lp, uint32_t mods) noexcept;
}  // namespace internal

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
    explicit TimeLog(const std::string &object_name);
    // duration is measured here
    void writeLog(size_t processed_bytes) const noexcept;

private:
    std::chrono::time_point<std::chrono::steady_clock> start_;
    const std::string id_;
};

}  // namespace cma::tools
