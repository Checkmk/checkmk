// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <ios>
#include <limits>
#include <memory>
#include <string>
#include <vector>

/// The four consolidation functions from
/// https://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html
struct CF {
    virtual ~CF() = default;
    [[nodiscard]] virtual std::string string() const = 0;
    [[nodiscard]] virtual double init() = 0;
    virtual void handle(double value) = 0;
};

std::ostream &operator<<(std::ostream &os, const CF &cf);

class MaxCF : public CF {
public:
    [[nodiscard]] std::string string() const override { return "MAX"; };
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class MinCF : public CF {
public:
    [[nodiscard]] std::string string() const override { return "MIN"; };
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class AvgCF : public CF {
public:
    [[nodiscard]] std::string string() const override { return "AVERAGE"; };
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    std::size_t nelem = 0;
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class LastCF : public CF {
public:
    [[nodiscard]] std::string string() const override { return "LAST"; };
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

std::vector<double> rrd_consolidate(const std::unique_ptr<CF> &f,
                                    const std::vector<double> &input,
                                    std::size_t act_step, std::size_t target);
