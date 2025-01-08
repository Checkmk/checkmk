// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <limits>
#include <memory>
#include <vector>

/// The four consolidation functions from
/// https://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html
struct CF {
    virtual ~CF() = default;
    [[nodiscard]] virtual double init() = 0;
    virtual void handle(double value) = 0;
};

class MaxCF : public CF {
public:
    MaxCF() = default;
    ~MaxCF() override = default;
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class MinCF : public CF {
public:
    MinCF() = default;
    ~MinCF() override = default;
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class AvgCF : public CF {
public:
    AvgCF() = default;
    ~AvgCF() override = default;
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    std::size_t nelem = 0;
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

class LastCF : public CF {
public:
    LastCF() = default;
    ~LastCF() override = default;
    [[nodiscard]] double init() override;
    void handle(double value) override;

private:
    double counter_ = std::numeric_limits<double>::quiet_NaN();
};

std::vector<double> rrd_consolidate(const std::unique_ptr<CF> &f,
                                    const std::vector<double> &input,
                                    std::size_t act_step, std::size_t target);
