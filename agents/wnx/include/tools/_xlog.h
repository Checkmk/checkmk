// //////////////////////////////////////////////////////////////////////////
// xlog by Sergey Kipnis
// simplified dump file
// no CPP file required
// every aspect customizable
// cross platform
// NOT FORMATTED WITH CLANG BECAUSE OF stupid ifdefs
// //////////////////////////////////////////////////////////////////////////

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

// NOT RECOMMENDED TO USE ANYMORE
/*
xlog::AdvancedLog mylog;
void InitMe()
{
        mylog.log_param_.flags_ = xlog::Flags::NO_PREFIX;
}

void Something()
{
        mylog.d("Log no prefix");
}
*/

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
// "Bloede Idioten von Microsoft" have defined those macros and forgot to
// disable them Using NOMINMAX may not help when you have pre-compiled headers
#undef min
#undef max
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include <sstream>  // str in strstream

#define XLOG_INCLUDED
#if defined(__linux__) || defined(__native_client__) || defined(__pnacl__) || \
    defined(__APPLE__)
// supported automatically with new gcc or clang
#else
#if _MSC_VER < 1800
#error "MS VS should be at least 2013"
#endif
#endif

#if defined(NTDRV) || defined(NTVIDEO)
#define XLOG_RING_0 1
#endif

#if defined(NTDRV) || defined(NTVIDEO) || defined(XLOG_NO_STRING)
#define XLOG_LIMITED_BUILD 1
#if defined(_HAS_EXCEPTIONS) && (_HAS_EXCEPTIONS != 0)
#error \
    "Please, define at the beginning of srdatfx.h _HAS_EXCEPTIONS=0 - required for your target"
#endif
#endif

#if !defined(XLOG_DEFAULT_DIRECTIONS)
#if defined(__linux__)
#define XLOG_DEFAULT_DIRECTIONS Directions::kStdioPrint
#else
#define XLOG_DEFAULT_DIRECTIONS Directions::kDebuggerPrint
#endif
#endif

#if defined(NTDRV) || defined(NTVIDEO)
#define XLOG_LIMITED_BUILD 1
#endif

#if defined(XLOG_LIMITED_BUILD)
#if _MSC_VER >= 1900

// Attention!
// In MS VC 2017 we have problems with type_trait due to stdio linkage
namespace std
{
    template <class _Ty>
    struct remove_reference {  // remove reference
        using type = _Ty;
    };

    template <class _Ty>
    struct remove_reference<_Ty &> {  // remove reference
        using type = _Ty;
    };

    template <class _Ty>
    struct remove_reference<_Ty &&> {  // remove rvalue reference
        using type = _Ty;
    };

    template <class _Ty>
    using remove_reference_t = typename remove_reference<_Ty>::type;

    // FUNCTION TEMPLATE forward
    template <class _Ty>
    constexpr _Ty &&forward(
        remove_reference_t<_Ty> &
        _Arg) {  // forward an lvalue as either an lvalue or an rvalue
        return (static_cast<_Ty &&>(_Arg));
    }

    template <class _Ty>
    constexpr _Ty &&forward(remove_reference_t<_Ty> &&
                            _Arg) {  // forward an rvalue as an rvalue
        static_assert(!is_lvalue_reference_v<_Ty>, "bad forward call");
        return (static_cast<_Ty &&>(_Arg));
    }
};
#else
// older MS VC support type_trait good
#include <type_traits>
#endif
#else
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
#include <wchar.h>

#include <chrono>
#include <iomanip>
#include <string>
#include <strstream>
#include <type_traits>

#include "functional"
#endif


// utilities for ring 0
namespace xlog {
    // string length calculators, for ring 0
    template <typename T>
    size_t CalcStrLen(const T *Arg) {
        return 0;
    }

    template <>
    inline size_t CalcStrLen<char>(const char *Arg) {
        return strlen(Arg);
    }
    template <>
    inline size_t CalcStrLen<wchar_t>(const wchar_t *Arg) {
        return wcslen(Arg);
    }

    // small string class for ring 0
    template <typename T>
    class FixedStr {
    public:
        static const int MaxLen = 256;
        FixedStr() {
            body_ = new T[MaxLen];
            body_[0] = 0;
        }

