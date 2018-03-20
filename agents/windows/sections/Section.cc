// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "Section.h"
#include <sstream>
#include "Environment.h"
#include "Logger.h"

Section::Section(const std::string &outputName, const std::string &configName,
                 const Environment &env, Logger *logger,
                 const WinApiAdaptor &winapi)
    : _outputName(outputName)
    , _configName(configName)
    , _env(env)
    , _logger(logger)
    , _winapi(winapi) {}

bool Section::produceOutput(std::ostream &out,
                            const std::optional<std::string> &remoteIP,
                            bool nested) {
    Debug(_logger) << "<<<" << _outputName << ">>>";

    std::string output;
    bool res = generateOutput(output, remoteIP);

    if (res) {
        const char *left_bracket = nested ? "[" : "<<<";
        const char *right_bracket = nested ? "]" : ">>>";

        if (!output.empty()) {
            if (!_outputName.empty() && showHeader()) {
                out << left_bracket << _outputName;
                if (auto sep = separator(); sep != ' ' && !nested) {
                    out << ":sep(" << static_cast<unsigned>(sep) << ")";
                }
                out << right_bracket << "\n";
            }

            out << output;
            if (*output.rbegin() != '\n') {
                out << '\n';
            }
        }
    }

    return res;
}

bool Section::generateOutput(std::string &buffer,
                             const std::optional<std::string> &remoteIP) {
    std::ostringstream inner;
    bool res = produceOutputInner(inner, remoteIP);
    buffer = inner.str();
    return res;
}
