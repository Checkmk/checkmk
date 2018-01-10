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
#include <fstream>
#include <regex>
#include "Environment.h"
#include "Logger.h"
#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include "WinApiAdaptor.h"

using std::ifstream;
using std::ofstream;

namespace {

class MissingFile : public std::runtime_error {
public:
    explicit MissingFile(const std::string &what) : std::runtime_error(what) {}
};

const size_t UNICODE_BUFFER_SIZE = 8192;

// Process content of the given textfile
// Can be called in dry-run mode (write_output = false). This tries to detect
// CRIT or WARN patterns
// If write_output is set to true any data found is written to the out socket
inline int fill_unicode_bytebuffer(ifstream &file, char *buffer, int offset) {
    int bytes_to_read = UNICODE_BUFFER_SIZE - offset;
    file.read(buffer + offset, bytes_to_read);
    return file.gcount() + offset;
}

inline int find_crnl_end(char *buffer) {
    for (size_t index = 0; index < UNICODE_BUFFER_SIZE; index += 2) {
        if (buffer[index] == 0x0d && index < UNICODE_BUFFER_SIZE - 2 &&
            buffer[index + 2] == 0x0a)
            return index + 4;
    }
    return -1;
}

file_encoding determine_encoding(const logwatch_textfile &textfile) {
    ifstream ifs(textfile.paths.front(), ifstream::in | ifstream::binary);

    if (ifs.fail()) {
        return UNDEF;
    }

    std::array<char, 2> bytes;

    if (ifs.read(bytes.data(), bytes.size()) &&
        static_cast<unsigned char>(bytes[0]) == 0xFF &&
        static_cast<unsigned char>(bytes[1]) == 0xFE) {
        return UNICODE;
    } else {
        return DEFAULT;
    }
}

ifstream open_logfile(logwatch_textfile &textfile) {
    ifstream result;

    if ((textfile.encoding == UNDEF) || (textfile.offset == 0)) {
        textfile.encoding = determine_encoding(textfile);
    }

    if (textfile.encoding == UNDEF) {
        result.setstate(std::ios_base::badbit);
    } else {
        auto mode = ifstream::in;
        if (textfile.encoding == UNICODE) {
            mode |= ifstream::binary;
        }
        result.open(textfile.paths.front(), mode);
    }

    return result;
}

uint64_t logfile_offset(const logwatch_textfile &textfile) {
    uint64_t offset = textfile.offset;
    if ((offset == 0) && (textfile.encoding == UNICODE)) {
        offset = 2;
    }
    return offset;
}

void addConditionPattern(globline_container &globline, const char *state,
                         const char *value) {
    globline.patterns.emplace_back(std::toupper(state[0]), value);
}

}  // namespace

logwatch_hint parseLogwatchStateLine(const std::string &line) {
    /* Example: line = "M://log1.log|98374598374|0|16"; */
    const auto tokens = tokenize(line, "\\|");

    if (tokens.size() != 4 ||
        std::any_of(tokens.cbegin(), tokens.cend(),
                    [](const std::string &t) { return t.empty(); })) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }

    try {
        return {tokens[0], std::move(std::vector<std::string>{tokens[0]}),
                std::stoull(tokens[1]), std::stoull(tokens[2]),
                std::stoull(tokens[3])};
    } catch (const std::invalid_argument &) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }
}