        FixedStr(const T *Text) {
            body_ = new T[MaxLen];
            safeAssign(Text);
        }

        FixedStr(FixedStr &&Src) {
            body_ = Src.body_;
            Src.body_ = nullptr;
        }

        ~FixedStr() { delete[] body_; }

        FixedStr &operator=(const T *Text) {
            if (!body_) return;
            SafeAssign(Text);
            return *this;
        }

        FixedStr &operator=(const FixedStr &Src) {
            if (!body_) return;
            SafeAssign(Src.body_);
            return *this;
        }

        FixedStr &operator=(FixedStr &&Src) {
            if (!body_) return;
            body_ = Src.body_;
            Src.body_ = nullptr;
            return *this;
        }

        const T *c_str() const { return body_; }

        FixedStr &operator+=(const FixedStr &y) {
            add(y.c_str());
            return *this;
        }

        void add(const T *Text) {
            auto len1 = CalcStrLen(body_);
            auto len2 = CalcStrLen(Text);
            if (len1 > MaxLen - 1) {
                return;
            }

            if (len1 + len2 > MaxLen - 1) {
                len2 = MaxLen - 1 - len1;
            }

            memcpy(body_ + len1, Text, len2);
            body_[len1 + len2] = 0;
        }

    private:
        void safeAssign(const T *Text) {
            auto len = CalcStrLen(Text);
            if (len >= MaxLen - 1) len = MaxLen - 1;
            memcpy(body_, Text, len * sizeof(T));
            body_[len] = 0;
        }
        T *body_;
    };
}// namespace xlog

#include "_xdbg.h"
// Target determination
#define XLOG_DEBUG_TARGET 0
#define XLOG_RELEASE_TARGET 1

#if DBG || defined(_DEBUG) || defined(DEBUG)
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



//#include <string>
namespace xlog {
    inline int ConvertChar2Wchar(wchar_t * Output, int Len, const char *Input) {
        if (Input == nullptr || Len <= 0) return 0;
#if defined(XLOG_LIMITED_BUILD)
        // Simple conversion when swprintf is not allowed
        auto input = Input;
        auto output = Output;
        auto pos = 0;
        do {
            if (pos++ == Len - 1) {
                *output = 0;
                break;
            }
            *output++ = *input++;
        } while (*input);
#elif _MSC_VER >= 1700
    swprintf_s(Output, Len, L"%S", Input);
#elif defined(__linux) || defined(CX_SUBOS_CHROME) || defined(__pnacl__)
    swprintf(Output, Len, L"%s", Input);
#else
    swnprintf(Output, Len, L"%S", Input);
#endif

        return (int)wcslen(Output);
    }

    inline int NtDrvConvertWchar2Char(char *Output, int Len,
                                      const wchar_t *Input) {
        if (Input == nullptr || Output == nullptr) return 0;

        // sprintf(Output, "%ls", Input); <-- may call paged code
        const auto output = Output;
        if (Len) {
            do {
                *Output++ = (char)(*Input++);
            } while (--Len && *Input);

            if (Len)
                *Output = 0;  // finish output
            else
                Output[-1] = 0;  // special case when output string is too short
                                 // and probably last value is not 0
            return (int)strlen(output);
        } else {
            return 0;
        }
    }

    inline int ConvertWchar2Char(char *Output, int Len, const wchar_t *Input) {
        if (Input == nullptr) return 0;

#if defined(NTVIDEO)
#pragma warning(push)
#pragma warning(disable : 4996)
        sprintf(Output, "%ls", Input);
#pragma warning(pop)
#elif defined(NTDRV)
    // sprintf(Output, "%ls", Input); <-- may call paged code
    return NtDrvConvertWchar2Char(Output, Len, Input);
#elif _MSC_VER >= 1700
    sprintf_s(Output, Len, "%ls", Input);
#else
    snprintf(Output, Len, "%ls", Input);
#endif

        return (int)strlen(Output);
    }

    // converter from the Int to string, simple, to be used only in NTDRV(where
    // we have possibility to crash system with sprintf)
    inline void NtDrvItoA(char *Output, int val, int base) {
        int digits = 1;
        int cur_val = val;
        if (val < 0) {
            Output[0] = '-';
            Output++;
            val *= -1;
        }
        while (cur_val /= base) digits++;
        Output[digits] = 0;
        for (; val && digits; --digits, val /= base)
            Output[digits - 1] = "0123456789ABCDEF"[val % base];
    }

