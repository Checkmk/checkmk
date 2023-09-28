// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Setup
/*
// defines which may be located in StdAfx.h or in project setup
#define XLOG_NO_LOG		// no logged messages in the binary even release
#define XLOG_VERBOSE	// hundreds less important messages
#define XLOG_FORCED_DUMP// all traces inside release also

Examples
Release
        DEFINED in source code            Left in Binaries
        XLOG_NO_LOG						= nothing!
        -default- or nothing			= xlog::l
        XLOG_FORCED_DUMP				= xlog::l + xlog::d
        XLOG_VERBOSE+XLOG_FORCED_DUMP	= xlog::l + xlog::d + xlog::v
Debug
        -default- or nothing			= xlog::l + xlog::d
        XLOG_VERBOSE					= xlog::l + xlog::d +
xlog::v

LINUX default is stdio
Windows default is debug print

*/

// Usage
#if (0)
#include "_xlog.h"

int somefoo() {
    xlog::d(L"Out %d\n", value);  // stripped from release
    xlog::l(L"Out %d\n", value);  // left in release

    xlog::l("Out").print().filelog("myfile").syslog("MySysLog", xlog::kError,
                                                    0xC00005);
}

// *RECOMMENDED* METHOD to use
xlog::AdvancedLog print_log( [](xlog::LogParam& Lg)	// <- this is boiler plate for logging variable print_log
{
    Lg.directions_ |=
        xlog::Directions::kStdioPrint;  // <-  this is parameter modification
                                        // code for your advanced log
    Lg.log_param_.flags_ =
        xlog::Flags::kNoPrefix;  // <-  this is parameter modification code for
                                 // your advanced log
}

void somefoo_want_stdio_trace()
{
    print_log.d("Something to print on stdio");
}

//*****************************************************
//Another useful methods  for optional dumping!
//1.
//......
bool enable_local = true;

void somefoo()
{
    xlog::d(enable_local, "Local print\n");
}

// 2.
//..........
extern bool G_TraceVideo;
//..........
void somefoo_about_video()
{
    xlog::d(G_TraceVideo, "This is a message from the video");
}
//..........
#endif

#pragma once
// Microsoft has defined those macros and forgot to
// disable them Using NOMINMAX may not help when you have pre-compiled headers
#undef min
#undef max
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <sstream>  // str in strstream

#define XLOG_INCLUDED
#if _MSC_VER < 1800
#error "MS VS should be at least 2013"
#endif

#include <chrono>
#include <cwchar>
#include <functional>
#include <iomanip>
#include <ranges>
#include <string>
#include <strstream>
#include <type_traits>

#include "_xdbg.h"
// Target determination
#define XLOG_DEBUG_TARGET 0
#define XLOG_RELEASE_TARGET 1

#if defined(DBG) || defined(_DEBUG) || defined(DEBUG)
#define XLOG_CUR_TARGET XLOG_DEBUG_TARGET
#define XLOG_DEBUG
#else
#define XLOG_CUR_TARGET XLOG_RELEASE_TARGET
#if defined(XLOG_FORCED_DUMP)
#define XLOG_DEBUG  // mandatory for forced
#else
#undef XLOG_VERBOSE
#endif
#endif


namespace xlog {
    inline size_t ConvertChar2Wchar(wchar_t * output, size_t len,
                                    const char *input) noexcept {
        if (input == nullptr || len == 0 || output == nullptr) {
            return 0;
        }
        ::swprintf_s(output, len, L"%S", input);
        return ::wcslen(output);
    }

    inline size_t ConvertWchar2Char(char *output, size_t len,
                                    const wchar_t *input) noexcept {
        if (input == nullptr || len == 0 || output == nullptr) {
            return 0;
        }

        ::sprintf_s(output, len, "%ls", input);
        return ::strlen(output);
    }

    inline size_t ConvertInt2Char(char *output, size_t len,
                                  int value) noexcept {
        if (len == 0 || output == nullptr) {
            return 0;
        }
        ::sprintf_s(output, len, "%d", value);
        return ::strlen(output);
    }

    template <typename T>
    void InternalPrint2Buffer(const wchar_t *prefix, T *buf, size_t len,
                              const T *format_string, ...) noexcept {
        static_assert(sizeof(T) == 1 || sizeof(T) == 2);

        va_list args{nullptr};
        va_start(args, format_string);
        if constexpr (sizeof(T) == 1) {
            auto offset = ConvertWchar2Char(buf, len, prefix);
            if (offset != -1) {
                vsprintf_s(buf + offset, len - offset, format_string, args);
            }

        } else {
            size_t offset = 0;
            if (prefix != nullptr) {
                ::wcscpy_s(buf, len, prefix);
                offset = ::wcslen(buf);
            }
            if (offset != -1) {
                ::vswprintf_s(buf + offset, len - offset, format_string, args);
            }
        }
        va_end(args);
    }

    // Windows Event Log VERY BASIC support
    enum class LogEvents {
        kSuccess = 99,
        kCritical = 1,
        kError = 2,
        kWarning = 3,
        kInformation = 4

    };

    /// Windows Specific log for App, mildly usable.
    template <typename T, typename... Args>
    void SysLogEvent(const T *log_name, LogEvents event_level, DWORD code,
                     const T *event_text, Args &&...args) {
        auto event_source = ::RegisterEventSource(nullptr, log_name);
        if (event_source == nullptr) {
            return;
        }

        unsigned short type = EVENTLOG_ERROR_TYPE;
        switch (event_level) {
            case LogEvents::kSuccess:
                type = EVENTLOG_SUCCESS;
                break;
            case LogEvents::kInformation:
                type = EVENTLOG_INFORMATION_TYPE;
                break;
            case LogEvents::kWarning:
                type = EVENTLOG_WARNING_TYPE;
                break;
            case LogEvents::kError:
            case LogEvents::kCritical:
                type = EVENTLOG_ERROR_TYPE;
                break;
        }
        T buf[4096] = {0};
        xlog::InternalPrint2Buffer(nullptr, buf, 4096, event_text,
                                   std::forward<Args>(args)...);

        const T *strings[2] = {
            log_name,
            buf,
        };
        ::ReportEvent(event_source,  // Event log handle
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

    template <typename T>
    using WorkString = std::basic_string<T>;
    constexpr std::wstring_view kDefaultPrefix{L"***: "};
    constexpr std::string_view kDefaultLogFileName{"default.log"};

    constexpr size_t kInternalMaxOut = 8192;
    constexpr size_t kInternalMaxPrefix = 16;

    // Determines WHEN message is generated
    enum class Type {
        kLogOut = 1,      // always
        kDebugOut = 2,    // on debug
        kVerboseOut = 3,  // when requested
        kOtherOut = 4,    // usually when we have stdio, very special
    };

    // Determine Message attribute
    enum class Marker {
        kErrorMark = 1,    // critical error, with breakpoint
        kWarningMark = 2,  // just not clear situation, but bad
        kTraceMark = 3,    // typical programmers dump
    };
    namespace Directions {
    constexpr uint32_t kDebuggerPrint = 1;
    constexpr uint32_t kStdioPrint = 2;
    constexpr uint32_t kFilePrint = 4;
    constexpr uint32_t kEventPrint = 8;
    }  // namespace Directions
    constexpr auto XLOG_DEFAULT_DIRECTIONS = Directions::kDebuggerPrint;

    namespace Flags {
    constexpr uint32_t kNoPrefix = 1;
    constexpr uint32_t kNoCr = 2;
    constexpr uint32_t kAddCr = 4;
    }  // namespace Flags

    inline std::string CurrentTime() {
        using std::chrono::system_clock;
        const auto cur_time = system_clock::now();
        const auto in_time_t = system_clock::to_time_t(cur_time);
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            cur_time.time_since_epoch()) %
                        1000;
        const auto *loc_time = std::localtime(&in_time_t);  // NOLINT
        const auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");

        std::stringstream sss;
        sss << p_time << "." << std::setfill('0') << std::setw(3) << ms.count()
            << std::ends;
        return sss.str();
    }

    inline std::string CalculateLogFilename(std::string_view file) {
        if (!file.empty()) {
            return std::string{file};
        }

        return std::string{kDefaultLogFileName};
    }

    // Small tool to print data in file
    template <typename T>
    void internal_PrintStringFile(std::string_view file,
                                  std::basic_string_view<T> text) {
        if (text.empty()) {
            return;
        }
        auto filename = CalculateLogFilename(file);

        auto file_ptr = std::fopen(filename.data(), "a");
        if (file_ptr == nullptr) {
            return;
        }

        auto text_time = CurrentTime();

        if constexpr (sizeof(T) == 2)
            std::fprintf(file_ptr, "%s %ls", text_time.c_str(), text.data());
        else
            std::fprintf(file_ptr, "%s %s", text_time.c_str(), text.data());

        std::fclose(file_ptr);
    }

    inline void internal_PrintStringDebugger(const wchar_t *txt) noexcept {
        ::OutputDebugStringW(txt);
    }
    inline void internal_PrintStringDebugger(const char *txt) noexcept {
        ::OutputDebugStringA(txt);
    }
    inline void internal_PrintStringStdio(const wchar_t *txt) noexcept {
        ::printf("%ls", txt);
    }
    inline void internal_PrintStringStdio(const char *txt) noexcept {
        ::printf("%s", txt);
    }

    // utility class which contains data of the last dump and can be post
    // processed
    template <typename T>
    class TextInfo {
    public:
        explicit TextInfo(const T *value) { setText(value); }
        explicit TextInfo(const std::basic_string<T> &value) : text_{value} {}
        TextInfo(const TextInfo &rhs) { setText(rhs.text_); }
        TextInfo &operator=(const TextInfo &rhs) {
            setText(rhs.text_);
            return *this;
        }
        TextInfo(TextInfo &&rhs) noexcept { text_ = std::move(rhs.text_); }
        TextInfo &operator=(TextInfo &&rhs) noexcept {
            text_ = std::move(rhs.text_);
            return *this;
        }
        ~TextInfo() = default;

        // EXTENDED API
        [[maybe_unused]] const TextInfo &filelog(  // NOLINT
            std::string_view filename) const {
            if (filename.empty()) {
                return *this;
            }
            internal_PrintStringFile(filename,
                                     std::basic_string_view<T>{text_});
            return *this;
        }

        // LogName is syslog source name.
        [[maybe_unused]] const TextInfo &syslog(  // NOLINT
            std::basic_string_view<T> log_name, LogEvents log_event,
            int code) const {
            if constexpr (sizeof(T) == 2) {
                // have to convert
                auto output_buf = std::make_unique<char[]>(len() + 1);
                if (ConvertWchar2Char(output_buf, len() + 1, text()))
                    SysLogEvent(log_name, log_event, code, output_buf);
            } else {
                SysLogEvent(log_name, log_event, code, text());
            }

            return *this;
        }

        // print on screen
        [[maybe_unused]] const TextInfo &print() const noexcept {  // NOLINT
            return print(true);
        }

        [[maybe_unused]] const TextInfo &print(  // NOLINT
            bool enable) const noexcept {
            if (enable) {
                internal_PrintStringStdio(text());
            }
            return *this;
        }

        //
        [[nodiscard]] const T *text() const noexcept { return text_.c_str(); }
        [[nodiscard]] size_t len() const noexcept { return text_.length(); }

    private:
        void setText(const T *text) {
            if (text == nullptr) {
                text_.clear();
                return;
            }
            text_ = text;
        }

        std::basic_string<T> text_;
    };

    class LogParam {
    public:
        explicit LogParam(const std::wstring &prefix) noexcept {
            initPrefix(prefix);
        }
        LogParam() noexcept : LogParam(std::wstring{}) {}

        [[nodiscard]] std::string filename() const noexcept {
            return file_name_out_;
        }
        void setFileName(std::string_view file_name) noexcept {
            file_name_out_ = file_name;
        }

        [[nodiscard]] auto prefix() const noexcept { return prefix_; }
        [[nodiscard]] auto prefixAscii() const noexcept {
            return prefix_ascii_;
        }

        void initPrefix(const std::wstring &prefix_text) noexcept {
            prefix_ = prefix_text.empty() ? std::wstring{kDefaultPrefix}
                                          : prefix_text;
            prefix_.resize(std::min(kInternalMaxPrefix, prefix_.length()));

            // 'safe' ASCIIZ conversion
            prefix_ascii_.clear();
            std::ranges::transform(prefix_, std::back_inserter(prefix_ascii_),
                                   [](auto w) { return static_cast<char>(w); });
        }

        xlog::Type type_{Type::kDebugOut};
        xlog::Marker mark_{Marker::kTraceMark};
        uint32_t directions_{XLOG_DEFAULT_DIRECTIONS};
        uint32_t flags_{Flags::kAddCr};

    private:
        std::wstring prefix_;
        std::string prefix_ascii_;
        std::string file_name_out_;
    };

    class AdvancedLog {
    public:
        explicit AdvancedLog(
            const std::function<void(LogParam &)> &log_function) {
            log_function(this->log_param_);
        }
        AdvancedLog() = default;
        LogParam log_param_;
        template <typename T, typename... Args>
        void d(const T *format_string, Args &&...args) {
#if defined(XLOG_DEBUG)
            internal_dout(log_param_, format_string,
                          std::forward<Args>(args)...);
#endif
        }

        template <typename T, typename... Args>
        void v(const T *format_string, Args &&...args) {
#if defined(XLOG_VERBOSE)
            internal_dout(log_param_, format_string,
                          std::forward<Args>(args)...);
#endif
        }

        template <typename T, typename... Args>
        void l(const T *format_string, Args &&...args) {
#if !defined(NO_LOG)
            auto &log_param = log_param_;
            log_param.type_ = Type::kLogOut;
            internal_dout(log_param_, format_string,
                          std::forward<Args>(args)...);
#endif
        }
    };

    template <typename T>
    size_t calc_len(const T *buf) noexcept {
        if constexpr (sizeof(T) == 1) {
            return ::strlen((const char *)buf);
        } else {
            return ::wcslen((const wchar_t *)buf);
        }
    }

    inline void kill_cr(wchar_t * buf) noexcept {
        if (buf == nullptr) {
            return;
        }
        auto len = ::wcslen(buf);
        if (len == 0) {
            return;
        }

        len--;
        while (len != 0U) {
            if (buf[len] == L'\n') {
                buf[len] = 0;
                len--;
            } else {
                break;
            }
        }
    }

    inline void kill_cr(char *buf) noexcept {
        if (buf == nullptr) {
            return;
        }

        auto len = ::strlen(buf);
        if (len == 0) {
            return;
        }

        len--;
        while (len != 0U) {
            if (buf[len] == '\n') {
                buf[len] = 0;
                len--;
            } else {
                break;
            }
        }
    }

    inline void add_cr(wchar_t * buf) noexcept {
        if (buf == nullptr) {
            return;
        }

        auto len = ::wcslen(buf);
        buf[len] = L'\n';
        buf[len + 1] = 0;
    }

    inline void add_cr(char *buf) noexcept {
        if (buf == nullptr) {
            return;
        }

        auto len = ::strlen(buf);
        buf[len] = '\n';
        buf[len + 1] = 0;
    }

#pragma warning(push)
#pragma warning(disable : 26444)
    template <typename T, typename... Args>
    [[maybe_unused]] TextInfo<T> internal_dout(
        const LogParam &log_param, const T *format_string, Args &&...args) {
        T buf[kInternalMaxOut] = {0};

        InternalPrint2Buffer(
            log_param.flags_ & Flags::kNoPrefix ? nullptr
                                                : log_param.prefix().c_str(),
            buf, kInternalMaxOut, format_string, std::forward<Args>(args)...);

        if (log_param.flags_ & Flags::kNoCr) {
            kill_cr(buf);
        } else if (log_param.flags_ & Flags::kAddCr) {
            kill_cr(buf);
            add_cr(buf);
        }

        if (log_param.directions_ & Directions::kDebuggerPrint) {
            internal_PrintStringDebugger(buf);
        }
        if (log_param.directions_ & Directions::kStdioPrint) {
            internal_PrintStringStdio(buf);
        }

        if (log_param.mark_ == Marker::kErrorMark) {
            xdbg::bp();
        }

        const size_t offset = log_param.flags_ & Flags::kNoPrefix
                                  ? 0U
                                  : log_param.prefix().length();

        return TextInfo<T>(buf + offset);
    }
#pragma warning(pop)

    // Common API
    template <typename T, typename... Args>
    void d(const T *format_string, Args &&...args) {
#if defined(XLOG_DEBUG)
        LogParam log_param;
        auto _ = internal_dout(log_param, format_string,
                               std::forward<Args>(args)...);
#endif
    }

    template <typename T, typename... Args>
    void d(bool enable, const T *format_string, Args &&...args) {

#if defined(XLOG_DEBUG)
        if (enable) {
            LogParam log_param;
            internal_dout(log_param, format_string,
                          std::forward<Args>(args)...);
        }
#endif
    }
    template <typename T, typename... Args>
    void v(const T *format_string, Args &&...args) {
#if defined(XLOG_VERBOSE)
        LogParam log_param;
        internal_dout(log_param, format_string, std::forward<Args>(args)...);
#endif
    }
#pragma warning(push)
#pragma warning(disable : 26444)
    template <typename T, typename... Args>
    [[maybe_unused]] TextInfo<T> l(const T *format_string, Args &&...args) {
#if defined(XLOG_NO_LOG)
        return TextInfo<T>((const T *)nullptr);
#else
    LogParam log_param;
    log_param.type_ = Type::kLogOut;
    auto k =
        internal_dout(log_param, format_string, std::forward<Args>(args)...);
    return k;
#endif
    }

    template <typename T, typename... Args>
    [[maybe_unused]] TextInfo<T> l(bool enable, const T *format_string,
                                   Args &&...args) {
        if (!enable) return TextInfo<T>((const T *)nullptr);

#if defined(XLOG_NO_LOG)
        return TextInfo<T>((const T *)nullptr);
#else
    LogParam log_param;
    log_param.type_ = Type::kLogOut;
    auto k =
        internal_dout(log_param, format_string, std::forward<Args>(args)...);
    return k;
#endif
    }

#pragma warning(pop)

    template <typename T>
    class Concatenator {
    public:
        explicit Concatenator(const T *value) : val_(value) {}
        const T *operator+(const T *y) {
            val_ += ": ";
            val_ += y;
            return val_.c_str();
        }

        Concatenator &operator+(const Concatenator &y) {
            val_ += " ";
            val_ += y.get();
            return *this;
        }
        [[nodiscard]] const WorkString<T> &get() const { return val_; }

    private:
        WorkString<T> val_;
    };

    template <typename T>
    Concatenator<T> FunctionPrefix(const T *function_name) {
        return Concatenator<T>(function_name);
    }

    inline Concatenator<char> FileLinePrefix(const char *fname, int line) {
        WorkString<char> file_line(fname);
        file_line += ":";
        char buf[32];
        ConvertInt2Char(buf, 30, line);
        file_line += buf;
        return Concatenator{file_line.c_str()};
    }
} // namespace xlog

#define KX_FUNCTION_PREFIX xlog::FunctionPrefix(__FUNCTION__)
#define XLOG_FUNC xlog::FunctionPrefix(__FUNCTION__)

#define XLOG_FLINE xlog::FileLinePrefix(__FILE__, __LINE__)
#define XLOG_ALL (XLOG_FUNC + XLOG_FLINE)
