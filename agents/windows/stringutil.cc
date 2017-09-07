#include "stringutil.h"
#include <cassert>
#include <cctype>
#include <codecvt>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <locale>
#include "WinApiAdaptor.h"

#ifdef _WIN32
#endif

using std::string;
using std::wstring;

char *lstrip(char *s) {
    while (isspace(*s)) s++;
    return s;
}

const char *lstrip(const char *s) {
    while (isspace(*s)) s++;
    return s;
}

char *rstrip(char *s) {
    char *end = s + strlen(s);  // point one beyond last character
    while (end > s && isspace(*(end - 1))) {
        end--;
    }
    *end = 0;
    return end;
}

char *strip(char *s) {
    rstrip(s);
    return lstrip(s);
}

std::vector<const char *> split_line(char *pos, int (*split_pred)(int)) {
    std::vector<const char *> result;

    char *current_word = pos;
    while (*pos != '\0') {
        if (split_pred(*pos)) {
            *pos = '\0';
            const char *trimmed = strip(current_word);
            if (*trimmed != '\0') {
                result.push_back(trimmed);
            }
            current_word = pos + 1;
        }
        ++pos;
    }
    const char *trimmed = strip(current_word);
    if (*trimmed != '\0') {
        result.push_back(trimmed);
    }
    return result;
}

char *next_word(char **line) {
    if (*line == 0)  // allow subsequent calls without checking
        return 0;

    char *end = *line + strlen(*line);
    char *value = *line;
    while (value < end) {
        value = lstrip(value);
        char *s = value;
        while (*s && !isspace(*s)) s++;
        *s = 0;
        *line = s + 1;
        rstrip(value);
        if (strlen(value) > 0)
            return value;
        else
            return 0;
    }
    return 0;
}

unsigned long long string_to_llu(const char *s) {
    unsigned long long value = 0;
    unsigned long long mult = 1;
    const char *e = s + strlen(s);
    while (e > s) {
        --e;
        value += mult * (*e - '0');
        mult *= 10;
    }
    return value;
}

void lowercase(char *s) {
    while (*s) {
        *s = tolower(*s);
        s++;
    }
}

int parse_boolean(const char *value) {
    if (!strcmp(value, "yes"))
        return 1;
    else if (!strcmp(value, "no"))
        return 0;
    else
        fprintf(stderr,
                "Invalid boolean value. Only yes and no are allowed.\r\n");
    return -1;
}

std::ostream &operator<<(std::ostream &os, const Utf8 &u) {
    return os << std::wstring_convert<std::codecvt_utf8<wchar_t>>().to_bytes(
               u._value);
}

string to_utf8(const char *input) {
    // this isn't right, the input is most likely in locat 8-bit encoding
    return std::string(input);
}

string to_utf8(const wchar_t *input, const WinApiAdaptor &winapi) {
    string result;
    // preflight: how many bytes to we need?
    int required_size =
        winapi.WideCharToMultiByte(CP_UTF8, 0, input, -1, NULL, 0, NULL, NULL);
    if (required_size == 0) {
        // conversion failure. What to do?
        return string();
    }
    result.resize(required_size);

    // real conversion
    winapi.WideCharToMultiByte(CP_UTF8, 0, input, -1, &result[0], required_size,
                               NULL, NULL);

    // strip away the zero termination. This is necessary, otherwise the stored
    // string length
    // in the string is wrong
    result.resize(required_size - 1);

    return result;
}

wstring to_utf16(const char *input, const WinApiAdaptor &winapi) {
    wstring result;
    // preflight: how many bytes to we need?
    int required_size =
        winapi.MultiByteToWideChar(CP_UTF8, 0, input, -1, NULL, 0);
    if (required_size == 0) {
        // conversion failure. What to do?
        return wstring();
    }
    result.resize(required_size);

    // real conversion
    winapi.MultiByteToWideChar(CP_UTF8, 0, input, -1, &result[0],
                               required_size);

    // strip away the zero termination. This is necessary, otherwise the stored
    // string length in the string is wrong
    result.resize(required_size - 1);

    return result;
}

bool ci_compare_pred(unsigned char lhs, unsigned char rhs) {
    return std::tolower(lhs) == std::tolower(rhs);
}

bool ci_equal(const std::string &lhs, const std::string &rhs) {
    return std::equal(lhs.begin(), lhs.end(), rhs.begin(), ci_compare_pred);
}

