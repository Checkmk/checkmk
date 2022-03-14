// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Provides basic section formatting
// header with optional separator
// empty header
// local header
// default names
// in the future we will add something here

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

// special markers
constexpr std::string_view kFooter4{"<<<<>>>>"};
constexpr std::string_view kFooter4Left{"<<<<"};
constexpr std::string_view kFooter4Right{">>>>"};
constexpr std::string_view kFooterStd{"<<<>>>"};

// Sub Section(as for WMI)
constexpr std::string_view kLeftSubSectionBracket{"["};
constexpr std::string_view kRightSubSectionBracket{"]"};

// section names
// usually also used as a names in makeHeader
// special name: section must use own name
constexpr std::string_view kUseEmbeddedName = {"*"};

constexpr std::string_view kUptimeName{"uptime"};
constexpr std::string_view kDfName{"df"};
constexpr std::string_view kMemName{"mem"};
constexpr std::string_view kSystemTime{"systemtime"};
constexpr std::string_view kServices{"services"};
constexpr std::string_view kCheckMk{"check_mk"};
constexpr std::string_view kCheckMkCtlStatus{"cmk_agent_ctl_status:sep(0)"};

constexpr std::string_view kPlugins{"plugins"};  // NOT used in makeHeader
constexpr std::string_view kLocal{"local"};      // NOT used in makeHeader
constexpr std::string_view kLocalHeader{"local:sep(0)"};  // Used in makeHeader

constexpr std::string_view kMrpe{"mrpe"};                // used in makeHeader
constexpr std::string_view kOhm{"openhardwaremonitor"};  // used in makeHeader
constexpr std::string_view kSkype{"skype"};              // used in makeHeader
constexpr std::string_view kSpool{"spool"};              // used in makeHeader

constexpr std::string_view kLogWatchEventName{"logwatch"};

constexpr std::string_view kPsName{"ps"};
constexpr std::string_view kFileInfoName{"fileinfo"};

constexpr char kTabSeparator = '\t';
constexpr std::wstring_view kTabSeparatorString = L"\t";

constexpr char kPipeSeparator = '|';
constexpr std::wstring_view kPipeSeparatorString = L"|";

constexpr char kCommaSeparator = ',';
constexpr std::wstring_view kCommaSeparatorString = L",";

// gtest[+]
// Build standard header with optional Separator
// <<<sectionname>>>\n or
// <<<sectionname:sep(9)>>>\n
inline std::string MakeHeader(std::string_view name, char separator) noexcept {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftBracket;
    if (name.empty()) {
        XLOG::l.crit(XLOG_FUNC + " supplied empty string to header");
        s += "nothing";
    } else
        s += name;

    // separator part
    if (separator) {
        s += kLeftSeparator;
        s += std::to_string(separator);
        s += kRightSeparator;
    }

    s += kRightBracket;
    s += '\n';

    return s;
}

inline std::string MakeHeader(std::string_view name) noexcept {
    return MakeHeader(name, '\0');
}

// gtest[+]
// [subsectionname]
inline std::string MakeSubSectionHeader(std::string_view name) noexcept {
    using namespace cma::section;
    std::string s;
    s.reserve(32);  // reasonable

    s = kLeftSubSectionBracket;
    if (name.empty()) {
        XLOG::l.crit(XLOG_FUNC + " supplied empty string to subheader");
        s += "nothing";
    } else
        s += name;

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
    s += kLocalHeader;
    s += kRightBracket;
    s += '\n';

    return s;
}

}  // namespace section

// # TODO move to section namespace
namespace provider {  // WMI Sections

// #TODO replace raw ACIIZ with string_view or string
// const char*  used to have compatibilitz with low level WMI API
// and weak design. This is to be fixed in the future.

// Special Section
constexpr const char *kOhm = "openhardwaremonitor";

// Sections
constexpr const char *kDotNetClrMemory = "dotnet_clrmemory";
constexpr const char *kWmiWebservices = "wmi_webservices";
constexpr const char *kWmiCpuLoad = "wmi_cpuload";

constexpr const char *kMsExch = "msexch";

constexpr const char *kMsExchActiveSync = "msexch_activesync";
constexpr const char *kMsExchAvailability = "msexch_availability";
constexpr const char *kMsExchOwa = "msexch_owa";
constexpr const char *kMsExchAutoDiscovery = "msexch_autodiscovery";
constexpr const char *kMsExchIsClientType = "msexch_isclienttype";
constexpr const char *kMsExchIsStore = "msexch_isstore";
constexpr const char *kMsExchRpcClientAccess = "msexch_rpcclientaccess";

constexpr const char *kBadWmi = "bad_wmi";

constexpr const char *kSubSectionSystemPerf = "system_perf";
constexpr const char *kSubSectionComputerSystem = "computer_system";

// Path
constexpr const wchar_t *kWmiPathOhm = L"Root\\OpenHardwareMonitor";
constexpr const wchar_t *kWmiPathStd = L"Root\\Cimv2";

}  // namespace provider
}  // namespace cma
#endif  // section_header_h__
