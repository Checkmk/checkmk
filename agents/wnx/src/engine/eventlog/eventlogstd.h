// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef EVENT_LOG_H
#define EVENT_LOG_H

#include <map>

#include "EventLogBase.h"
namespace cma::evl {
class MessageResolver {
public:
    explicit MessageResolver(const std::wstring &log_name) : _name(log_name) {}
    MessageResolver(const MessageResolver &) = delete;
    MessageResolver &operator=(const MessageResolver &) = delete;
    MessageResolver(MessageResolver &&) = delete;
    MessageResolver &operator=(MessageResolver &&) = delete;
    ~MessageResolver();

    std::wstring resolve(DWORD event_id, LPCWSTR source,
                         LPCWSTR *parameters) const;

private:
    std::vector<std::wstring> getMessageFiles(LPCWSTR source) const;
    std::wstring resolveInt(DWORD event_id, LPCWSTR dllpath,
                            LPCWSTR *parameters) const;

    std::wstring _name;
    mutable std::map<std::wstring, HMODULE> _cache;
};

class EventLog final : public EventLogBase {
    static constexpr size_t INIT_BUFFER_SIZE = 64U * 1024U;

public:
    /**
     * Construct a reader for the named eventlog
     */
    explicit EventLog(const std::wstring &name);
    EventLog(const EventLog &) = delete;
    EventLog operator=(const EventLog &) = delete;
    EventLog(EventLog &&) = delete;
    EventLog operator=(EventLog &&) = delete;
    ~EventLog() override {
        if (handle_ != nullptr) {
            ::CloseEventLog(handle_);
            handle_ = nullptr;
        }
    }

    std::wstring getName() const override;

    /**
     * seek to the specified record on the next read or, if the
     * record_number is older than the oldest existing record, seek to the
     * beginning. Note: there is a bug in the MS eventlog code that prevents
     * seeking on large eventlogs. In this case this function will still
     * work as expected but the next read will be slow.
     */
    void seek(uint64_t record_number) override;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will
     * be quick most of the time but occasionally cause a fetch via api that
     * takes longer
     */
    EventLogRecordBase *readRecord() override;

    /**
     * return the ID of the last record in eventlog
     */
    uint64_t getLastRecordId() override;

    bool isLogValid() const override { return handle_ != nullptr; }

private:
    bool fillBuffer();

    std::wstring name_;
    HANDLE handle_;  // dtor
    DWORD record_offset_{0};
    bool seek_possible_{true};
    std::vector<BYTE> buffer_;
    DWORD buffer_offset_{0};
    DWORD buffer_used_{0};
    DWORD last_record_read_{0};

    MessageResolver message_resolver_;
};
}  // namespace cma::evl
#endif  // EVENT_LOG_H
