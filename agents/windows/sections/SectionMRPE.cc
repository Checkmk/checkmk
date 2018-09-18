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

#include "SectionMRPE.h"
#include <cstring>
#include "Environment.h"
#include "ExternalCmd.h"
#include "Logger.h"
#include "SectionHeader.h"

using std::regex;
using std::sregex_token_iterator;
using std::string;
using std::vector;

SectionMRPE::SectionMRPE(Configuration &config, Logger *logger,
                         const WinApiInterface &winapi)
    : Section("mrpe", config.getEnvironment(), logger, winapi,
              std::make_unique<DefaultHeader>("mrpe", logger))
    , _entries(config, "mrpe", "check", winapi)
    , _includes(config, "mrpe", "include", winapi) {}

void SectionMRPE::updateIncludes() {
    _included_entries.clear();

    for (const auto &[user, path] : *_includes) {
        std::ifstream ifs(path);
        if (!ifs) {
            Warning(_logger) << "Include file not found " << path;
            continue;
        }

        string line;
        for (unsigned lineno = 1; std::getline(ifs, line); ++lineno) {
            ltrim(line);
            rtrim(line);
            if (line.empty() || line[0] == '#' || line[0] == ';')
                continue;  // skip empty lines and comments

            // split up line at = sign
            auto tokens = tokenize(line, "=");
            if (tokens.size() != 2) {
                Warning(_logger)
                    << "Invalid line " << lineno << " in " << path << ".";
                continue;
            }
            auto &var = tokens[0];
            auto &value = tokens[1];
            rtrim(var);
            std::transform(var.cbegin(), var.cend(), var.begin(), tolower);
            ltrim(value);

            if (var == "check") {
                mrpe_entry entry = from_string<mrpe_entry>(_winapi, value);
                entry.run_as_user = user;
                _included_entries.push_back(entry);
            }
        }
    }
}

bool SectionMRPE::produceOutputInner(std::ostream &out,
                                     const std::optional<std::string> &) {
    Debug(_logger) << "SectionMRPE::produceOutputInner";
    updateIncludes();

    mrpe_entries_t all_entries;
    all_entries.insert(all_entries.end(), _entries->begin(), _entries->end());
    all_entries.insert(all_entries.end(), _included_entries.begin(),
                       _included_entries.end());

    for (const auto &entry : all_entries) {
        out << entry << " ";
        Debug(_logger) << entry.run_as_user << " " << entry;

        string run_as_prefix;

        if (!entry.run_as_user.empty()) {
            run_as_prefix = "runas /User:" + entry.run_as_user + " ";
        }
        string modified_command = run_as_prefix + entry.command_line;

        try {
            ExternalCmd command(modified_command, _env, _logger, _winapi);
            Debug(_logger) << "Script started -> collecting data";
            string buffer(8192, '\0');
            char *buf_start = &buffer[0];
            char *pos = &buffer[0];
            while (command.exitCode() == STILL_ACTIVE) {
                DWORD read = command.readStdout(
                    pos, buffer.size() - (pos - buf_start), false);
                pos += read;
                _winapi.Sleep(10);
            }
            DWORD read = command.readStdout(
                pos, buffer.size() - (pos - buf_start), false);
            pos += read;
            buffer.resize(pos - buf_start);
            rtrim(buffer);
            ltrim(buffer);

            // replace newlines
            std::transform(buffer.cbegin(), buffer.cend(), buffer.begin(),
                           [](char ch) {
                               if (ch == '\n') return '\1';
                               if (ch == '\r')
                                   return ' ';
                               else
                                   return ch;
                           });
            int nagios_code = command.exitCode();
            out << nagios_code << " " << buffer << "\n";
            Debug(_logger) << "Script finished";
        } catch (const std::exception &e) {
            Error(_logger) << "mrpe failed: " << e.what();
            out << "3 Unable to execute - plugin may be missing.\n";
            continue;
        }
    }
    return true;
}

namespace {

enum class QuoteType { none, singleQuoted, doubleQuoted };

inline bool quoted(QuoteType qt) { return qt != QuoteType::none; }

inline QuoteType getQuoteType(const string &s) {
    if (s.front() == '\'' && s.back() == '\'') {
        return QuoteType::singleQuoted;
    } else if (s.front() == '"' && s.back() == '"') {
        return QuoteType::doubleQuoted;
    } else {
        return QuoteType::none;
    }
}

void removeQuotes(string &s, QuoteType qt) {
    if (quoted(qt)) {
        s = s.substr(1, s.size() - 2);
    }
}

void wrapInQuotes(string &s, QuoteType qt) {
    if (quoted(qt)) {
        char quote = (qt == QuoteType::singleQuoted) ? '\'' : '"';
        s.reserve(s.size() + 2);
        s.insert(0, 1, quote);
        s.push_back(quote);
    }
}

void normalizeCommand(string &cmd) {
    if (isPathRelative(cmd)) {
        Environment *env = Environment::instance();
        if (env == nullptr) {
            throw StringConversionError("No environment");
        }
        ltrim(cmd);
        rtrim(cmd);
        auto quoteType = getQuoteType(cmd);
        removeQuotes(cmd, quoteType);
        cmd.insert(0, env->agentDirectory() + "\\");
        wrapInQuotes(cmd, quoteType);
    }
}

}  // namespace

template <>
mrpe_entry from_string<mrpe_entry>(const WinApiInterface &,
                                   const string &value) {
    vector<string> tokens = tokenizePossiblyQuoted(value);

    if (tokens.size() < 2) {
        throw StringConversionError(
            "Invalid command specification for mrpe:\r\n"
            "Format: SERVICEDESC COMMANDLINE");
    }

    auto plugin_name = tokens[1];  // Intentional copy
    // compute plugin name, drop directory part
    removeQuotes(plugin_name, getQuoteType(plugin_name));

    for (const auto &delimiter : {"/", "\\"}) {
        auto pos = plugin_name.find_last_of(delimiter);
        if (pos != string::npos) {
            plugin_name = plugin_name.substr(pos + 1);
            break;
        }
    }

    string command_line =
        join(std::next(tokens.cbegin(), 2), tokens.cend(), " ");
    auto &cmd = tokens[1];
    normalizeCommand(cmd);

    if (command_line.empty()) {
        command_line = cmd;
    } else {
        command_line.insert(0, cmd + " ");
    }

    auto &service_description = tokens[0];
    removeQuotes(service_description, getQuoteType(service_description));

    return {"", command_line, plugin_name, service_description};
}
