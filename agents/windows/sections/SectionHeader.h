// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

#ifndef SectionHeader_h
#define SectionHeader_h

#include <optional>
#include <string>

class Logger;

template <unsigned char SepChar>
struct Separator {
    std::ostream &output(std::ostream &os) const {
        return os << ":sep(" << static_cast<unsigned>(SepChar) << ")";
    }
};

// Specialization for default ' ' (space) separator: skip output.
template <>
inline std::ostream &Separator<' '>::output(std::ostream &os) const {
    return os;
}

template <unsigned char SepChar>
inline std::ostream &operator<<(std::ostream &os,
                                const Separator<SepChar> &sep) {
    return sep.output(os);
}

struct SectionBrackets {
    static constexpr auto left = "<<<";
    static constexpr auto right = ">>>";
};

struct SubSectionBrackets {
    static constexpr auto left = "[";
    static constexpr auto right = "]";
};

class SectionHeaderBase {
public:
    SectionHeaderBase() = default;
    SectionHeaderBase(const SectionHeaderBase &) = delete;
    virtual ~SectionHeaderBase() = default;
    SectionHeaderBase &operator=(const SectionHeaderBase &) = delete;

    virtual std::ostream &output(std::ostream &os) const = 0;
};

template <unsigned char SepChar, class Brackets>
class SectionHeader : public SectionHeaderBase {
public:
    SectionHeader(const std::string &name, Logger *logger)
        : _name(name), _logger(logger) {}
    virtual ~SectionHeader() = default;

    virtual std::ostream &output(std::ostream &os) const override {
        return os << Brackets::left << _name << _separator << Brackets::right
                  << "\n";
    }

private:
    const std::string _name;
    Logger *_logger;
    const Separator<SepChar> _separator{};
};

using DefaultHeader = SectionHeader<' ', SectionBrackets>;
using SubSectionHeader = SectionHeader<' ', SubSectionBrackets>;

class HiddenHeader : public DefaultHeader {
public:
    explicit HiddenHeader(Logger *logger) : DefaultHeader({}, logger) {}

    std::ostream &output(std::ostream &os) const final { return os; }
};

inline std::ostream &operator<<(std::ostream &os,
                                const SectionHeaderBase &header) {
    return header.output(os);
}

#endif  // SectionHeader_h
