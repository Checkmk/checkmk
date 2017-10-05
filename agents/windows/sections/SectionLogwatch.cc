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

#include "SectionLogwatch.h"
#include <cassert>
#include <regex>
#include "../Environment.h"
#include "../Logger.h"
#include "../types.h"
#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include "../WinApiAdaptor.h"

static const size_t UNICODE_BUFFER_SIZE = 8192;

SectionLogwatch::SectionLogwatch(Configuration &config, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("logwatch", "logfiles", config.getEnvironment(), logger, winapi)
    , _globlines(config, "logfiles", winapi) {
    _globlines.setGroupFunction(&SectionLogwatch::addConditionPattern);

    loadLogwatchOffsets();
}

SectionLogwatch::~SectionLogwatch() { cleanup(); }

void SectionLogwatch::init() {
    for (const auto &globline : *_globlines) {
        for (const auto &token : globline->tokens) {
            processGlobExpression(token, globline->patterns);
        }
    }
}

// Remove missing files from list
void SectionLogwatch::cleanupTextfiles() {
    // remove_if puts the missing textfiles to the end of the list, it doesn't
    // actually remove anything
    auto first_missing =
        std::remove_if(_textfiles.begin(), _textfiles.end(),
                       [](logwatch_textfile *file) { return file->missing; });

    for (auto iter = first_missing; iter != _textfiles.end(); ++iter) {
        delete *iter;
    }

    _textfiles.erase(first_missing, _textfiles.end());
}

// Called on program exit
void SectionLogwatch::cleanup() {
    for (logwatch_textfile *textfile : _textfiles) {
        delete textfile;
    }
    _textfiles.clear();
    for (logwatch_textfile *hint : _hints) {
        delete hint;
    }
    _hints.clear();

    // cleanup globlines and textpatterns
    for (globline_container *cont : *_globlines) {
        for (auto tok : cont->tokens) {
            free(tok->pattern);
            delete (tok);
        }
        cont->tokens.clear();

        for (auto pat : cont->patterns) {
            free(pat->glob_pattern);
            delete (pat);
        }
        cont->patterns.clear();
        delete cont;
    }
}

void SectionLogwatch::addConditionPattern(globline_container *&globline,
                                          const char *state,
                                          const char *value) {
    condition_pattern *new_pattern = new condition_pattern();
    new_pattern->state = std::toupper(state[0]);
    new_pattern->glob_pattern = strdup(value);
    globline->patterns.push_back(new_pattern);
}

std::vector<SectionLogwatch::FileEntryType> SectionLogwatch::globMatches(
    const char *pattern) {
    std::vector<FileEntryType> matches;

    std::string path;
    const char *end = strrchr(pattern, '\\');

    if (end != nullptr) {
        path = std::string(static_cast<const char *>(pattern), end + 1);
    }

    WIN32_FIND_DATA data;
    HANDLE h = _winapi.FindFirstFileEx(pattern, FindExInfoStandard, &data,
                                       FindExSearchNameMatch, nullptr, 0);

    bool more = h != INVALID_HANDLE_VALUE;

    while (more) {
        if (!(data.dwFileAttributes &
              FILE_ATTRIBUTE_DIRECTORY))  // Skip directories
            matches.push_back(
                std::make_pair(path + data.cFileName, data.ftLastWriteTime));
        more = _winapi.FindNextFile(h, &data);
    }
    _winapi.FindClose(h);

    return matches;
}

logwatch_textfile *SectionLogwatch::getLogwatchTextfile(const char *name) {
    for (logwatch_textfile *textfile : _textfiles) {
        if (strcmp(name, textfile->name.c_str()) == 0) return textfile;
    }
    return nullptr;
}

// Check if the given full_filename already exists. If so, do some basic file
// integrity checks
// Otherwise create a new textfile instance
void SectionLogwatch::updateOrCreateLogwatchTextfile(
    const char *full_filename, glob_token *token,
    condition_patterns_t &patterns) {
    logwatch_textfile *textfile = getLogwatchTextfile(full_filename);
    if (textfile == nullptr)
        textfile = addNewLogwatchTextfile(full_filename, token, patterns);
    updateLogwatchTextfile(textfile);
}

void SectionLogwatch::updateOrCreateRotatedLogfile(
    const std::vector<std::string> &filenames, glob_token *token,
    condition_patterns_t &patterns) {
    assert(filenames.size() > 0);

    logwatch_textfile *textfile = getLogwatchTextfile(token->pattern);

    if (textfile == nullptr)
        textfile =
            addNewRotatedLogfile(token->pattern, filenames, token, patterns);
    updateRotatedLogfile(token->pattern, textfile);
}

// Process a single expression (token) of a globline and try to find matching
// files
void SectionLogwatch::processGlobExpression(glob_token *glob_token,
                                            condition_patterns_t &patterns) {
    std::vector<FileEntryType> matches = globMatches(glob_token->pattern);
    glob_token->found_match = !matches.empty();

    if (glob_token->rotated) {
        // rotated: all matches are assumed to belong to the same log.
        // If the file most recently read has been consumed we need to read
        // the next file. This sorting defines what is considered
        // "next"
        if (matches.size() > 0) {
            updateOrCreateRotatedLogfile(sortedByTime(matches), glob_token,
                                         patterns);
        } else {
            Notice(_logger)
                << "pattern " << glob_token->pattern << " matches no files";
        }
    } else {
        // non-rotated: each match is a separate log
        for (const FileEntryType &ent : matches) {
            updateOrCreateLogwatchTextfile(ent.first.c_str(), glob_token,
                                           patterns);
        }
    }
}

void SectionLogwatch::saveOffsets(const std::string &logwatch_statefile) {
    FILE *file = fopen(logwatch_statefile.c_str(), "w");
    if (!file) {
        const auto saveErrno = errno;
        Error(_logger) << "Cannot open " << logwatch_statefile
                       << " for writing: " << strerror(saveErrno) << " ("
                       << saveErrno << ").";
        // not stopping the agent from crashing. This way the user at least
        // notices something went wrong.
        // FIXME: unless there aren't any textfiles configured to be monitored
    }
    for (logwatch_textfile *tf : _textfiles) {
        if (!tf->missing) {
            fprintf(file, "%s|%" PRIu64 "|%" PRIu64 "|%" PRIu64 "\r\n",
                    tf->name.c_str(), tf->file_id, tf->file_size, tf->offset);
        }
    }
    if (file != NULL) {
        fclose(file);
    }
}

// Process content of the given textfile
// Can be called in dry-run mode (write_output = false). This tries to detect
// CRIT or WARN patterns
// If write_output is set to true any data found is written to the out socket
int fill_unicode_bytebuffer(FILE *file, char *buffer, int offset) {
    int bytes_to_read = UNICODE_BUFFER_SIZE - offset;
    int read_bytes = fread(buffer + offset, 1, bytes_to_read, file);
    return read_bytes + offset;
}

int find_crnl_end(char *buffer) {
    for (size_t index = 0; index < UNICODE_BUFFER_SIZE; index += 2) {
        if (buffer[index] == 0x0d && index < UNICODE_BUFFER_SIZE - 2 &&
            buffer[index + 2] == 0x0a)
            return index + 4;
    }
    return -1;
}

SectionLogwatch::ProcessTextfileResponse
SectionLogwatch::processTextfileUnicode(FILE *file, logwatch_textfile *textfile,
                                        std::ostream &out, bool write_output) {
    Notice(_logger) << "Checking UNICODE file " << textfile->paths.front();
    ProcessTextfileResponse response;
    char unicode_block[UNICODE_BUFFER_SIZE];

    condition_pattern *pattern = 0;
    int buffer_level = 0;     // Current bytes in buffer
    bool cut_line = false;    // Line does not fit in buffer
    int crnl_end_offset = 0;  // Byte index of CRLF in unicode block
    int old_buffer_level = 0;

    memset(unicode_block, 0, UNICODE_BUFFER_SIZE);

    while (true) {
        // Only fill buffer if there is no CRNL present
        if (find_crnl_end(unicode_block) == -1) {
            old_buffer_level = buffer_level;
            buffer_level =
                fill_unicode_bytebuffer(file, unicode_block, buffer_level);

            if (old_buffer_level == buffer_level)
                break;  // Nothing new, file finished
        }

        crnl_end_offset = find_crnl_end(unicode_block);
        if (crnl_end_offset == -1) {
            if (buffer_level == UNICODE_BUFFER_SIZE)
                // This line is too long, only report up to the buffers size
                cut_line = true;
            else
                // Missing CRNL... this line is not finished yet
                continue;
        }
        const size_t buffer_size = cut_line ? (UNICODE_BUFFER_SIZE - 2) / 2
                                            : (crnl_end_offset - 4) / 2;
        std::wstring unicode_wstr(reinterpret_cast<wchar_t *>(unicode_block));
        // Argh! The wstring needs to be cut at CRLF as it may go on beyond that
        unicode_wstr.resize(buffer_size);
        std::string output_buffer = to_utf8(unicode_wstr);
        Debug(_logger)
            << "SectionLogwatch::processTextfileUnicode, output_buffer: "
            << output_buffer;
        // Check line
        char state = '.';
        for (condition_patterns_t::iterator it_patt =
                 textfile->patterns->begin();
             it_patt != textfile->patterns->end(); it_patt++) {
            pattern = *it_patt;
            Debug(_logger) << "glob_pattern: " << pattern->glob_pattern
                           << ", state: " << pattern->state;
            if (globmatch(pattern->glob_pattern, output_buffer.c_str())) {
                if (!write_output &&
                    (pattern->state == 'C' || pattern->state == 'W' ||
                     pattern->state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = buffer_level;
                    return response;
                }
                state = pattern->state;
                break;
            }
        }

        // Output line
        if (write_output && !output_buffer.empty()) {
            out << state << " " << output_buffer << "\n";
        }

        if (cut_line) {
            cut_line = false;
            buffer_level = 2;
            while (crnl_end_offset == -1) {
                memcpy(unicode_block, unicode_block + UNICODE_BUFFER_SIZE - 2,
                       2);
                memset(unicode_block + 2, 0, UNICODE_BUFFER_SIZE - 2);
                old_buffer_level = buffer_level;
                buffer_level = fill_unicode_bytebuffer(file, unicode_block, 2);
                if (old_buffer_level == buffer_level)
                    // Nothing new, file finished
                    break;
                crnl_end_offset = find_crnl_end(unicode_block);
            }
        }

        if (crnl_end_offset > 0) {
            buffer_level = buffer_level - crnl_end_offset;
            memmove(unicode_block, unicode_block + crnl_end_offset,
                    buffer_level);
            memset(unicode_block + buffer_level, 0,
                   UNICODE_BUFFER_SIZE - buffer_level);
        }
    }

    response.found_match = false;
    response.unprocessed_bytes = buffer_level;
    return response;
}

SectionLogwatch::ProcessTextfileResponse
SectionLogwatch::processTextfileDefault(FILE *file, logwatch_textfile *textfile,
                                        std::ostream &out, bool write_output) {
    char line[4096];
    ProcessTextfileResponse response;
    Notice(_logger) << "Checking file " << textfile->paths.front();

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)) break;

        if (line[strlen(line) - 1] == '\n') line[strlen(line) - 1] = 0;

        char state = '.';
        for (condition_pattern *pattern : *textfile->patterns) {
            if (globmatch(pattern->glob_pattern, line)) {
                if (!write_output &&
                    (pattern->state == 'C' || pattern->state == 'W' ||
                     pattern->state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = 0;
                    return response;
                }
                state = pattern->state;
                break;
            }
        }

        if (write_output && strlen(line) > 0 &&
            !(textfile->nocontext && (state == 'I' || state == '.')))
            out << state << " " << line << "\n";
    }

    response.found_match = false;
    response.unprocessed_bytes = 0;
    return response;
}

