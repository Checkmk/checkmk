#include "stdafx.h"

#include "eventlog/eventlogstd.h"

#include <algorithm>
#include <map>
#include <string>

#include "tools/_raii.h"

#include "common/wtools.h"

#include "logger.h"
namespace cma::evl {
std::vector<std::wstring> MessageResolver::getMessageFiles(
    LPCWSTR source) const {
    static const std::wstring base =
        std::wstring(L"SYSTEM\\CurrentControlSet\\Services\\EventLog");
    std::wstring regpath = base + L"\\" + _name + L"\\" + source;

    HKEY key = nullptr;
    DWORD ret =
        RegOpenKeyExW(HKEY_LOCAL_MACHINE, regpath.c_str(), 0, KEY_READ, &key);
    if (ret != ERROR_SUCCESS) {
        XLOG::t("Can't to open HKLM: '{}'", wtools::ConvertToUTF8(regpath));
        return {};
    }
    ON_OUT_OF_SCOPE(RegCloseKey(key));

    DWORD size = 64;
    std::vector<BYTE> buffer(size);
    // first try with fixed-size buffer
    DWORD res = RegQueryValueExW(key, L"EventMessageFile", nullptr, nullptr,
                                 buffer.data(), &size);
    if (res == ERROR_MORE_DATA) {
        buffer.resize(size);
        // actual read
        res = ::RegQueryValueExW(key, L"EventMessageFile", nullptr, nullptr,
                                 buffer.data(), &size);
    }

    if (res != ERROR_SUCCESS) {
        XLOG::t("Can't to read EventMessageFile in registry '{}' : {:X}",
                wtools::ConvertToUTF8(regpath), (unsigned int)res);
        return {};
    }

    // result may be multiple dlls
    std::vector<std::wstring> result;
    std::wstringstream str(reinterpret_cast<wchar_t *>(&buffer[0]));
    std::wstring dll_path;
    while (std::getline(str, dll_path, L';')) {
        result.push_back(dll_path);
    }
    return result;
}

std::wstring MessageResolver::resolveInt(DWORD eventID, LPCWSTR dllpath,
                                         LPCWSTR *parameters) const {
    HMODULE dll = nullptr;

    if (dllpath) {
        auto iter = _cache.find(dllpath);
        if (iter == _cache.end()) {
            dll = wtools::LoadWindowsLibrary(dllpath);
            _cache.emplace(std::wstring(dllpath), dll);
        } else {
            dll = iter->second;
        }

        if (!dll) {
            XLOG::l("Failed to load dll '{}'", wtools::ConvertToUTF8(dllpath));
            return {};
        }
    } else {
        dll = nullptr;
    }

    std::wstring result;
    // maximum supported size
    result.resize(8192);

    DWORD dwFlags = FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
    if (dll) dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;

    XLOG::t("Event ID: {}.{}",
            eventID / 65536,   // "Qualifiers": no idea what *that* is
            eventID % 65536);  // the actual event id

    XLOG::t("Formatting Message");
    DWORD len =
        ::FormatMessageW(dwFlags, dll, eventID,
                         0,  // accept any language
                         &result[0], (DWORD)result.size(), (char **)parameters);
    XLOG::t("Formatting Message - DONE");

    // this trims the result string or empties it if formatting failed
    result.resize(len);
    return result;
}

std::wstring MessageResolver::resolve(DWORD eventID, LPCWSTR source,
                                      LPCWSTR *parameters) const {
    std::wstring result;
    auto sources = getMessageFiles(source);
    for (const auto &dllpath : sources) {
        result = resolveInt(eventID, dllpath.c_str(), parameters);
        if (!result.empty()) {
            break;
        }
    }

    if (result.empty()) {
        // failed to resolve message, create an output_message
        // that simply concatenates all parameters
        for (int i = 0; parameters[i] != nullptr; ++i) {
            if (i > 0) {
                result += L" ";
            }
            result += parameters[i];
        }
    }
    std::replace_if(
        result.begin(), result.end(),
        [](wchar_t ch) { return ch == L'\n' || ch == L'\r'; }, ' ');
    return result;
}

class EventLogRecord : public EventLogRecordBase {
public:
    EventLogRecord(EVENTLOGRECORD *record, const MessageResolver &resolver)
        : _record(record), _resolver(resolver) {}

    virtual uint64_t recordId() const override {
        return static_cast<uint64_t>(_record->RecordNumber);
    }

    virtual uint16_t eventId() const override {
        return _record->EventID % 65536;
    }

    virtual uint16_t eventQualifiers() const override {
        return (uint16_t)(_record->EventID / 65536);
    }

    virtual time_t timeGenerated() const override {
        return _record->TimeGenerated;
    }

    virtual std::wstring source() const override {
        return std::wstring(reinterpret_cast<LPCWSTR>(_record + 1));
    }

    virtual Level eventLevel() const override {
        switch (_record->EventType) {
            case EVENTLOG_ERROR_TYPE:
                return Level::Error;
            case EVENTLOG_WARNING_TYPE:
                return Level::Warning;
            case EVENTLOG_INFORMATION_TYPE:
                return Level::Information;
            case EVENTLOG_AUDIT_SUCCESS:
                return Level::AuditSuccess;
            case EVENTLOG_SUCCESS:
                return Level::Success;
            case EVENTLOG_AUDIT_FAILURE:
                return Level::AuditFailure;
            default:
                return Level::Error;
        }
    }