    inline int ConvertInt2Char(char *Output, int Len, int Value) {
#if defined(NTVIDEO)
#pragma warning(push)
#pragma warning(disable : 4996)
        sprintf(Output, "%d", Value);
#pragma warning(pop)
#elif defined(NTDRV)
    // sprintf(Output, "%d", Value); <<--- dangerous in RINg-0 Dispatch LEVEL
    NtDrvItoA(Output, Value, 10);
#elif _MSC_VER >= 1700
    sprintf_s(Output, Len, "%d", Value);
#else
    snprintf(Output, Len, "%d", Value);
#endif

        return (int)strlen(Output);
    }

    // Windows Event Log VERY BASIC support
    enum LogEvents {
        kSuccess = 99,
        kCritical = 1,
        kError = 2,
        kWarning = 3,
        kInformation = 4

    };

    /// Windows Specific log for App, mildly usable.
    template <typename T, typename... Args>
    void SysLogEvent(const T *LogName, LogEvents EventLevel, int Code,
                     const T *Text, Args... args) {
#if defined(_WIN32) && defined(EVENTLOG_ERROR_TYPE)
        auto eventSource = RegisterEventSource(nullptr, LogName);
        if (eventSource) {
            unsigned short type = EVENTLOG_ERROR_TYPE;
            switch (EventLevel) {
                case kSuccess:
                    type = EVENTLOG_SUCCESS;
                    break;
                case kInformation:
                    type = EVENTLOG_INFORMATION_TYPE;
                    break;
                case kWarning:
                    type = EVENTLOG_WARNING_TYPE;
                    break;
                case kError:
                case kCritical:
                    type = EVENTLOG_ERROR_TYPE;
                    break;
                default:
                    type = EVENTLOG_INFORMATION_TYPE;
                    break;
            }
            T buf[4096];
            xlog::internal_Print2Buffer(nullptr, buf, 4096, Text,
                                        std::forward<Args>(args)...);

            const T *strings[2] = {
                LogName,
                buf,
            };
            ReportEvent(eventSource,  // Event log handle
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
#else
    // not implemented
#endif
    }

#if defined(XLOG_LIMITED_BUILD)
    template <typename T>
    using WorkString = FixedStr<T>;
#else
template <typename T>
using WorkString = std::basic_string<T>;
#endif
    // implementation
    const wchar_t *const kDefaultPrefix = L"***: ";
    const char *const kDefaultLogFileName = "default.log";

    enum Consts {
#if XLOG_LIMITED_BUILD
        kInternalMaxOut = 512,
#else
    kInternalMaxOut = 8192,
#endif
        kInternalMaxPrefix = 16,
        kFileNameLength = 512
    };

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

    // Determine Message attribute
    enum Directions {
        kDebuggerPrint = 1,  //
        kStdioPrint = 2,     //
        kFilePrint = 4,      //
        kEventPrint = 8,     // eventlog too
    };

    enum Flags {
        kNoPrefix = 1,  //
        kNoCr = 2,      //
        kAddCr = 4,     //
    };

    enum LogCodes {
        kIamLazy = 13,
        kBadParameters = 100,  // wrong data, json for example
        kNullData = 200,       // nullptr
        kLogicFail = 300,      // it is impossible case
        kTodo = 400,           // not implemented yet
        kBadData = 500,        // something wrong
    };

    const char *const kDefaultFile = "";

    // Small tool to print data in file
    // cross platform
    template <typename T>
    void internal_PrintStringFile(const char *FileName, const T *Text) {
#if defined(NTDRV) || defined(NTVIDEO)
        // not implemented
#else  // Ring-3:
    if (0 == FileName[0]) {
#if defined(DBG_NAME)
        FileName = DBG_NAME ".log";
#else
        FileName = kDefaultLogFileName;
#endif
    }

    if (Text[0] == 0) return;  // skip empty strings

    auto file_ptr = std::fopen(FileName, "a");
    if (!file_ptr) {
#if defined(_WIN32)
        auto error = GetLastError();
        xlog::l("You have error %d opening file %s", error, FileName);
#else
        // old GCC cannot find not declared xlog::l
        // xlog::l("You have error opening file %s", FileName);
#endif
        return;
    }

    {
        auto cur_time = std::chrono::system_clock::now();
        auto in_time_t = std::chrono::system_clock::to_time_t(cur_time);
        std::stringstream sss;
#if defined(_WIN32)
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                      cur_time.time_since_epoch()) %
                  1000;
        auto loc_time = std::localtime(&in_time_t);
        auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
        sss << p_time << "." << std::setfill('0') << std::setw(3) << ms.count()
            << std::ends;
#else
        sss << (in_time_t / 1024) << std::ends;
#endif
        std::fprintf(file_ptr, "%s ", sss.str().c_str());
    }

    if (sizeof(T) == 2)
        std::fprintf(
            file_ptr, "%ls",
            (wchar_t *)Text);  // not very elegant, we have to avoid warning
                               // when instantiating template with T = char
    else
        std::fprintf(
            file_ptr, "%s",
            (char *)Text);  // not very elegant, we have to avoid warning
                            // when instantiating template with T = char
    std::fclose(file_ptr);
#endif  // end of Ring3
    }

#if defined(NTDRV)
    inline void internal_PrintStringDebugger(const wchar_t *Txt) {
        DbgPrint("%S", Txt);
    };
    inline void internal_PrintStringDebugger(const char *Txt) {
        DbgPrint(Txt);
    };
    inline void internal_PrintStringStdio(const wchar_t *){};
    inline void internal_PrintStringStdio(const char *){};
#elif defined(NTVIDEO)
inline void internal_VideoDebugPrint(const char *DebugMessage, ...) {
    va_list ap;

    va_start(ap, DebugMessage);
    EngDebugPrint("", (PCHAR)DebugMessage, ap);
    va_end(ap);
}
inline void internal_PrintStringDebugger(const wchar_t *Txt) {
    internal_VideoDebugPrint("%S", Txt);
};
inline void internal_PrintStringDebugger(const char *Txt) {
    internal_VideoDebugPrint(Txt);
};
inline void internal_PrintStringStdio(const wchar_t *){};
inline void internal_PrintStringStdio(const char *){};
#elif defined(_WIN32)
inline void internal_PrintStringDebugger(const wchar_t *Txt) {
    OutputDebugStringW(Txt);
};
inline void internal_PrintStringDebugger(const char *Txt) {
    OutputDebugStringA(Txt);
};
inline void internal_PrintStringStdio(const wchar_t *Txt) {
    printf("%ls", Txt);
};
inline void internal_PrintStringStdio(const char *Txt) { printf("%s", Txt); };
#elif defined(LINUX) || defined(CX_SUBOS_CHROME)
inline void internal_PrintStringDebugger(const wchar_t *){};
inline void internal_PrintStringDebugger(const char *){};
inline void internal_PrintStringStdio(const wchar_t *Txt) {
    printf("%ls", Txt);
};
inline void internal_PrintStringStdio(const char *Txt) { printf("%s", Txt); };
#elif defined(_CONSOLE)
inline void internal_PrintStringDebugger(const wchar_t *Txt) {
    OutputDebugStringW(Txt);
};
inline void internal_PrintStringDebugger(const char *Txt) {
    OutputDebugStringA(Txt);
};
inline void internal_PrintStringStdio(const wchar_t *Txt) {
    printf("%ls", Txt);
};
inline void internal_PrintStringStdio(const char *Txt) { printf("%s", Txt); };
#else
#error "Target is unknown"
#endif

    // cross platform array allocator
    template <typename T>
    T *CxArrayAlloc(size_t Count) {
#if defined(XLOG_RING_0)
        return new T[Count];
#else

    try {
        return new T[Count];
    } catch (...) {
        return nullptr;
    }
#endif
    }

    // utility class which contains data of the last dump and can be post
    // processed
    template <typename T>
    class TextInfo {
    public:
        // COPY CREATE
        explicit TextInfo(const T *Rhs) : text_(nullptr) { setText(Rhs); }

        explicit TextInfo(const TextInfo &Rhs) : text_(nullptr) {
            setText(Rhs.text_);
        }

        TextInfo &operator=(const TextInfo &Rhs) {
            text_ = nullptr;
            setText(Rhs.text_);
            return *this;
        }

        // MOVE CREATE
        TextInfo(TextInfo &&Rhs) {
            text_ = Rhs.text_;
            Rhs.text_ = nullptr;
        }

        TextInfo &operator=(TextInfo &&Rhs) {
            delete[] text_;
            text_ = Rhs.text_;
            Rhs.text_ = nullptr;
            return *this;
        }

        // DTOR
        ~TextInfo() { delete[] text_; }

        // EXTENDED API
        // FileName,nullptr - no print
        //			"" - default file
        const TextInfo &filelog(const char *FileName = nullptr) const {
            if (!FileName) return *this;
            internal_PrintStringFile(FileName, text());
            return *this;
        }

        const TextInfo &filelog(const std::string FileName) const {
            if (FileName.empty()) return *this;
            internal_PrintStringFile(FileName.c_str(), text());
            return *this;
        }

        // LogName is syslog source name. If nullptr - no print
        //
        const TextInfo &syslog(const char *LogName, xlog::LogEvents LogEvent,
                               int Code = xlog::LogCodes::kIamLazy) const {
            if (!LogName) return *this;

            if (sizeof(T) == 2) {
                // have to convert
                auto output_buf = new char[len() + 1];
                if (ConvertWchar2Char(output_buf, len() + 1, (wchar_t *)text()))
                    SysLogEvent(LogName, LogEvent, Code, output_buf);
                delete[] output_buf;
            } else {
                SysLogEvent(LogName, LogEvent, Code, (char *)text());
            }

            return *this;
        }

        // print on screen
        const TextInfo &print(bool Enable = true) const {
            if (Enable) internal_PrintStringStdio(text());
            return *this;
        }

        //
        const T *text() const { return text_ ? text_ : (const T *)&text_; }

        // private implementation to decrease cross-platform include
        // dependencies
        size_t len() const {
            if (!text_) return 0;
            auto p = text_;
            while (*p++)
                ;
            return p - text_ - 1;
        }

    private:
        void setText(const T *Text) {
            delete[] text_;
            if (Text && Text[0]) {
                // get length
                auto p = Text;
                while (*p++)
                    ;
                // alloc and fill
                text_ = CxArrayAlloc<T>(p - Text);
                if (text_) memcpy(text_, Text, (p - Text) * sizeof(T));
            } else
                text_ = nullptr;
        }

        T *text_;
    };

    inline const wchar_t *GetPrefix() {
#if defined(DBG_NAME_DYNAMIC)
        static wchar_t prefix[256] = L"";
        ConvertChar2Wchar(prefix, 128, DBG_NAME_DYNAMIC);
        return prefix;
#elif defined(DBG_NAME)
    static bool first_run = true;
    static wchar_t prefix[256] = L"";
    if (first_run) {
        first_run = false;
        ConvertChar2Wchar(prefix, 128, DBG_NAME);
    }
    return prefix;
#else
    return kDefaultPrefix;
#endif
    }

    class LogParam {
    public:
        LogParam(const wchar_t *const Prefix = nullptr)
            : type_(Type::kDebugOut)
            , mark_(Marker::kTraceMark)
            , directions_(XLOG_DEFAULT_DIRECTIONS)
            , flags_(kAddCr) {
            file_name_out_[0] = 0;
            initPrefix(Prefix);
        }

        const char *filename() const { return file_name_out_; }
        void setFileName(const char *FileName) {
            if (FileName) {
                if (strlen(FileName) < kFileNameLength)
                    strcpy(file_name_out_, FileName);
            } else
                file_name_out_[0] = 0;
        }

        xlog::Type type_;
        xlog::Marker mark_;  // # TODO this is not a good place
        int directions_;
        int flags_;

    private:
        wchar_t prefix_[kInternalMaxPrefix];
        char prefix_ascii_[kInternalMaxPrefix];
        char file_name_out_[kFileNameLength];

    public:
        auto prefix() const { return prefix_; }
        auto prefixAscii() const { return prefix_ascii_; }

        void initPrefix(const wchar_t *Prefix) {
            auto prefix = Prefix ? Prefix : GetPrefix();

            // safe ASCIIZ copy
            auto len = static_cast<int>(wcslen(prefix));
            auto to_copy = std::min(len, kFileNameLength - 1);
            memcpy(prefix_, prefix, to_copy * sizeof(wchar_t));
            prefix_[to_copy] = 0;

            // "safe" UTF16 to UTF8 conversion, for prefix enough
            for (int i = 0;; ++i) {
                auto ch = prefix_[i];
                prefix_ascii_[i] = static_cast<char>(ch);
                if (ch == 0) break;
            }
        }
    };

    class AdvancedLog {
    public:
#if !defined(XLOG_LIMITED_BUILD)
        AdvancedLog(std::function<void(LogParam &)> Log) {
            Log(this->log_param_);
        }
#endif
        AdvancedLog() {}
        LogParam log_param_;
        template <typename T, typename... Args>
        inline void d(const T *Format, Args &&... args) {
#if defined(XLOG_DEBUG)
            internal_dout(log_param_, Format, std::forward<Args>(args)...);
#endif
        }

        template <typename T, typename... Args>
        inline void v(const T *Format, Args &&... args) {
#if defined(XLOG_VERBOSE)
            internal_dout(log_param_, Format, std::forward<Args>(args)...);
#endif
        }

        template <typename T, typename... Args>
        inline void l(const T *Format, Args &&... args) {
#if !defined(NO_LOG)
            auto &log_param = log_param_;
            log_param.type_ = Type::kLogOut;
            internal_dout(log_param_, Format, std::forward<Args>(args)...);
#endif
        }
    };

    void internal_Print2Buffer(const wchar_t *Prefix, wchar_t *Buf, int Len,
                               const wchar_t *Format, ...);

    inline void internal_Print2Buffer(const wchar_t *Prefix, char *Buf, int Len,
                                      const char *Format, ...) {
        va_list args;
        va_start(args, Format);
        auto offset = ConvertWchar2Char(Buf, Len, Prefix);
        if (offset != -1) {
#if defined(NTVIDEO)
#pragma warning(push)
#pragma warning(disable : 4996)
            vsprintf(Buf + offset, Format, args);
#pragma warning(pop)
#elif _MSC_VER >= 1700
        vsprintf_s(Buf + offset, Len - offset, Format, args);
#elif defined(__linux) || defined(CX_SUBOS_CHROME) || defined(__pnacl__)
        vsnprintf(Buf + offset, Len - offset, Format, args);
#else
        CxVsnprintf(Buf + offset, Len - offset, Format, args);
#endif
        }
        va_end(args);
    }
    template <typename T>
    size_t calc_len(const T *Buf) {
        if (sizeof(T) == 1)
            return strlen((const char *)Buf);
        else
            return wcslen((const wchar_t *)Buf);
    }

    inline void kill_cr(wchar_t * Buf) {
        if (!Buf) return;
        auto len = wcslen(Buf);
        if (!len) return;
        len--;
        while (len) {
            if (Buf[len] == L'\n') {
                Buf[len] = 0;
                len--;
            } else
                break;
        }
    }

    inline void kill_cr(char *Buf) {
        if (!Buf) return;
        auto len = strlen(Buf);
        if (!len) return;
        len--;
        while (len) {
            if (Buf[len] == '\n') {
                Buf[len] = 0;
                len--;
            } else
                break;
        }
    }

    inline void add_cr(wchar_t * Buf) {
        if (!Buf) return;
        auto len = wcslen(Buf);
        Buf[len] = L'\n';
        Buf[len + 1] = 0;
    }

    inline void add_cr(char *Buf) {
        if (!Buf) return;
        auto len = strlen(Buf);
        Buf[len] = '\n';
        Buf[len + 1] = 0;
    }

    template <typename T, typename... Args>
    inline TextInfo<T> internal_dout(const LogParam &Param, const T *Format,
                                     Args &&... args) {
        T buf[kInternalMaxOut];

        internal_Print2Buffer(
            Param.flags_ & Flags::kNoPrefix ? nullptr : Param.prefix(), buf,
            kInternalMaxOut, Format, std::forward<Args>(args)...);

        if (Param.flags_ & kNoCr) {
            kill_cr(buf);
        } else if (Param.flags_ & kAddCr) {
            kill_cr(buf);
            add_cr(buf);
        }

        if (Param.directions_ & Directions::kDebuggerPrint)
            internal_PrintStringDebugger(buf);
        if (Param.directions_ & Directions::kStdioPrint)
            internal_PrintStringStdio(buf);

        if (Param.mark_ == Marker::kErrorMark) {
            xdbg::bp();
        }

        auto offset =
            Param.flags_ & Flags::kNoPrefix ? 0 : calc_len(Param.prefix());

        return TextInfo<T>(buf + offset);
    }

    // Common API
    template <typename T, typename... Args>
    inline void d(const T *Format, Args &&... args) {
#if defined(XLOG_LIMITED_BUILD)
        static_assert(sizeof(T) == 1,
                      "Wide Char output for the target is not possible");
#endif
#if defined(XLOG_DEBUG)
        LogParam log_param;
        internal_dout(log_param, Format, std::forward<Args>(args)...);
#else
    // return TextInfo<T>((const T*)nullptr);
#endif
    }

    template <typename T, typename... Args>
    inline void d(bool Enable, const T *Format, Args &&... args) {
#if defined(XLOG_LIMITED_BUILD)
        static_assert(sizeof(T) == 1,
                      "Wide Char output for the target is not possible");
#endif

#if defined(XLOG_DEBUG)
        if (Enable) {
            LogParam log_param;
            internal_dout(log_param, Format, std::forward<Args>(args)...);
        }
#else
    // return TextInfo<T>((const T*)nullptr);
#endif
    }
    template <typename T, typename... Args>
    inline void v(const T *Format, Args &&... args) {
#if defined(XLOG_LIMITED_BUILD)
        static_assert(sizeof(T) == 1,
                      "Wide Char output for the target is not possible");
#endif
#if defined(XLOG_VERBOSE)
        LogParam log_param;
        internal_dout(log_param, Format, std::forward<Args>(args)...);
#else
    // TextInfo<T>((const T*)nullptr);
#endif
    }

    template <typename T, typename... Args>
    inline TextInfo<T> l(const T *Format, Args &&... args) {
#if defined(XLOG_LIMITED_BUILD)
        static_assert(sizeof(T) == 1,
                      "Wide Char output for the target is not possible");
#endif
#if defined(XLOG_NO_LOG)
        return TextInfo<T>((const T *)nullptr);
#else
    LogParam log_param;
    log_param.type_ = Type::kLogOut;
    auto k = internal_dout(log_param, Format, std::forward<Args>(args)...);
    return k;
#endif
    }

    template <typename T, typename... Args>
    inline TextInfo<T> l(bool Enable, const T *Format, Args &&... args) {
#if defined(XLOG_LIMITED_BUILD)
        static_assert(sizeof(T) == 1,
                      "Wide Char output for the target is not possible");
#endif
        if (!Enable) return TextInfo<T>((const T *)nullptr);

#if defined(XLOG_NO_LOG)
        return TextInfo<T>((const T *)nullptr);
#else
    LogParam log_param;
    log_param.type_ = Type::kLogOut;
    auto k = internal_dout(log_param, Format, std::forward<Args>(args)...);
    return k;
#endif
    }

    // rare API
    inline void dumpBinData(const char *Marker, const void *Data,
                            int SizeofData) {
#if defined(XLOG_DEBUG)
        const int MAX_STRING_LEN = 80;
        const char *data = static_cast<const char *>(Data);
        int rowCount = SizeofData / MAX_STRING_LEN + 1;
        for (int row = 0; row < rowCount; row++) {
            xlog::FixedStr<char> output = "";
            auto max_data =
                SizeofData > MAX_STRING_LEN ? MAX_STRING_LEN : SizeofData;
            for (int i = 0; i < max_data; i++) {
                char hexString[12];
                if (i % 4 == 0 && i) output.add(" ");
#if defined(__linux__)
                sprintf(hexString, "%02X", (unsigned char)(data[i]));
#elif defined(NTVIDEO)
#pragma warning(push)
#pragma warning(disable : 4996)
                sprintf(hexString, "%02X", (unsigned char)(data[i]));
#pragma warning(pop)
#elif defined(NTDRV)
                sprintf(hexString, "%02X", (unsigned char)(data[i]));
#else
                sprintf_s(hexString, 12, "%02X", (unsigned char)(data[i]));
#endif
                output.add(hexString);
            }
            xlog::d("%s %s\n", Marker, output.c_str());
            data += max_data;
            SizeofData -= max_data;
        }
#endif  // defined(DBG) || defined(_DEBUG)
    }

    template <typename T>
    struct Concatenator {
    public:
        Concatenator(const T *Val) : val_(Val) {}
        const T *operator+(const T *y) {
            val_ += ": ";
            val_ += y;
            return val_.c_str();
        };

        Concatenator &operator+(const Concatenator &y) {
            val_ += " ";
            val_ += y.get();
            return *this;
        };
        const WorkString<T> &get() const { return val_; }

    private:
        WorkString<T> val_;
    };

    template <typename T>
    inline Concatenator<T> FunctionPrefix(const T *FunctionName) {
        return Concatenator<T>(FunctionName);
    }

    inline Concatenator<char> FileLinePrefix(const char *FileName, int Line) {
        WorkString<char> file_line(FileName);
        file_line += ":";
        char buf[32];
        ConvertInt2Char(buf, 30, Line);
        file_line += buf;
        return Concatenator<char>(file_line.c_str());
    }
    };  // namespace xlog

#if defined(_MSC_VER)
#define KX_FUNCTION_PREFIX xlog::FunctionPrefix(__FUNCTION__)
#define XLOG_FUNC xlog::FunctionPrefix(__FUNCTION__)
#else
#define KX_FUNCTION_PREFIX xlog::FunctionPrefix(__func__)
#define XLOG_FUNC xlog::FunctionPrefix(__func__)
#endif

#define XLOG_FLINE xlog::FileLinePrefix(__FILE__, __LINE__)
#define XLOG_ALL XLOG_FUNC + XLOG_FLINE
// usage
// xlog::d(XLOG_FUNC + XLOG_FL + " My dump %d\n", 3);

//#if defined(here)

#undef here
#define here()                                                    \
    do {                                                          \
        xlog::d("### ERROR ###  in %s:%d\n", __FILE__, __LINE__); \
        xdbg::bp();                                               \
    } while (0)
#undef dump
#define dump xlog::d
#undef dlog
#define dlog xlog::l
#undef verbose
#define verbose xlog::v
#undef CX_ASSERT
#define CX_ASSERT(expr)                                            \
    do {                                                           \
        if (!(expr)) {                                             \
            xlog::d("### ASSERT ### %s:%d\n", __FILE__, __LINE__); \
            xdbg::bp();                                            \
        }                                                          \
    } while (0)
#undef derr
#define derr(Text)                                                             \
    do {                                                                       \
        xlog::d("### ERROR ###  in %s:%d \"%s\"\n", __FILE__, __LINE__, Text); \
        xdbg::bp();                                                            \
    } while (0)
#undef DumpBinaryData
#define DumpBinaryData xlog::dumpBinData
    //#endif