file_encoding determine_encoding(logwatch_textfile *textfile) {
    // Determine Encoding
    FILE *file = fopen(textfile->paths.front().c_str(), "rb");
    if (!file) {
        return UNDEF;
    }

    OnScopeExit auto_close([file]() { fclose(file); });

    char bytes[2];
    int read_bytes = fread(bytes, 1, sizeof(bytes), file);

    if ((read_bytes == sizeof(bytes)) &&
        static_cast<unsigned char>(bytes[0]) == 0xFF &&
        static_cast<unsigned char>(bytes[1]) == 0xFE)
        return UNICODE;
    else
        return DEFAULT;
}

FILE *open_logfile(logwatch_textfile *textfile) {
    FILE *result = nullptr;

    if ((textfile->encoding == UNDEF) || (textfile->offset == 0)) {
        textfile->encoding = determine_encoding(textfile);
    }

    if (textfile->encoding != UNDEF) {
        if (textfile->encoding == UNICODE)
            result = fopen(textfile->paths.front().c_str(), "rb");
        else
            result = fopen(textfile->paths.front().c_str(), "r");
    }

    return result;
}

uint64_t logfile_offset(logwatch_textfile *textfile) {
    uint64_t offset = textfile->offset;
    if ((offset == 0) && (textfile->encoding == UNICODE)) {
        offset = 2;
    }
    return offset;
}

