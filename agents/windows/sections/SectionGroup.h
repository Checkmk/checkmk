// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef SectionGroup_h
#define SectionGroup_h

#include <ctime>
#include <memory>
#include "Section.h"

class Environment;

/**
 * allows treating several sections as a group.
 * This allows toggling the whole set of queries with a single "section"-name
 * and - optionally - outputting them as "nested" tables using [[[sectionname]]]
 * syntax so that a single check can process them.
 * This is mostly useful with sections with standardized syntax like wmi or
 * perfcounter interfaces.
 **/
class SectionGroup : public Section {
public:
    SectionGroup(const std::string &outputName, const std::string &configName,
                 const Environment &env, Logger *logger,
                 const WinApiInterface &winapi, bool show_header);

    /**
     * add a section that will be printed as part of this group
     **/
    SectionGroup *withSubSection(Section *section);
    /**
     * add a section that will be printed as part of this group, but
     * only if one of the "regular" sections added with "withSubSection"
     * has had output.
     * This is useful for sections that are only interesting in
     * combination with another one
     **/
    SectionGroup *withDependentSubSection(Section *section);
    SectionGroup *withToggleIfMissing();

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &remoteIP) override;

private:
    std::vector<std::unique_ptr<Section>> _subsections;
    std::vector<std::unique_ptr<Section>> _dependent_subsections;
    bool _toggle_if_missing{false};
    bool _fail_if_missing{false};
    time_t _disabled_until{0};
};

#endif  // SectionGroup_h
