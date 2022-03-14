#include "stdafx.h"

#include "eventlog/eventlogstd.h"

#include <algorithm>
#include <map>
#include <string>

#include "common/wtools.h"
#include "logger.h"
#include "tools/_raii.h"
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
        // XLOG::t("Can't open HKLM: '{}'", wtools::ConvertToUTF8(regpath));
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
        /*
                XLOG::t("Can't read EventMessageFile in registry '{}' : {:X}",
                        wtools::ConvertToUTF8(regpath), (unsigned int)res);
        */
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

std::wstring MessageResolver::resolveInt(DWORD event_id, LPCWSTR dllpath,
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
            XLOG::l("Failed to load dll '{}' error = [{}]", wtools::ToUtf8(dllpath), ::GetLastError());
            return {};
        }
    }

    std::wstring result;
    result.resize(8192);

    DWORD dwFlags = FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
    if (dll) {
        dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;
    }

    DWORD len = ::FormatMessageW(dwFlags, dll, event_id,
                                 0,  // accept any language
                                 &result[0], static_cast<DWORD>(result.size()),
                                 (char **)parameters);

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
    std::ranges::replace_if(
        result, [](wchar_t ch) { return ch == L'\n' || ch == L'\r'; }, ' ');
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
                return Level::error;
            case EVENTLOG_WARNING_TYPE:
                return Level::warning;
            case EVENTLOG_INFORMATION_TYPE:
                return Level::information;
            case EVENTLOG_AUDIT_SUCCESS:
                return Level::audit_success;
            case EVENTLOG_SUCCESS:
                return Level::success;
            case EVENTLOG_AUDIT_FAILURE:
                return Level::audit_failure;
            default:
                return Level::error;
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
        XLOG::l("failed to open eventlog: '{}' error = [{}]",
                wtools::ToUtf8(name_), GetLastError());
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
            auto temp =
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

        if (result == nullptr && !fillBuffer()) break;  // end or error
    }

    if (result == nullptr) return nullptr;

    last_record_read_ = result->RecordNumber;
    return new EventLogRecord(result, message_resolver_);
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

// function is based on the legacy agent code
// this is absolutely crazy approach
// returns false on error or end of stream
// #TODO REWRITE
bool EventLog::fillBuffer() {
    buffer_offset_ = 0;

    // test if we're at the end of the log, as we don't get
    // a proper error message when reading beyond the last log record
    DWORD oldest_record = 0;
    DWORD total_records = 0;

    if (::GetOldestEventLogRecord(handle_, &oldest_record) &&
        ::GetNumberOfEventLogRecords(handle_, &total_records)) {
        if (record_offset_ >= oldest_record + total_records) {
            return false;
        }
    }

    DWORD flags = EVENTLOG_FORWARDS_READ;
    if ((record_offset_ != 0) && (seek_possible_)) {
        flags |= EVENTLOG_SEEK_READ;
    } else {
        flags |= EVENTLOG_SEQUENTIAL_READ;
    }

    DWORD bytes_required = 0;

    if (::ReadEventLogW(handle_, flags, record_offset_, buffer_.data(),
                        (DWORD)buffer_.size(), &buffer_used_,
                        &bytes_required)) {
        return true;
    }

    auto error = ::GetLastError();
    if (error == ERROR_HANDLE_EOF) {
        // end of log, all good
        return false;
    }

    // #TODO remove those recursion in next version
    if (error == ERROR_INSUFFICIENT_BUFFER) {
        // resize buffer and recurse
        buffer_.resize(bytes_required);
        return fillBuffer();
    }

    if ((error == ERROR_INVALID_PARAMETER) &&
        0 != (flags & EVENTLOG_SEEK_READ)) {
        // if error during "seek_read" we should retry with
        // sequential read
        // the most likely cause for this error (since our
        // parameters are good) is the following bug:
        // https://support.microsoft.com/en-us/kb/177199
        seek_possible_ = false;
        return fillBuffer();
        // otherwise treat this like any other error
    }

    XLOG::l("Can't read eventlog '{}' error {}", wtools::ToUtf8(name_), error);
    return false;
}
}  // namespace cma::evl
