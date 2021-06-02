// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef EventLog_h
#define EventLog_h

#include <map>

#include "EventLogBase.h"
namespace cma::evl {
class MessageResolver {
public:
    MessageResolver(const std::wstring &log_name) : _name(log_name) {}
    MessageResolver(const MessageResolver &) = delete;
    MessageResolver &operator=(const MessageResolver &) = delete;
    ~MessageResolver() {
        for (auto &c : _cache) {
            if (c.second != nullptr) {
                FreeLibrary(c.second);
            }
        }
    }

    std::wstring resolve(DWORD eventID, LPCWSTR source,
                         LPCWSTR *parameters) const;

private:
    std::vector<std::wstring> getMessageFiles(LPCWSTR source) const;
    std::wstring resolveInt(DWORD eventID, LPCWSTR dllpath,
                            LPCWSTR *parameters) const;

    std::wstring _name;
    mutable std::map<std::wstring, HMODULE> _cache;
};

class EventLog : public EventLogBase {
    static const size_t INIT_BUFFER_SIZE = 64 * 1024;

public:
    /**
     * Construct a reader for the named eventlog
     */
    EventLog(const std::wstring &Name);
    ~EventLog() {
        if (handle_ != nullptr) {
            ::CloseEventLog(handle_);
            handle_ = nullptr;
        }
    }

    virtual std::wstring getName() const override;

    /**
     * seek to the specified record on the next read or, if the
     * record_number is older than the oldest existing record, seek to the
     * beginning. Note: there is a bug in the MS eventlog code that prevents
     * seeking on large eventlogs. In this case this function will still
     * work as expected but the next read will be slow.
     */
    virtual void seek(uint64_t record_id) override;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will
     * be quick most of the time but occasionally cause a fetch via api that
     * takes longer
     */
    virtual EventLogRecordBase *readRecord() override;

    /**
     * return the ID of the last record in eventlog
     */
    virtual uint64_t getLastRecordId() override;

    virtual bool isLogValid() const override { return handle_ != nullptr; }

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
#endif  // EventLog_h
