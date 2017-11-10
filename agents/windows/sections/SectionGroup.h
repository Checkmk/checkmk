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

#ifndef SectionGroup_h
#define SectionGroup_h

#include <ctime>
#include <memory>
#include "../Section.h"

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
    std::vector<std::unique_ptr<Section>> _subsections;
    std::vector<std::unique_ptr<Section>> _dependent_subsections;
    bool _toggle_if_missing{false};
    bool _fail_if_missing{false};
    bool _nested{false};
    time_t _disabled_until{0};

public:
    SectionGroup(const std::string &outputName, const std::string &configName,
                 const Environment &env, Logger *logger,
                 const WinApiAdaptor &winapi);
    SectionGroup *withNestedSubtables();
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
    virtual bool produceOutputInner(std::ostream &out) override;
};

#endif  // SectionGroup_h