SectionLogwatch::ProcessTextfileResponse SectionLogwatch::processTextfile(
    FILE *file, logwatch_textfile *textfile, std::ostream &out,
    bool write_output) {
    fseek(file, logfile_offset(textfile), SEEK_SET);
    if (textfile->encoding == UNICODE)
        return processTextfileUnicode(file, textfile, out, write_output);
    else
        return processTextfileDefault(file, textfile, out, write_output);
}

void SectionLogwatch::processTextfile(std::ostream &out,
                                      logwatch_textfile *textfile) {
    if (textfile->missing) {
        out << "[[[" << textfile->name << ":missing]]]\n";
        return;
    }

    // Start processing file
    FILE *file = open_logfile(textfile);

    if (!file) {
        out << "[[[" << textfile->name << ":cannotopen]]]\n";
        return;
    }
    OnScopeExit auto_close([file]() { fclose(file); });

    out << "[[[" << replaceAll(textfile->name, "*", "__all__") << "]]]\n";
    if (textfile->offset == textfile->file_size) {  // no new data
        return;
    }

    // determine if there is anything important enough to report
    ProcessTextfileResponse response =
        processTextfile(file, textfile, out, false);
    if (response.found_match) {
        // actually report things
        response = processTextfile(file, textfile, out, true);
    }

    textfile->offset = textfile->file_size - response.unprocessed_bytes;
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
bool SectionLogwatch::produceOutputInner(std::ostream &out) {
    // First of all invalidate all textfiles
    for (logwatch_textfile *textfile : _textfiles) {
        textfile->missing = true;
    }
    init();

    // Missing glob patterns
    for (const globline_container *cont : *_globlines) {
        for (const glob_token *token : cont->tokens) {
            if (!token->found_match) {
                out << "[[[" << token->pattern << ":missing]]]\n";
            }
        }
    }
    // found files
    for (logwatch_textfile *textfile : _textfiles) {
        // for rotated log, this list may contain entries where the pattern
        // currently matches nothing
        if (!textfile->paths.empty()) {
            processTextfile(out, textfile);
        }
    }

    cleanupTextfiles();
    saveOffsets(_env.logwatchStatefile());
    return true;
}

bool SectionLogwatch::getFileInformation(const char *filename,
                                         BY_HANDLE_FILE_INFORMATION *info) {
    HANDLE hFile = _winapi.CreateFile(
        filename,      // file to open
        GENERIC_READ,  // open for reading
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr,                // default security
        OPEN_EXISTING,          // existing file only
        FILE_ATTRIBUTE_NORMAL,  // normal file
        nullptr);               // no attr. template

    if (hFile == INVALID_HANDLE_VALUE) {
        return false;
    }

    bool res = _winapi.GetFileInformationByHandle(hFile, info);
    _winapi.CloseHandle(hFile);
    return res;
}

std::vector<std::string> SectionLogwatch::sortedByTime(
    const std::vector<FileEntryType> &entries) {
    std::vector<FileEntryType> sorted(entries);
    std::sort(sorted.begin(), sorted.end(),
              [&](const FileEntryType &lhs, const FileEntryType &rhs) {
                  return _winapi.CompareFileTime(&lhs.second, &rhs.second) < 0;
              });
    std::vector<std::string> result;
    for (const FileEntryType &ent : sorted) {
        result.push_back(ent.first);
    }
    return result;
}

void SectionLogwatch::updateLogwatchTextfile(logwatch_textfile *textfile) {
    BY_HANDLE_FILE_INFORMATION fileinfo;
    if (!getFileInformation(textfile->paths.front().c_str(), &fileinfo)) {
        Notice(_logger) << "Cant open file with CreateFile "
                        << textfile->paths.front();
        return;
    }

    // Do some basic checks to ensure its still the same file
    // try to fill the structure with info regarding the file
    uint64_t file_id = to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
    textfile->file_size = to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);

    if (file_id != textfile->file_id) {  // file has been changed
        Notice(_logger) << "File " << textfile->paths.front()
                        << ": id has changed from " << textfile->file_id
                        << " to " << file_id;
        textfile->offset = 0;
        textfile->file_id = file_id;
    } else if (textfile->file_size <
               textfile->offset) {  // file has been truncated
        Notice(_logger) << "File " << textfile->paths.front()
                        << ": file has been truncated";
        textfile->offset = 0;
    }

    textfile->missing = false;
}