SectionLogwatch::SectionLogwatch(Configuration &config, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("logwatch", "logfiles", config.getEnvironment(), logger, winapi)
    , _globlines(config, "logfiles", winapi) {
    _globlines.setGroupFunction(&addConditionPattern);
    loadLogwatchOffsets();
}

SectionLogwatch::~SectionLogwatch() {}

void SectionLogwatch::init() {
    for (auto &globline : *_globlines) {
        for (auto &token : globline.tokens) {
            processGlobExpression(token, globline.patterns);
        }
    }
}

// Remove missing files from list
void SectionLogwatch::cleanupTextfiles() {
    // remove_if puts the missing textfiles to the end of the list, it doesn't
    // actually remove anything
    auto first_missing = std::remove_if(
        _textfiles.begin(), _textfiles.end(),
        [](const logwatch_textfile &file) { return file.missing; });

    _textfiles.erase(first_missing, _textfiles.end());
}

std::vector<SectionLogwatch::FileEntryType> SectionLogwatch::globMatches(
    const std::string &pattern) {
    std::vector<FileEntryType> matches;

    std::string path;
    const auto end = pattern.find_last_of('\\');

    if (end != std::string::npos) {
        path = pattern.substr(0, end + 1);
    }

    WIN32_FIND_DATA data;
    SearchHandle searchHandle{
        _winapi.FindFirstFileEx(pattern.c_str(), FindExInfoStandard, &data,
                                FindExSearchNameMatch, nullptr, 0),
        _winapi};

    bool more = bool(searchHandle);

    while (more) {
        if (!(data.dwFileAttributes &
              FILE_ATTRIBUTE_DIRECTORY))  // Skip directories
            matches.push_back(
                std::make_pair(path + data.cFileName, data.ftLastWriteTime));
        more = _winapi.FindNextFile(searchHandle.get(), &data);
    }

    return matches;
}

std::vector<logwatch_textfile>::iterator SectionLogwatch::findLogwatchTextfile(
    const std::string &name) {
    return std::find_if(_textfiles.begin(), _textfiles.end(),
                        [&name](const logwatch_textfile &textfile) {
                            return textfile.name == name;
                        });
}

// Check if the given full_filename already exists. If so, do some basic file
// integrity checks
// Otherwise create a new textfile instance
void SectionLogwatch::updateOrCreateLogwatchTextfile(
    const char *full_filename, const glob_token &token,
    condition_patterns_t &patterns) {
    auto it = findLogwatchTextfile(full_filename);
    auto &textfile =
        (it != _textfiles.end()) ? *it : addNewLogwatchTextfile(
                                             full_filename, token, patterns);
    updateLogwatchTextfile(textfile);
}

void SectionLogwatch::updateOrCreateRotatedLogfile(
    const std::vector<std::string> &filenames, const glob_token &token,
    condition_patterns_t &patterns) {
    assert(filenames.size() > 0);

    auto it = findLogwatchTextfile(token.pattern);
    auto &textfile =
        (it != _textfiles.end())
            ? *it
            : addNewRotatedLogfile(token.pattern, filenames, token, patterns);
    updateRotatedLogfile(token.pattern, textfile);
}

// Process a single expression (token) of a globline and try to find matching
// files
void SectionLogwatch::processGlobExpression(glob_token &glob_token,
                                            condition_patterns_t &patterns) {
    std::vector<FileEntryType> matches =
        globMatches(glob_token.pattern.c_str());
    glob_token.found_match = !matches.empty();

    try {
        if (glob_token.rotated) {
            // rotated: all matches are assumed to belong to the same log.
            // If the file most recently read has been consumed we need to read
            // the next file. This sorting defines what is considered
            // "next"
            if (matches.size() > 0) {
                updateOrCreateRotatedLogfile(sortedByTime(matches), glob_token,
                                             patterns);
            } else {
                Notice(_logger)
                    << "pattern " << glob_token.pattern << " matches no files";
            }
        } else {
            // non-rotated: each match is a separate log
            for (const FileEntryType &ent : matches) {
                updateOrCreateLogwatchTextfile(ent.first.c_str(), glob_token,
                                               patterns);
            }
        }
    } catch (const MissingFile &e) {
        Notice(_logger) << e.what();
    }
}

void SectionLogwatch::saveOffsets(const std::string &logwatch_statefile) {
    ofstream ofs(logwatch_statefile);
    if (ofs.fail()) {
        const auto saveErrno = errno;
        Error(_logger) << "Cannot open " << logwatch_statefile
                       << " for writing: " << strerror(saveErrno) << " ("
                       << saveErrno << ").";
        // not stopping the agent from crashing. This way the user at least
        // notices something went wrong.
        // FIXME: unless there aren't any textfiles configured to be monitored
    }
    for (const auto &tf : _textfiles) {
        if (!tf.missing) {
            ofs << tf.name << "|" << tf.file_id << "|" << tf.file_size << "|"
                << tf.offset << std::endl;
        }
    }
}

SectionLogwatch::ProcessTextfileResponse
SectionLogwatch::processTextfileUnicode(ifstream &file,
                                        const logwatch_textfile &textfile,
                                        std::ostream &out, bool write_output) {
    Notice(_logger) << "Checking UNICODE file " << textfile.paths.front();
    ProcessTextfileResponse response;
    char unicode_block[UNICODE_BUFFER_SIZE];

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
        rtrim(output_buffer);
        Debug(_logger)
            << "SectionLogwatch::processTextfileUnicode, output_buffer: "
            << output_buffer;
        // Check line
        char state = '.';
        for (auto it_patt = textfile.patterns.get().begin();
             it_patt != textfile.patterns.get().end(); it_patt++) {
            const auto &pattern = *it_patt;
            Debug(_logger) << "glob_pattern: " << pattern.glob_pattern
                           << ", state: " << pattern.state;
            if (globmatch(pattern.glob_pattern.c_str(),
                          output_buffer.c_str())) {
                if (!write_output &&
                    (pattern.state == 'C' || pattern.state == 'W' ||
                     pattern.state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = buffer_level;
                    return response;
                }
                state = pattern.state;
                break;
            }
        }

        // Output line
        if (write_output && !output_buffer.empty() &&
            !(textfile.nocontext && (state == 'I' || state == '.'))) {
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
SectionLogwatch::processTextfileDefault(ifstream &file,
                                        const logwatch_textfile &textfile,
                                        std::ostream &out, bool write_output) {
    std::string line;
    ProcessTextfileResponse response;
    Notice(_logger) << "Checking file " << textfile.paths.front();

    while (std::getline(file, line)) {
        rtrim(line);

        char state = '.';
        for (const auto &pattern : textfile.patterns.get()) {
            if (globmatch(pattern.glob_pattern.c_str(), line.c_str())) {
                if (!write_output &&
                    (pattern.state == 'C' || pattern.state == 'W' ||
                     pattern.state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = 0;
                    return response;
                }
                state = pattern.state;
                break;
            }
        }

        if (write_output && !line.empty() &&
            !(textfile.nocontext && (state == 'I' || state == '.')))
            out << state << " " << line << "\n";
    }

    response.found_match = false;
    response.unprocessed_bytes = 0;
    return response;
}

SectionLogwatch::ProcessTextfileResponse SectionLogwatch::processTextfile(
    ifstream &file, const logwatch_textfile &textfile, std::ostream &out,
    bool write_output) {
    // Reset stream state after previous read as we process the files twice.
    // Necessary as reading UTF-16 file sets some fail bit(s) at the end.
    file.clear();
    file.seekg(logfile_offset(textfile));
    if (textfile.encoding == UNICODE)
        return processTextfileUnicode(file, textfile, out, write_output);
    else
        return processTextfileDefault(file, textfile, out, write_output);
}

void SectionLogwatch::processTextfile(std::ostream &out,
                                      logwatch_textfile &textfile) {
    if (textfile.missing) {
        out << "[[[" << textfile.name << ":missing]]]\n";
        return;
    }

    // Start processing file
    ifstream file = open_logfile(textfile);

    if (file.fail()) {
        out << "[[[" << textfile.name << ":cannotopen]]]\n";
        return;
    }

    out << "[[[" << replaceAll(textfile.name, "*", "__all__") << "]]]\n";
    if (textfile.offset == textfile.file_size) {  // no new data
        return;
    }

    // determine if there is anything important enough to report
    ProcessTextfileResponse response =
        processTextfile(file, textfile, out, false);
    if (response.found_match) {
        // actually report things
        response = processTextfile(file, textfile, out, true);
    }

    textfile.offset = textfile.file_size - response.unprocessed_bytes;
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
bool SectionLogwatch::produceOutputInner(std::ostream &out) {
    Debug(_logger) << "SectionLogwatch::produceOutputInner";
    // First of all invalidate all textfiles
    for (auto &textfile : _textfiles) {
        textfile.missing = true;
    }
    init();

    // Missing glob patterns
    for (const auto &cont : *_globlines) {
        for (const auto &token : cont.tokens) {
            if (!token.found_match) {
                out << "[[[" << token.pattern << ":missing]]]\n";
            }
        }
    }
    // found files
    for (auto &textfile : _textfiles) {
        // for rotated log, this list may contain entries where the pattern
        // currently matches nothing
        if (!textfile.paths.empty()) {
            processTextfile(out, textfile);
        }
    }

    cleanupTextfiles();
    saveOffsets(_env.logwatchStatefile());
    return true;
}

bool SectionLogwatch::getFileInformation(const std::string &filename,
                                         BY_HANDLE_FILE_INFORMATION *info) {
    WrappedHandle<InvalidHandleTraits> hFile{
        _winapi.CreateFile(
            filename.c_str(),  // file to open
            GENERIC_READ,      // open for reading
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr,                // default security
            OPEN_EXISTING,          // existing file only
            FILE_ATTRIBUTE_NORMAL,  // normal file
            nullptr),               // no attr. template
        _winapi};

    return hFile ? _winapi.GetFileInformationByHandle(hFile.get(), info)
                 : false;
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

void SectionLogwatch::updateLogwatchTextfile(logwatch_textfile &textfile) {
    BY_HANDLE_FILE_INFORMATION fileinfo{0};
    if (!getFileInformation(textfile.paths.front().c_str(), &fileinfo)) {
        Notice(_logger) << "Cant open file with CreateFile "
                        << textfile.paths.front();
        return;
    }

    // Do some basic checks to ensure its still the same file
    // try to fill the structure with info regarding the file
    uint64_t file_id = to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
    textfile.file_size = to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);

    if (file_id != textfile.file_id) {  // file has been changed
        Notice(_logger) << "File " << textfile.paths.front()
                        << ": id has changed from " << textfile.file_id
                        << " to " << file_id;
        textfile.offset = 0;
        textfile.file_id = file_id;
    } else if (textfile.file_size <
               textfile.offset) {  // file has been truncated
        Notice(_logger) << "File " << textfile.paths.front()
                        << ": file has been truncated";
        textfile.offset = 0;
    }

    textfile.missing = false;
}

// Add a new textfile to the global textfile list
// and determine some initial values
logwatch_textfile &SectionLogwatch::addNewLogwatchTextfile(
    const char *full_filename, const glob_token &token,
    const condition_patterns_t &patterns) {
    BY_HANDLE_FILE_INFORMATION fileinfo;
    if (!getFileInformation(full_filename, &fileinfo)) {
        Debug(_logger) << "failed to open " << full_filename;
        throw MissingFile(std::string("failed to open ") + full_filename);
    }

    const auto cend = _hints.cend();
    const auto it = std::find_if(_hints.cbegin(), cend,
                                 [full_filename](const logwatch_hint &hint) {
                                     return hint.paths.front() == full_filename;
                                 });
    bool found_hint = it != cend;

    // previously the file size was taken from the hint file. Why is the file
    // size stored with the hint???
    unsigned long long file_id =
        found_hint ? it->file_id
                   : to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
    unsigned long long file_size =
        found_hint ? it->file_size
                   : to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);
    unsigned long long offset =
        found_hint ? it->offset : (token.from_start ? 0 : file_size);

    _textfiles.emplace_back(
        full_filename, std::move(std::vector<std::string>{full_filename}),
        file_id, file_size, offset, token.nocontext, false, patterns);
    return _textfiles.back();
}

bool SectionLogwatch::updateCurrentRotatedTextfile(
    logwatch_textfile &textfile) {
    const std::string &current_file = textfile.paths.front();

    BY_HANDLE_FILE_INFORMATION fileinfo{0};
    if (!getFileInformation(current_file.c_str(), &fileinfo)) {
        Debug(_logger) << "Can't retrieve file info " << current_file;
        return false;
    }

    uint64_t file_id = to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
    textfile.file_size = to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);

    if (textfile.file_id != file_id) {
        // the oldest file we know is "newer" than the one read last.
        Debug(_logger) << "File " << current_file << " rotated";
        textfile.offset = 0;
        textfile.file_id = file_id;
        return true;
    } else if (textfile.file_size < textfile.offset) {
        // this shouldn't happen on a rotated log
        Debug(_logger) << "File " << current_file << " truncated";
        textfile.offset = 0;
        return true;
    } else if ((textfile.offset == textfile.file_size) &&
               (textfile.paths.size() > 1)) {
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
        BY_HANDLE_FILE_INFORMATION fileinfo{0};
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

void SectionLogwatch::updateRotatedLogfile(const std::string &pattern,
                                           logwatch_textfile &textfile) {
    textfile.paths = sortedByTime(globMatches(pattern));
    eraseFilesOlder(textfile.paths, textfile.file_id);

    // find the file to read from
    while ((textfile.paths.size() > 0) &&
           !updateCurrentRotatedTextfile(textfile)) {
        textfile.paths.erase(textfile.paths.begin());
        textfile.offset = 0;
    }

    textfile.missing = textfile.paths.size() == 0;
}

logwatch_textfile &SectionLogwatch::addNewRotatedLogfile(
    const std::string &pattern, const std::vector<std::string> &filenames,
    const glob_token &token, condition_patterns_t &patterns) {
    assert(filenames.size() > 0);

    const auto cend = _hints.cend();
    auto hint_iter = std::find_if(
        _hints.cbegin(), _hints.cend(),
        [&pattern](const logwatch_hint &hint) { return hint.name == pattern; });
    bool found_hint = hint_iter != cend;
    std::vector<std::string> paths{filenames};

    if (found_hint) {
        eraseFilesOlder(paths, hint_iter->file_id);
    } else if (!token.from_start) {
        paths.erase(paths.begin(), paths.end() - 1);
    }

    unsigned long long file_id = 0, file_size = 0, offset = 0;

    if (found_hint) {
        file_id = hint_iter->file_id;
        file_size = hint_iter->file_size;
        offset = hint_iter->offset;
    } else {
        if (!paths.empty()) {
            BY_HANDLE_FILE_INFORMATION fileinfo{0};

            if (!getFileInformation(filenames.front(), &fileinfo)) {
                Debug(_logger) << "failed to open " << filenames.front();
                throw MissingFile(
                    std::string("failed to open " + filenames.front()));
            }

            file_id = to_u64(fileinfo.nFileIndexLow, fileinfo.nFileIndexHigh);
            file_size = to_u64(fileinfo.nFileSizeLow, fileinfo.nFileSizeHigh);
            if (!token.from_start) {
                offset = file_size;
            }
        }
    }

    _textfiles.emplace_back(token.pattern, std::move(paths), file_id, file_size,
                            offset, token.nocontext, true, patterns);
    return _textfiles.back();
}

void SectionLogwatch::loadLogwatchOffsets() {
    if (!_offsets_loaded) {
        ifstream ifs(_env.logwatchStatefile());
        if (ifs) {
            std::string line;
            while (std::getline(ifs, line)) {
                rtrim(line);
                _hints.push_back(parseLogwatchStateLine(line));
            }
        }
        _offsets_loaded = true;
    }
}

// Add a new globline from the config file:
// C:/Testfile | D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by
// process_glob_expression
template <>
globline_container from_string<globline_container>(const WinApiAdaptor &,
                                                   const std::string &value) {
    // Each globline receives its own pattern container
    // In case new files matching the glob pattern are we
    // we already have all state,regex patterns available
    glob_tokens_t tokens;

    // Split globline into tokens
    std::regex split_exp("[^|]+");
    std::string copy(value);
    std::regex_token_iterator<std::string::iterator> iter(
        copy.begin(), copy.end(), split_exp),
        end;

    for (; iter != end; ++iter) {
        std::string descriptor = iter->str();
        ltrim(descriptor);
        glob_token new_token;

        for (const auto &token :
             std::vector<std::string>{"nocontext", "from_start", "rotated"}) {
            std::regex tokenRegex("\\b" + token + "\\b");
            if (std::regex_search(descriptor, tokenRegex)) {
                if (token == "nocontext") {
                    new_token.nocontext = true;
                } else if (token == "from_start") {
                    new_token.from_start = true;
                } else if (token == "rotated") {
                    new_token.rotated = true;
                }
                descriptor = std::regex_replace(descriptor, tokenRegex, "");
                ltrim(descriptor);
            }
        }

        new_token.pattern = descriptor;
        tokens.push_back(new_token);
    }

    return {tokens, {}};
}
