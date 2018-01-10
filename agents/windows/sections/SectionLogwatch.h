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

#ifndef SectionLogwatch_h
#define SectionLogwatch_h

#include "Configurable.h"
#include "Section.h"
#include "types.h"

typedef struct _BY_HANDLE_FILE_INFORMATION BY_HANDLE_FILE_INFORMATION;

enum file_encoding {
    UNDEF,
    DEFAULT,
    UNICODE,
};

// Stores the condition pattern together with its state
// Pattern definition within the config file:
//      C = *critpatternglobdescription*
struct condition_pattern {
    condition_pattern(const char state_, const std::string glob_pattern_)
        : state(state_), glob_pattern(glob_pattern_) {}
    char state;
    std::string glob_pattern;
};

using condition_patterns_t = std::vector<condition_pattern>;

// A textfile instance containing information about various file
// parameters and a reference to the matching pattern_container
struct logwatch_textfile {
    logwatch_textfile(const std::string &name_,
                      const std::vector<std::string> &paths_,
                      unsigned long long file_id_,
                      unsigned long long file_size_, unsigned long long offset_,
                      bool nocontext_, bool rotated_,
                      const condition_patterns_t &patterns_)
        : name(name_)
        , paths(paths_)
        , file_id(file_id_)
        , file_size(file_size_)
        , offset(offset_)
        , nocontext(nocontext_)
        , rotated(rotated_)
        , patterns(std::ref(patterns_)) {}
    logwatch_textfile(const logwatch_textfile&) = delete;
    logwatch_textfile &operator=(const logwatch_textfile&) = delete;
    logwatch_textfile(logwatch_textfile&&) = default;
    logwatch_textfile &operator=(logwatch_textfile&&) = default;

    std::string name;  // name used for section headers. this is the
                       // filename for regular logs and the pattern
                       // for rotated logs
    std::vector<std::string> paths;
    unsigned long long file_id;    // used to detect if a file has been replaced
    unsigned long long file_size;  // size of the file
    unsigned long long offset{0};  // current fseek offset in the file
    bool missing{false};           // file no longer exists
    bool nocontext;                // do not report ignored lines
    bool rotated;                  // assume the logfile is a rotating log
    file_encoding encoding{UNDEF};
    std::reference_wrapper<const condition_patterns_t>
        patterns;  // glob patterns applying for this file
};

// Single element of a globline:
// C:/tmp/Testfile*.log
struct glob_token {
    std::string pattern;
    bool nocontext{false};
    bool from_start{false};
    bool rotated{false};
    bool found_match{false};
};

using glob_tokens_t = std::vector<glob_token>;

// Container for all globlines read from the config
// The following is considered a globline
// textfile = C:\Logfile1.txt C:\tmp\Logfile*.txt
struct globline_container {
    glob_tokens_t tokens;
    condition_patterns_t patterns;
};

using GlobListT = std::vector<globline_container>;

template <>
globline_container from_string<globline_container>(const WinApiAdaptor &winapi,
                                                   const std::string &value);

inline std::ostream &operator<<(std::ostream &os, const globline_container &g) {
    os << "\n[tokens]\n";
    for (const auto &token : g.tokens) {
        os << "<pattern: " << token.pattern
           << ", nocontext: " << std::boolalpha << token.nocontext
           << ", from_start: " << token.from_start
           << ", rotated: " << token.rotated
           << ", found_match: " << token.found_match << ">\n";
    }
    os << "[patterns]\n";
    for (const auto &pattern : g.patterns) {
        os << "<state: " << pattern.state
           << ", glob_pattern: " << pattern.glob_pattern << ">\n";
    }
    return os;
}

class GlobListConfigurable
    : public ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                              AddMode::PriorityAppendGrouped<GlobListT>> {
    typedef ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                             AddMode::PriorityAppendGrouped<GlobListT>>
        SuperT;

public:
    GlobListConfigurable(Configuration &config, const char *section,
                         const WinApiAdaptor &winapi)
        : SuperT(config, section, "textfile", winapi) {
        config.reg(section, "warn", this);
        config.reg(section, "crit", this);
        config.reg(section, "ignore", this);
        config.reg(section, "ok", this);
    }

    virtual void feed(const std::string &key,
                      const std::string &value) override {
        if (key == "textfile") {
            SuperT::feed(key, value);
        } else {
            SuperT::feedInner(key, value);
        }
    }
};

logwatch_textfile parseLogwatchStateLine(const std::string &line);

class SectionLogwatch : public Section {
    struct ProcessTextfileResponse {
        bool found_match;
        int unprocessed_bytes;
    };

    typedef std::pair<std::string, FILETIME> FileEntryType;

public:
    SectionLogwatch(Configuration &config, Logger *logger,
                    const WinApiAdaptor &winapi);
    virtual ~SectionLogwatch();

protected:
    virtual bool produceOutputInner(std::ostream &out) override;

private:
    void init();

    void eraseFilesOlder(std::vector<std::string> &file_names,
                         uint64_t file_id);

    void cleanupTextfiles();

    void loadLogwatchOffsets();

    bool getFileInformation(const std::string &filename,
                            BY_HANDLE_FILE_INFORMATION *info);

    void saveOffsets(const std::string &logwatch_statefile);

    std::vector<std::string> sortedByTime(
        const std::vector<FileEntryType> &entries);
    std::vector<logwatch_textfile>::iterator findLogwatchTextfile(
        const std::string &name);

    bool updateCurrentRotatedTextfile(logwatch_textfile &textfile);

    logwatch_textfile &addNewLogwatchTextfile(
        const char *full_filename, const glob_token &token,
        const condition_patterns_t &patterns);

    void updateLogwatchTextfile(logwatch_textfile &textfile);

    void updateRotatedLogfile(const std::string &pattern,
                              logwatch_textfile &textfile);

    logwatch_textfile &addNewRotatedLogfile(
        const std::string &pattern, const std::vector<std::string> &filenames,
        const glob_token &token, condition_patterns_t &patterns);

    void updateOrCreateLogwatchTextfile(const char *full_filename,
                                        const glob_token &token,
                                        condition_patterns_t &patterns);

    void updateOrCreateRotatedLogfile(const std::vector<std::string> &filenames,
                                      const glob_token &token,
                                      condition_patterns_t &patterns);
    std::vector<FileEntryType> globMatches(const std::string &pattern);

    ProcessTextfileResponse processTextfileDefault(
        std::ifstream &file, const logwatch_textfile &textfile,
        std::ostream &out, bool write_output);

    ProcessTextfileResponse processTextfileUnicode(
        std::ifstream &file, const logwatch_textfile &textfile,
        std::ostream &out, bool write_output);

    ProcessTextfileResponse processTextfile(std::ifstream &file,
                                            const logwatch_textfile &textfile,
                                            std::ostream &out,
                                            bool write_output);

    void processTextfile(std::ostream &out, logwatch_textfile &textfile);

    void processGlobExpression(glob_token &glob_token,
                               condition_patterns_t &patterns);

    GlobListConfigurable _globlines;
    std::vector<logwatch_textfile> _textfiles;
    std::vector<logwatch_textfile> _hints;
    bool _offsets_loaded{false};
    bool _initialised{false};
};

#endif  // SectionLogwatch_h
