// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
