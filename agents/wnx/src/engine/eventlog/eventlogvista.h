#ifndef EventLogVista_h
#define EventLogVista_h

// Windows Event Log API is available from Windows Vista
#undef _WIN32_WINNT
#define _WIN32_WINNT _WIN32_WINNT_VISTA
#include <winsock2.h>
#include <windows.h>
#include <winevt.h>
#include <exception>
#include <functional>
#include <string>
#include <vector>
#include "EventLogBase.h"

namespace cma::evl {

// This safe wrapper for Vista API when Vista API is not accessible(XP/2003)
struct EvtFunctionMap {
public:
    explicit EvtFunctionMap();
    ~EvtFunctionMap();

    HMODULE module() { return module_handle_; }

    decltype(&EvtOpenLog) openLog;
    decltype(&EvtQuery) query;
    decltype(&EvtClose) close;
    decltype(&EvtSeek) seek;
    decltype(&EvtNext) next;
    decltype(&EvtCreateBookmark) createBookmark;
    decltype(&EvtUpdateBookmark) updateBookmark;
    decltype(&EvtCreateRenderContext) createRenderContext;
    decltype(&EvtRender) render;
    decltype(&EvtSubscribe) subscribe;
    decltype(&EvtFormatMessage) formatMessage;
    decltype(&EvtGetEventMetadataProperty) getEventMetadataProperty;
    decltype(&EvtOpenPublisherMetadata) openPublisherMetadata;
    decltype(&EvtGetLogInfo) getLogInfo;

private:
    HMODULE module_handle_;
};

extern EvtFunctionMap g_evt;

class EventLogVista : public EventLogBase {
    static const int EVENT_BLOCK_SIZE = 16;

public:
    // constructor
    EventLogVista(const std::wstring &path);
    ~EventLogVista() {
        if (event_signal_) CloseHandle(event_signal_);
        if (g_evt.close) {
            if (subscription_handle_) g_evt.close(subscription_handle_);
            for (auto &h : event_table_) g_evt.close(h);
            if (render_context_) g_evt.close(render_context_);
        }
    }

    virtual std::wstring getName() const override;

    virtual void seek(uint64_t record_id) override;

    virtual EventLogRecordBase *readRecord() override;

    virtual uint64_t getLastRecordId() override;

    virtual bool isLogValid() const override;

private:
    void destroyEvents() {
        if (g_evt.close) {
            for (auto &h : event_table_) g_evt.close(h);
        }
        event_table_.clear();
    }

    bool fillBuffer();
    std::wstring renderBookmark(EVT_HANDLE bookmark) const;

    std::wstring log_name_;
    EVT_HANDLE subscription_handle_;
    EVT_HANDLE render_context_;
    HANDLE event_signal_;
    std::vector<EVT_HANDLE> event_table_;
    size_t index_in_events_{0};
};  // namespace cma::evl
}  // namespace cma::evl
#endif  // EventLogVista_h
