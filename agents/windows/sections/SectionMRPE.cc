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
#include "../Environment.h"
#include "../ExternalCmd.h"
#include "../LoggerAdaptor.h"

SectionMRPE::SectionMRPE(Configuration &config, LoggerAdaptor &logger)
    : Section("mrpe", config.getEnvironment(), logger)
    , _entries(config, "mrpe", "check")
    , _includes(config, "mrpe", "include") {}

void SectionMRPE::updateIncludes() {
    for (unsigned int i = 0; i < _included_entries.size(); ++i)
        delete _included_entries[i];
    _included_entries.clear();

    FILE *file;
    char line[512];
    int lineno = 0;
    for (const auto &user_path : *_includes) {
        std::string user, path;
        std::tie(user, path) = user_path;
        file = fopen(path.c_str(), "r");
        if (!file) {
           _logger.crashLog("Include file not found %s", path.c_str());
            continue;
        }

        lineno = 0;
        while (!feof(file)) {
            lineno++;
            if (!fgets(line, sizeof(line), file)) {
                printf("intern clse\n");
                fclose(file);
                continue;
            }

            char *l = strip(line);
            if (l[0] == 0 || l[0] == '#' || l[0] == ';')
                continue;  // skip empty lines and comments

            // split up line at = sign
            char *s = l;
            while (*s && *s != '=') s++;
            if (*s != '=') {
               _logger.crashLog("Invalid line %d in %s.", lineno, path.c_str());
                continue;
            }
            *s = 0;
            char *value = s + 1;
            char *var = l;
            rstrip(var);
            lowercase(var);
            value = strip(value);

            if (!strcmp(var, "check")) {
                // First word: service description
                // Rest: command line
                char *service_description = next_word(&value);
                char *command_line = value;
                if (!command_line || !command_line[0]) {
                   _logger.crashLog(
                        "Invalid line %d in %s. Invalid command specification",
                        lineno, path.c_str());
                    continue;
                }

                mrpe_entry *tmp_entry = new mrpe_entry();
                memset(tmp_entry, 0, sizeof(mrpe_entry));

                strncpy(tmp_entry->command_line, command_line,
                        sizeof(tmp_entry->command_line));
                strncpy(tmp_entry->service_description, service_description,
                        sizeof(tmp_entry->service_description));

                // compute plugin name, drop directory part
                char *plugin_name = next_word(&value);
                char *p = strrchr(plugin_name, '/');
                if (!p) p = strrchr(plugin_name, '\\');
                if (p) plugin_name = p + 1;
                strncpy(tmp_entry->plugin_name, plugin_name,
                        sizeof(tmp_entry->plugin_name));
                strncpy(tmp_entry->run_as_user, user.c_str(),
                        sizeof(tmp_entry->run_as_user));
                _included_entries.push_back(tmp_entry);
            }
        }
        fclose(file);
    }
}

bool SectionMRPE::produceOutputInner(std::ostream &out) {
    updateIncludes();

    mrpe_entries_t all_entries;
    all_entries.insert(all_entries.end(), _entries->begin(), _entries->end());
    all_entries.insert(all_entries.end(), _included_entries.begin(),
                       _included_entries.end());
    
    for (mrpe_entry *entry : all_entries) {
        out << "(" << entry->plugin_name << ") " << entry->service_description << " ";
       _logger.crashLog("%s (%s) %s ", entry->run_as_user, entry->plugin_name,
                  entry->service_description);

        char modified_command[1024];
        char run_as_prefix[512];
        memset(run_as_prefix, 0, sizeof(run_as_prefix));
        if (strlen(entry->run_as_user) > 0)
            snprintf(run_as_prefix, sizeof(run_as_prefix), "runas /User:%s ",
                     entry->run_as_user);
        snprintf(modified_command, sizeof(modified_command), "%s%s", run_as_prefix,
                 entry->command_line);

        try {
            ExternalCmd command(modified_command, _logger);
           _logger.crashLog("Script started -> collecting data");
            std::string buffer;
            buffer.resize(8192);
            char *buf_start = &buffer[0];
            char *pos = &buffer[0];
            while (command.exitCode() == STILL_ACTIVE) {
                DWORD read = command.readStdout(
                    pos, buffer.size() - (pos - buf_start), false);
                pos += read;
                Sleep(10);
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
           _logger.crashLog("Script finished");
        } catch (const std::exception &e) {
           _logger.crashLog("mrpe failed: %s", e.what());
            out << "3 Unable to execute - plugin may be missing.\n";
            continue;
        }
    }
    return true;
}

