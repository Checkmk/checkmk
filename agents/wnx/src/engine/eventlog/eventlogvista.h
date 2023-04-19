// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef EventLogVista_h
#define EventLogVista_h
#include <windows.h>
#include <winevt.h>

#include <string>
#include <vector>

#include "EventLogBase.h"

namespace cma::evl {

struct EvtHandleDeleter {
    using pointer = EVT_HANDLE;  // trick to use HANDLE as STL pointer
    void operator()(EVT_HANDLE h) const noexcept;
};

using EvtHandle = std::unique_ptr<EVT_HANDLE, EvtHandleDeleter>;

constexpr int EVENT_BLOCK_SIZE = 16;

bool IsEvtApiAvailable() noexcept;

class EventLogVista final : public EventLogBase {
public:
    explicit EventLogVista(const std::wstring &path);
    EventLogVista(const EventLogVista &) = delete;
    EventLogVista operator=(const EventLogVista &) = delete;
    EventLogVista(EventLogVista &&) = delete;
    EventLogVista operator=(EventLogVista &&) = delete;
    ~EventLogVista() override;

    [[nodiscard]] std::wstring getName() const override;
    void seek(uint64_t record_id) override;
    EventLogRecordBase *readRecord() override;
    uint64_t getLastRecordId() override;
    [[nodiscard]] bool isLogValid() const override;

private:
    bool fillBuffer();
    bool processEvents();
    void resetData();
    [[nodiscard]] bool isNoMoreData() const noexcept;

    std::wstring log_name_;
    EvtHandle subscription_handle_;
    EvtHandle render_context_;
    HANDLE event_signal_;
    std::vector<EVT_HANDLE> event_table_;
    size_t index_in_table_{0};
};
}  // namespace cma::evl
#endif  // EventLogVista_h