bool globmatch(const char *pattern, const char *astring) {
    const char *p = pattern;
    const char *s = astring;
    while (*s) {
        if (!*p) return false;  // pattern too short

        // normal character-wise match
        if (tolower(*p) == tolower(*s) || *p == '?') {
            p++;
            s++;
        }

        // non-matching charactetr
        else if (*p != '*')
            return false;

        else {  // check *
            // If there is more than one asterisk in the pattern,
            // we need to try out several variants. We do this
            // by backtracking (smart, eh?)
            int maxlength = strlen(s);
            // replace * by a sequence of ?, at most the rest length of s
            char *subpattern = (char *)malloc(strlen(p) + maxlength + 1);
            bool match = false;
            for (int i = 0; i <= maxlength; i++) {
                for (int x = 0; x < i; x++) subpattern[x] = '?';
                strcpy(subpattern + i, p + 1);  // omit leading '*'
                if (globmatch(subpattern, s)) {
                    match = true;
                    break;
                }
            }
            free(subpattern);
            return match;
        }
    }

    // string has ended, pattern not. Pattern must only
    // contain * now if it wants to match
    while (*p == '*') p++;
    return *p == 0;
}

bool globmatch(const wchar_t *pattern, const wchar_t *astring) {
    const wchar_t *p = pattern;
    const wchar_t *s = astring;
    while (*s) {
        if (!*p) return false;  // pattern too short

        // normal character-wise match
        if (towlower(*p) == towlower(*s) || *p == L'?') {
            p++;
            s++;
        }

        // non-matching charactetr
        else if (*p != L'*')
            return false;

        else {  // check *
            // If there is more than one asterisk in the pattern,
            // we need to try out several variants. We do this
            // by backtracking (smart, eh?)
            int maxlength = wcslen(s);
            // replace * by a sequence of ?, at most the rest length of s
            wchar_t *subpattern = (wchar_t *)malloc(
                (wcslen(p) + maxlength + 1) * sizeof(wchar_t));
            bool match = false;
            for (int i = 0; i <= maxlength; i++) {
                for (int x = 0; x < i; x++) subpattern[x] = L'?';
                wcscpy(subpattern + i, p + 1);  // omit leading '*'
                if (globmatch(subpattern, s)) {
                    match = true;
                    break;
                }
            }
            free(subpattern);
            return match;
        }
    }

    // string has ended, pattern not. Pattern must only
    // contain * now if it wants to match
    while (*p == L'*') p++;
    return *p == 0;
}

std::string replaceAll(const std::string &str, const std::string &from,
                       const std::string &to) {
    if (from.empty()) {
        return str;
    }

    std::string result(str);
    size_t pos = 0;

    while ((pos = result.find(from, pos)) != std::string::npos) {
        result.replace(pos, from.length(), to);
        pos += to.length();
    }
    return result;
}

void stringToIPv6(const char *value, uint16_t *address,
                  const WinApiAdaptor &winapi) {
    const char *pos = value;
    std::vector<uint16_t> segments;
    int skip_offset = -1;
    segments.reserve(8);

    while (pos != NULL) {
        char *endpos = NULL;
        unsigned long segment = strtoul(pos, &endpos, 16);
        if (segment > 0xFFFFu) {
            fprintf(stderr, "Invalid ipv6 address %s\n", value);
            exit(1);
        } else if (endpos == pos) {
            skip_offset = segments.size();
        } else {
            segments.push_back((unsigned short)segment);
        }
        if (*endpos != ':') {
            break;
        }
        pos = endpos + 1;
        ++segment;
    }

    int idx = 0;
    for (std::vector<uint16_t>::const_iterator iter = segments.begin();
         iter != segments.end(); ++iter) {
        if (idx == skip_offset) {
            // example with ::42: segments.size() = 1
            //   this will fill the first 7 fields with 0 and increment idx by 7
            for (size_t i = 0; i < 8 - segments.size(); ++i) {
                address[idx + i] = 0;
            }
            idx += 8 - segments.size();
        }

        address[idx++] = winapi.htons(*iter);
        assert(idx <= 8);
    }
}

void stringToIPv4(const char *value, uint32_t &address) {
    unsigned a, b, c, d;
    if (4 != sscanf(value, "%u.%u.%u.%u", &a, &b, &c, &d)) {
        fprintf(stderr, "Invalid value %s for only_hosts\n", value);
        exit(1);
    }

    address = a + b * 0x100 + c * 0x10000 + d * 0x1000000;
}

void netmaskFromPrefixIPv6(int bits, uint16_t *netmask,
                           const WinApiAdaptor &winapi) {
    memset(netmask, 0, sizeof(uint16_t) * 8);
    for (int i = 0; i < 8; ++i) {
        if (bits > 0) {
            int consume_bits = std::min(16, bits);
            netmask[i] = winapi.htons(0xFFFF << (16 - consume_bits));
            bits -= consume_bits;
        }
    }
}

void netmaskFromPrefixIPv4(int bits, uint32_t &netmask) {
    uint32_t mask_swapped = 0;
    for (int bit = 0; bit < bits; bit++) mask_swapped |= 0x80000000 >> bit;
    unsigned char *s = (unsigned char *)&mask_swapped;
    unsigned char *t = (unsigned char *)&netmask;
    t[3] = s[0];
    t[2] = s[1];
    t[1] = s[2];
    t[0] = s[3];
}
