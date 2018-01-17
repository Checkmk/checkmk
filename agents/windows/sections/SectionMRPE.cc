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

SectionMRPE::SectionMRPE(Configuration &config, Logger *logger,
                         const WinApiAdaptor &winapi)
    : Section("mrpe", "mrpe", config.getEnvironment(), logger, winapi)
    , _entries(config, "mrpe", "check", winapi)
    , _includes(config, "mrpe", "include", winapi) {}

void SectionMRPE::updateIncludes() {
    _included_entries.clear();

    for (const auto &user_path : *_includes) {
        std::string user, path;
        std::tie(user, path) = user_path;
        std::ifstream ifs(path);
        if (!ifs) {
            Warning(_logger) << "Include file not found " << path;
            continue;
        }

        std::string line;
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

bool SectionMRPE::produceOutputInner(std::ostream &out) {
    Debug(_logger) << "SectionMRPE::produceOutputInner";
    updateIncludes();

    mrpe_entries_t all_entries;
    all_entries.insert(all_entries.end(), _entries->begin(), _entries->end());
    all_entries.insert(all_entries.end(), _included_entries.begin(),
                       _included_entries.end());

    for (const auto &entry : all_entries) {
        out << entry << " ";
        Debug(_logger) << entry.run_as_user << " " << entry;

        std::string run_as_prefix;

        if (!entry.run_as_user.empty()) {
            run_as_prefix = "runas /User:" + entry.run_as_user + " ";
        }
        std::string modified_command = run_as_prefix + entry.command_line;

        try {
            ExternalCmd command(modified_command, _env, _logger, _winapi);
            Debug(_logger) << "Script started -> collecting data";
            std::string buffer;
            buffer.resize(8192);
            char *buf_start = &buffer[0];
            char *pos = &buffer[0];
            while (command.exitCode() == STILL_ACTIVE) {
                DWORD read = command.readStdout(
                    pos, buffer.size() - (pos - buf_start), false);
                pos += read;
                _winapi.Sleep(10);
            }
            command.readStdout(pos, buffer.size() - (pos - buf_start), false);

            char *output_end = rstrip(&buffer[0]);
            char *plugin_output = lstrip(&buffer[0]);
            // replace newlines
            std::transform(plugin_output, output_end, plugin_output,
                           [](char ch) {
                               if (ch == '\n') return '\1';
                               if (ch == '\r')
                                   return ' ';
                               else
                                   return ch;
                           });
            int nagios_code = command.exitCode();
            out << nagios_code << " " << plugin_output << "\n";
            Debug(_logger) << "Script finished";
        } catch (const std::exception &e) {
            Error(_logger) << "mrpe failed: " << e.what();
            out << "3 Unable to execute - plugin may be missing.\n";
            continue;
        }
    }
    return true;
}

template <>
mrpe_entry from_string<mrpe_entry>(const WinApiAdaptor &,
                                   const std::string &value) {
    const auto tokens = tokenize(value, " ");
    const std::string &service_description = tokens[0];
    std::string command_line = join(std::next(tokens.cbegin()), tokens.cend(), " ");

    // Strip any " from start and end
    if (!command_line.empty() && command_line.front() == '"') {
        command_line = command_line.substr(1);
    }
    if (!command_line.empty() && command_line.back() == '"') {
        command_line = command_line.substr(0, command_line.length() - 1);
    }

    if (command_line.empty()) {
        throw StringConversionError(
            "Invalid command specification for mrpe:\r\n"
            "Format: SERVICEDESC COMMANDLINE");
    }

    if (isPathRelative(command_line)) {
        Environment *env = Environment::instance();
        if (env == nullptr) {
            throw StringConversionError("No environment");
        }
        ltrim(command_line);
        command_line = env->agentDirectory() + "\\" + command_line;
    }

    // compute plugin name, drop directory part
    std::string plugin_name = tokenize(command_line, " ")[0];
    for (const auto &delimiter : {"/", "\\"}) {
        auto pos = plugin_name.find_last_of(delimiter);
        if (pos != std::string::npos) {
            plugin_name = plugin_name.substr(pos + 1);
            break;
        }
    }

    return {"", command_line, plugin_name, service_description};
}