    inline void xlog::internal_Print2Buffer(const wchar_t *Prefix, wchar_t *Buf,
                                            int Len, const wchar_t *Format,
                                            ...) {
#if defined(XLOG_LIMITED_BUILD)
    return;
#else
    va_list args;
    va_start(args, Format);
    int offset = 0;
    if (Prefix) {
#if defined(XLOG_RING_0)
#pragma warning(push)
#pragma warning(disable : 4996)
        wcscpy(Buf, Prefix);
#pragma warning(pop)
#elif _MSC_VER >= 1700
        wcscpy_s(Buf, Len, Prefix);
#else
        wcscpy(Buf, Prefix);
#endif
        offset = (int)wcslen(Buf);
    }

    if (offset != -1) {
#if defined(XLOG_RING_0)
#pragma warning(push)
#pragma warning(disable : 4996)
        vswprintf(Buf + offset, Len - offset, Format, args);
#pragma warning(pop)
#elif _MSC_VER >= 1700
        vswprintf_s(Buf + offset, Len - offset, Format, args);
#elif defined(__linux) || defined(CX_SUBOS_CHROME) || defined(__pnacl__)
        vswprintf(Buf + offset, Len - offset, Format, args);
#else
        CxVsnwprintf(Buf + offset, Len, Format, args);
#endif
    }
    va_end(args);
#endif
    }