bool SectionLogwatch::updateFromHint(const char *file_name,
                                     logwatch_textfile *textfile) {
    for (logwatch_textfile *hint : _hints) {
        if (hint->paths.front() == file_name) {
            textfile->file_size = hint->file_size;
            textfile->file_id = hint->file_id;
            textfile->offset = hint->offset;
            return true;
        }
    }
    return false;
}

// Add a new textfile to the global textfile list
// and determine some initial values
logwatch_textfile *SectionLogwatch::addNewLogwatchTextfile(
    const char *full_filename, glob_token *token,
    condition_patterns_t &patterns) {
    BY_HANDLE_FILE_INFORMATION fileinfo;
    if (!getFileInformation(full_filename, &fileinfo)) {
        Debug(_logger) << "failed to open " << full_filename;
        return nullptr;
    }

    logwatch_textfile *new_textfile = new logwatch_textfile();
    new_textfile->name = full_filename;
    new_textfile->paths.push_back(full_filename);
    new_textfile->missing = false;
    new_textfile->patterns = &patterns;
    new_textfile->nocontext = token->nocontext;

    bool found_hint = updateFromHint(full_filename, new_textfile);

    // previously the file size was taken from the hint file. Why is the file
    // size stored with the hint???
    if (!found_hint) {
        new_textfile->file_size =
            to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);
        new_textfile->file_id =
            to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);

        if (!token->from_start) new_textfile->offset = new_textfile->file_size;
    }

    _textfiles.push_back(new_textfile);
    return new_textfile;
}