    virtual std::wstring makeMessage() const override {
        // prepare array of zero terminated strings to be inserted
        // into message template.
        std::vector<LPCWSTR> strings;
        LPCWSTR string = (WCHAR *)(((char *)_record) + _record->StringOffset);
        for (int i = 0; i < _record->NumStrings; ++i) {
            strings.push_back(string);
            string += wcslen(string) + 1;
        }
        // Sometimes the eventlog record does not provide
        // enough strings for the message template. Causes crash...
        // -> Fill the rest with empty strings
        strings.resize(63, L"");
        // end marker in array
        strings.push_back(nullptr);

        return _resolver.resolve(_record->EventID, source().c_str(),
                                 &strings[0]);
    }

private:
    EVENTLOGRECORD *_record;
    const MessageResolver &_resolver;
};

EventLog::EventLog(const std::wstring &Name)
    : name_(Name), message_resolver_(Name) {
    handle_ = OpenEventLogW(nullptr, name_.c_str());

    if (handle_ == nullptr) {
        XLOG::l("failed to open eventlog: '{}'", wtools::ConvertToUTF8(name_));
    }

    buffer_.resize(INIT_BUFFER_SIZE);
}

std::wstring EventLog::getName() const { return name_; }

void EventLog::seek(uint64_t record_number) {
    DWORD oldestRecord = 0;
    DWORD recordCount = 0;

    if (GetOldestEventLogRecord(handle_, &oldestRecord) &&
        (record_number < oldestRecord)) {
        // Beyond the oldest record:
        record_offset_ = oldestRecord;
    } else if (GetNumberOfEventLogRecords(handle_, &recordCount) &&
               (record_number >= oldestRecord + recordCount)) {
        // Beyond the newest record. Note: set offset intentionally to the next
        // record after the currently last one!
        record_offset_ = oldestRecord + recordCount;
    } else {
        // Within bounds, the offset for the next actual read:
        record_offset_ = (DWORD)record_number;
    }
    buffer_offset_ = buffer_used_;  // enforce that a new chunk is fetched
}

EventLogRecordBase *EventLog::readRecord() {
    EVENTLOGRECORD *result = nullptr;
    while (result == nullptr) {
        while (buffer_offset_ < buffer_used_) {
            EVENTLOGRECORD *temp =
                reinterpret_cast<EVENTLOGRECORD *>(&(buffer_[buffer_offset_]));
            buffer_offset_ += temp->Length;
            // as long as seeking on this event log is possible this will
            // always be true.
            // otherwise this skips events we want to move past
            if (temp->RecordNumber >= record_offset_) {
                record_offset_ = 0;  // don't need to keep the offset after
                                     // we moved past it
                result = temp;
                break;
            }
        }

        if (result == nullptr) {
            // no fitting record in our buffer, get the next couple of
            // records
            try {
                if (!fillBuffer()) {
                    // no more events to read, break out of the loop
                    break;
                }
            } catch (const std::exception &e) {
                // win_exception is coming here
                // generated exception in fillBuffer must be processed in any
                // case usually we have something like FILE_TOO_LARGE(223)
                // during reading Event Log and fpor some reason we thorw
                // exception. Bad? Bad. In Fact, we have SERIOUS problem with
                // monitored host. Our Log was informed. Probably we need some
                // additional checks pointing that logs are either bad or
                // overflown
                XLOG::l("Error reading event log. Exception is {}", e.what());
                break;
            }
        }
    }
    if (result != nullptr) {
        last_record_read_ = result->RecordNumber;
        return new EventLogRecord(result, message_resolver_);
    } else {
        return nullptr;
    }
}

uint64_t EventLog::getLastRecordId() {
    DWORD oldest_record = 0;
    DWORD record_count = 0;
    if (::GetOldestEventLogRecord(handle_, &oldest_record) &&
        ::GetNumberOfEventLogRecords(handle_, &record_count) &&
        oldest_record + record_count > 0) {
        return oldest_record + record_count - 1;
    }

    return 0;
}

bool EventLog::fillBuffer() {
    buffer_offset_ = 0;

    // test if we're at the end of the log, as we don't get
    // a proper error message when reading beyond the last log record
    DWORD oldestRecord = 0;
    DWORD recordCount = 0;

    if (::GetOldestEventLogRecord(handle_, &oldestRecord) &&
        ::GetNumberOfEventLogRecords(handle_, &recordCount)) {
        if (record_offset_ >= oldestRecord + recordCount) {
            return false;
        }
    }

    DWORD flags = EVENTLOG_FORWARDS_READ;
    if ((record_offset_ != 0) && (seek_possible_)) {
        flags |= EVENTLOG_SEEK_READ;
    } else {
        flags |= EVENTLOG_SEQUENTIAL_READ;
    }

    XLOG::t("  seek to {}", record_offset_);

    DWORD bytes_required = 0;

    if (::ReadEventLogW(handle_, flags, record_offset_, buffer_.data(),
                        (DWORD)buffer_.size(), &buffer_used_,
                        &bytes_required)) {
        return true;
    } else {
        DWORD error = ::GetLastError();
        if (error == ERROR_HANDLE_EOF) {
            // end of log, all good
            return false;
        } else if (error == ERROR_INSUFFICIENT_BUFFER) {
            // resize buffer and recurse
            buffer_.resize(bytes_required);
            return fillBuffer();
        } else if (error == ERROR_INVALID_PARAMETER) {
            if ((flags & EVENTLOG_SEEK_READ) == EVENTLOG_SEEK_READ) {
                // the most likely cause for this error (since our
                // parameters are good) is the following bug:
                // https://support.microsoft.com/en-us/kb/177199
                seek_possible_ = false;
                return fillBuffer();
            }  // otherwise treat this like any other error
        }

        XLOG::l("Can't read eventlog '{}' error {}",
                wtools::ConvertToUTF8(name_), error);
        return false;
    }
}
}  // namespace cma::evl
