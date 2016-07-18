// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef RendererPython_h
#define RendererPython_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include <vector>
#include "OutputBuffer.h"
#include "Renderer.h"

class RendererPython : public Renderer {
public:
    RendererPython(OutputBuffer *output,
                   OutputBuffer::ResponseHeader response_header,
                   bool do_keep_alive, std::string invalid_header_message,
                   int timezone_offset);

    void startOfQuery() override;
    void outputDataSetSeparator() override;
    void endOfQuery() override;

    void outputDatasetBegin() override;
    void outputFieldSeparator() override;
    void outputDatasetEnd() override;

    void outputBeginList() override;
    void outputListSeparator() override;
    void outputEndList() override;

    void outputBeginSublist() override;
    void outputSublistSeparator() override;
    void outputEndSublist() override;

    void outputBeginDict() override;
    void outputDictSeparator() override;
    void outputDictValueSeparator() override;
    void outputEndDict() override;

    void outputNull() override;
    void outputBlob(const std::vector<char> *blob) override;
    void outputString(const char *value, int len = -1) override;
};

#endif  // RendererPython_h