bool SectionLogwatch::updateCurrentRotatedTextfile(
    logwatch_textfile *textfile) {
    const std::string &current_file = textfile->paths.front();

    BY_HANDLE_FILE_INFORMATION fileinfo;
    if (!getFileInformation(current_file.c_str(), &fileinfo)) {
        Debug(_logger) << "Can't retrieve file info " << current_file;
        return false;
    }

    uint64_t file_id = to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
    textfile->file_size = to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);

    if (textfile->file_id != file_id) {
        // the oldest file we know is "newer" than the one read last.
        Debug(_logger) << "File " << current_file << " rotated";
        textfile->offset = 0;
        textfile->file_id = file_id;
        return true;
    } else if (textfile->file_size < textfile->offset) {
        // this shouldn't happen on a rotated log
        Debug(_logger) << "File " << current_file << " truncated";
        textfile->offset = 0;
        return true;
    } else if ((textfile->offset == textfile->file_size) &&
               (textfile->paths.size() > 1)) {
        // we read to the end of the file and there are newer files.
        // This means this file is finished and will not be written to anymore.
        return false;
    } else {
        // either there is more data in this file or there is no newer
        // file (yet).
        return true;
    }
}

// erase all files from the specified list that are older than the one
// with the specified file_id. This assumes that the file_names list is
// already sorted by file age
void SectionLogwatch::eraseFilesOlder(std::vector<std::string> &file_names,
                                      uint64_t file_id) {
    auto iter = file_names.begin();
    for (; iter != file_names.end(); ++iter) {
        BY_HANDLE_FILE_INFORMATION fileinfo;
        if (getFileInformation(iter->c_str(), &fileinfo) &&
            (file_id ==
             to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh))) {
            // great, found  the right file. all older files were probably
            // processed before
            break;
        }
    }

    if (iter == file_names.end()) {
        // file index not found. Have to assume all
        // files available now are new
        iter = file_names.begin();
    }

    file_names.erase(file_names.begin(), iter);
}

void SectionLogwatch::updateRotatedLogfile(const char *pattern,
                                           logwatch_textfile *textfile) {
    textfile->paths = sortedByTime(globMatches(pattern));
    eraseFilesOlder(textfile->paths, textfile->file_id);

    // find the file to read from
    while ((textfile->paths.size() > 0) &&
           !updateCurrentRotatedTextfile(textfile)) {
        textfile->paths.erase(textfile->paths.begin());
        textfile->offset = 0;
    }

    textfile->missing = textfile->paths.size() == 0;
}

