
// Provides basic section formatting
// header with optional separator
// empty header
// local header
// default names
// in the future we will add something here
// #TODO Optimise

#pragma once

#ifndef section_header_h__
#define section_header_h__

#include <string>       // we are using strings her
#include <string_view>  // we are using strings her

#include "logger.h"  // we have logging here

namespace cma {

namespace section {

// bracketing

// Usual Section
constexpr std::string_view kLeftBracket{"<<<"};
constexpr std::string_view kRightBracket{">>>"};
constexpr std::string_view kLeftSeparator{":sep("};
constexpr std::string_view kRightSeparator{")"};

// Sub Section(as for WMI)
constexpr std::string_view kLeftSubSectionBracket{"["};
constexpr std::string_view kRightSubSectionBracket{"]"};

// section names
// usually also used as a names in makeHeader
// special name: section must use own name
constexpr std::string_view kUseEmbeddedName = {"*"};

constexpr std::string_view kUptimeName{"uptime"};
constexpr std::string_view kCheckMkName{"check_mk"};
constexpr std::string_view kDfName{"df"};
constexpr std::string_view kMemName{"mem"};
constexpr std::string_view kSystemTime{"systemtime"};
constexpr std::string_view kServices{"services"};
constexpr std::string_view kCheckMk{"check_mk"};

constexpr std::string_view kPlugins{"plugins"};   // not used in makeHeader
constexpr std::string_view kLocalGroup{"local"};  // not used in makeHeader

constexpr std::string_view kMrpe{"mrpe"};                // used in makeHeader
constexpr std::string_view kOhm{"openhardwaremonitor"};  // used in makeHeader
constexpr std::string_view kSkype{"skype"};              // used in makeHeader
constexpr std::string_view kSpool{"spool"};              // used in makeHeader

constexpr std::string_view kLogWatchEventName{"logwatch"};

constexpr std::string_view kPsName{"ps"};
constexpr std::string_view kFileInfoName{"fileinfo"};

// gtest[+]
// Build standard header with optional Separator
// <<<sectionname>>>\n or
// <<<sectionname:sep(9)>>>\n
inline std::string MakeHeader(const std::string_view Name,
                              const char Separator = 0) noexcept {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftBracket;
    if (Name.empty()) {
        XLOG::l.crit(XLOG_FUNC + " supplied empty string to header");
        s += "nothing";
    } else
        s += Name;

    // separator part
    if (Separator) {
        s += kLeftSeparator;
        s += std::to_string(Separator);
        s += kRightSeparator;
    }

    s += kRightBracket;
    s += '\n';

    return s;
}

// gtest[+]
// [subsectionname]
inline std::string MakeSubSectionHeader(const std::string& Name) noexcept {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftSubSectionBracket;
    if (Name.empty()) {
        XLOG::l.crit(XLOG_FUNC + " supplied empty string to subheader");
        s += "nothing";
    } else
        s += Name;

    s += kRightSubSectionBracket;
    s += '\n';

    return s;
}

inline std::string MakeEmptyHeader() {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftBracket;
    s += kRightBracket;
    s += '\n';

    return s;
}

inline std::string MakeLocalHeader() {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftBracket;
    s += kLocalGroup;
    s += kRightBracket;
    s += '\n';

    return s;
}

}  // namespace section
}  // namespace cma
#endif  // section_header_h__
