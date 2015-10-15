#include "stringutil.h"
#include <cstring>
#include <cctype>
#include <cstdio>
#include <windows.h>


char *lstrip(char *s)
{
    while (isspace(*s))
        s++;
    return s;
}


void rstrip(char *s)
{
    char *end = s + strlen(s); // point one beyond last character
    while (end > s && isspace(*(end - 1))) {
        end--;
    }
    *end = 0;
}

char *strip(char *s)
{
    rstrip(s);
    return lstrip(s);
}

std::vector<const char*> split_line(char *pos, int (*split_pred)(int))
{
    std::vector<const char*> result;

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


char *next_word(char **line)
{
    if (*line == 0) // allow subsequent calls without checking
        return 0;

    char *end = *line + strlen(*line);
    char *value = *line;
    while (value < end) {
        value = lstrip(value);
        char *s = value;
        while (*s && !isspace(*s))
            s++;
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


char *llu_to_string(unsigned long long value)
{
    static char buffer[64];

    if (value == 0) {
        strcpy(buffer, "0");
        return buffer;
    }

    buffer[63] = 0;

    char *write = buffer + 63;
    while (value > 0) {
        if (write <= buffer) {
            strcpy(buffer, "(invalid)");
            return buffer;
        }
        char digit = (value % 10) + '0';
        *--write = digit;
        value = value / 10;
    }
    return write;
}


unsigned long long string_to_llu(const char *s)
{
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


char *ipv4_to_text(uint32_t ip)
{
    static char text[32];
    snprintf(text, 32, "%u.%u.%u.%u",
            ip & 255,
            ip >> 8 & 255,
            ip >> 16 & 255,
            ip >> 24);
    return text;
}

void lowercase(char *s)
{
    while (*s) {
        *s = tolower(*s);
        s++;
    }
}


int parse_boolean(char *value)
{
    if (!strcmp(value, "yes"))
        return 1;
    else if (!strcmp(value, "no"))
        return 0;
    else
        fprintf(stderr, "Invalid boolean value. Only yes and no are allowed.\r\n");
    return -1;
}

bool globmatch(const char *pattern, const char *astring)
{
    const char *p = pattern;
    const char *s = astring;
    while (*s) {
        if (!*p)
            return false; // pattern too short

        // normal character-wise match
        if (tolower(*p) == tolower(*s) || *p == '?') {
            p++;
            s++;
        }

        // non-matching charactetr
        else if (*p != '*')
            return false;

        else { // check *
            // If there is more than one asterisk in the pattern,
            // we need to try out several variants. We do this
            // by backtracking (smart, eh?)
            int maxlength = strlen(s);
            // replace * by a sequence of ?, at most the rest length of s
            char *subpattern = (char *)malloc(strlen(p) + maxlength + 1);
            bool match = false;
            for (int i=0; i<=maxlength; i++) {
                for (int x=0; x<i; x++)
                    subpattern[x] = '?';
                strcpy(subpattern + i, p + 1); // omit leading '*'
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


std::string get_win_error_as_string(DWORD error_id)
{
    //Get the error message, if any.
    //DWORD errorMessageID = ::GetLastError();
    if(error_id == 0)
        return "No error message has been recorded";

    LPSTR messageBuffer = NULL;
    size_t size = FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                                 NULL, error_id, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (LPSTR)&messageBuffer, 0, NULL);

    std::string message(messageBuffer, size);

    //Free the buffer.
    LocalFree(messageBuffer);

    return message;
}