logwatch_textfile *SectionLogwatch::addNewRotatedLogfile(
    const char *pattern, const std::vector<std::string> &filenames,
    glob_token *token, condition_patterns_t &patterns) {
    assert(filenames.size() > 0);

    logwatch_textfile *textfile = new logwatch_textfile();
    textfile->name = token->pattern;
    textfile->paths = filenames;
    textfile->missing = false;
    textfile->patterns = &patterns;
    textfile->nocontext = token->nocontext;

    auto hint_iter = std::find_if(
        _hints.begin(), _hints.end(),
        [pattern](logwatch_textfile *hint) { return hint->name == pattern; });
    if (hint_iter != _hints.end()) {
        logwatch_textfile *hint = *hint_iter;
        // ok, there is a hint. find the file we stopped reading before
        // by its index
        eraseFilesOlder(textfile->paths, hint->file_id);
        textfile->file_size = hint->file_size;
        textfile->file_id = hint->file_id;
        textfile->offset = hint->offset;
    } else {
        if (!token->from_start) {
            // keep only the newest file and start reading at the end of it
            textfile->paths.erase(textfile->paths.begin(),
                                  textfile->paths.end() - 1);
        }

        BY_HANDLE_FILE_INFORMATION fileinfo;
        if (textfile->paths.size() > 0) {
            getFileInformation(textfile->paths.front().c_str(), &fileinfo);
            textfile->file_size =
                to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);
            textfile->file_id =
                to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
            textfile->offset = token->from_start ? 0 : textfile->file_size;
        } else {
            textfile->file_size = textfile->offset = textfile->file_id = 0;
        }
    }

    _textfiles.push_back(textfile);
    return textfile;
}

void SectionLogwatch::parseLogwatchStateLine(char *line) {
    /* Example: line = "M://log1.log|98374598374|0|16"; */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;

    char *token = strtok(p, "|");
    if (!token) return;  // Ignore invalid lines
    unsigned long long file_id = std::strtoull(token, NULL, 10);

    token = strtok(NULL, "|");
    if (!token) return;
    unsigned long long file_size = std::strtoull(token, NULL, 10);

    token = strtok(NULL, "|");
    if (!token) return;
    unsigned long long offset = std::strtoull(token, NULL, 10);

    logwatch_textfile *tf = new logwatch_textfile();
    tf->name = std::string(path);
    tf->paths.push_back(tf->name);
    tf->file_id = file_id;
    tf->file_size = file_size;
    tf->offset = offset;
    tf->missing = false;
    tf->patterns = 0;
    _hints.push_back(tf);
}

void SectionLogwatch::loadLogwatchOffsets() {
    static bool offsets_loaded = false;
    if (!offsets_loaded) {
        FILE *file = fopen(_env.logwatchStatefile().c_str(), "r");
        if (file) {
            char line[256];
            while (NULL != fgets(line, sizeof(line), file)) {
                parseLogwatchStateLine(line);
            }
            fclose(file);
        }
        offsets_loaded = true;
    }
}

// Add a new globline from the config file:
// C:/Testfile | D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by
// process_glob_expression
template <>
globline_container *from_string<globline_container *>(
    const WinApiAdaptor &, const std::string &value) {
    // Each globline receives its own pattern container
    // In case new files matching the glob pattern are we
    // we already have all state,regex patterns available
    globline_container *new_globline = new globline_container();

    // Split globline into tokens
    std::regex split_exp("[^|]+");
    std::string copy(value);
    std::regex_token_iterator<std::string::iterator> iter(
        copy.begin(), copy.end(), split_exp),
        end;

    for (; iter != end; ++iter) {
        std::string descriptor = iter->str();
        const char *token = lstrip(descriptor.c_str());
        glob_token *new_token = new glob_token();

        while (true) {
            if (strncmp(token, "nocontext", 9) == 0) {
                new_token->nocontext = true;
                token = lstrip(token + 9);
            } else if (strncmp(token, "from_start", 10) == 0) {
                new_token->from_start = true;
                token = lstrip(token + 10);
            } else if (strncmp(token, "rotated", 7) == 0) {
                new_token->rotated = true;
                token = lstrip(token + 7);
            } else {
                break;
            }
        }

        new_token->pattern = strdup(token);
        new_globline->tokens.push_back(new_token);
    }
    return new_globline;
}
