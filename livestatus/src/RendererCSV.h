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

#ifndef RendererCSV_h
#define RendererCSV_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include <vector>
#include "OutputBuffer.h"
#include "Renderer.h"

class RendererCSV : public Renderer {
public:
    RendererCSV(OutputBuffer *output,
                OutputBuffer::ResponseHeader response_header,
                bool do_keep_alive, std::string invalid_header_message,
                std::string field_separator, std::string dataset_separator,
                std::string list_separator, std::string host_service_separator,
                int timezone_offset);

    void outputNull() override;
    void outputBlob(const std::vector<char> *blob) override;
    void outputString(const char *value, int len = -1) override;

private:
    // separateRowElements
    const std::string _field_separator;
    // endRow
    const std::string _dataset_separator;
    // separateListElements, separateDictElements
    const std::string _list_separator;
    // separateSublistElements, separateDictKeyValue
    const std::string _host_service_separator;

    void startQuery() override;
    void separateQueryElements() override;
    void endQuery() override;

    void startRow() override;
    void separateRowElements() override;
    void endRow() override;

    void startList() override;
    void separateListElements() override;
    void endList() override;

    void startSublist() override;
    void separateSublistElements() override;
    void endSublist() override;

    void startDict() override;
    void separateDictElements() override;
    void separateDictKeyValue() override;
    void endDict() override;
};

#endif  // RendererCSV_h
