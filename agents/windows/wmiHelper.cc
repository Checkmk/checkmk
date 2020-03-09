// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "wmiHelper.h"

#include <comdef.h>
#include <oleauto.h>
#include <ios>
#include <iostream>
#include <sstream>
#include <string>

#include "Logger.h"
#include "stringutil.h"
#include "types.h"

using namespace wmi;
using namespace std;

std::string ComException::resolveError(HRESULT result,
                                       const WinApiInterface &winapi) {
    switch (static_cast<ULONG>(result)) {
        case WBEM_E_INVALID_NAMESPACE:
            return string("Invalid Namespace");
        case WBEM_E_ACCESS_DENIED:
            return string("Access Denied");
        case WBEM_E_INVALID_CLASS:
            return string("Invalid Class");
        case WBEM_E_INVALID_QUERY:
            return string("Invalid Query");
        default:
            return _com_error(result, getErrorInfo(winapi)).ErrorMessage();
    }
}

ComException::ComException(const string &message, HRESULT result,
                           const WinApiInterface &winapi)
    : runtime_error(message + string(": ") + resolveError(result, winapi) +
                    string(" (") + toStringHex(result) + string(")")) {}

ComTypeException::ComTypeException(const string &message)
    : runtime_error(message) {}

IErrorInfo *ComException::getErrorInfo(const WinApiInterface &winapi) {
    IErrorInfo *result;
    winapi.GetErrorInfo(0, &result);
    return result;
}

string ComException::toStringHex(HRESULT res) {
    ostringstream out;
    out << hex << res;
    return out.str();
}

Variant::Variant(const VARIANT &val, Logger *logger,
                 const WinApiInterface &winapi)
    : _value(val), _logger(logger), _winapi(winapi) {}

Variant::~Variant() { _winapi.VariantClear(&_value); }

void releaseInterface(IUnknown *ptr) {
    if (ptr != nullptr) {
        ptr->Release();
    }
}

ObjectWrapper::ObjectWrapper(IWbemClassObject *object, Logger *logger,
                             const WinApiInterface &winapi)
    : _current(object, releaseInterface), _logger(logger), _winapi(winapi) {}

ObjectWrapper::ObjectWrapper(const ObjectWrapper &reference)
    : _current(reference._current)
    , _logger(reference._logger)
    , _winapi(reference._winapi) {}

bool ObjectWrapper::contains(const wchar_t *key) const {
    VARIANT value;
    HRESULT res = _current->Get(key, 0, &value, nullptr, nullptr);
    if (FAILED(res)) {
        return false;
    }
    bool not_null = value.vt != VT_NULL;
    _winapi.VariantClear(&value);
    return not_null;
}

int ObjectWrapper::typeId(const wchar_t *key) const {
    VARIANT value;
    HRESULT res = _current->Get(key, 0, &value, nullptr, nullptr);
    if (FAILED(res)) {
        return 0;
    }
    int type_id = value.vt;
    _winapi.VariantClear(&value);
    return type_id;
}

ObjectWrapper::~ObjectWrapper() noexcept {}

VARIANT ObjectWrapper::getVarByKey(const wchar_t *key) const {
    VARIANT value;
    HRESULT res = _current->Get(key, 0, &value, nullptr, nullptr);
    if (FAILED(res)) {
        throw ComException(
            std::string("Failed to retrieve key: ") + to_utf8(key), res,
            _winapi);
    }

    return value;
}

Result::Result(Logger *logger, const WinApiInterface &winapi)
    : ObjectWrapper(nullptr, logger, winapi)
    , _enumerator(nullptr, releaseInterface) {}

Result::Result(const Result &reference)
    : ObjectWrapper(reference)
    , _enumerator(reference._enumerator)
    , _last_error(reference._last_error) {}

Result::Result(IEnumWbemClassObject *enumerator, Logger *logger,
               const WinApiInterface &winapi)
    : ObjectWrapper(nullptr, logger, winapi)
    , _enumerator(enumerator, releaseInterface) {
    if (!next()) {
        // if the first enumeration fails the result is empty
        // we abstract away two possible reasons:
        //   a) The class doesn't exist at all
        //   b) The result is indeed empty
        _enumerator = nullptr;
    }
}

Result::~Result() noexcept {}

Result &Result::operator=(const Result &reference) {
    if (&reference != this) {
        if (_enumerator != nullptr) {
            _enumerator->Release();
        }
        _enumerator = reference._enumerator;
        _current = reference._current;
        _last_error = reference._last_error;
    }
    return *this;
}

bool Result::valid() const { return _current.get() != nullptr; }

namespace {

struct SafeArrayHandleTraits {
    using HandleT = SAFEARRAY *;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.SafeArrayDestroy(value);
    }
};

struct BStringHandleTraits {
    using HandleT = BSTR;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.SysFreeString(value);
    }
};

using SafeArrayHandle = WrappedHandle<SafeArrayHandleTraits>;
using BStringHandle = WrappedHandle<BStringHandleTraits>;

}  // namespace

vector<wstring> Result::names() const {
    Debug(_logger) << "Result::names";
    vector<wstring> result;
    SAFEARRAY *names = nullptr;
    HRESULT res = _current->GetNames(
        nullptr, WBEM_FLAG_ALWAYS | WBEM_FLAG_NONSYSTEM_ONLY, nullptr, &names);

    if (FAILED(res)) {
        throw ComException("Failed to retrieve field names", res, _winapi);
    }

    SafeArrayHandle namesHandle{names, _winapi};
    long lLower = 0, lUpper = 0;
    _winapi.SafeArrayGetLBound(namesHandle.get(), 1, &lLower);
    _winapi.SafeArrayGetUBound(namesHandle.get(), 1, &lUpper);
    result.reserve(static_cast<size_t>(lUpper - lLower + 1));

    for (long i = lLower; i <= lUpper; ++i) {
        BSTR propName = nullptr;
        res = _winapi.SafeArrayGetElement(namesHandle.get(), &i, &propName);
        BStringHandle propHandle{propName, _winapi};
        result.push_back(wstring(propName));
    }

    return result;
}

#if 0
// testing code
// we do not want to loose our time for
// writing real tests for legacy product
bool GlobalTimeout = false;
#endif

bool Result::next() {
    Debug(_logger) << "Result::next";
    if (_enumerator == nullptr) {
        return false;
    }

    IWbemClassObject *obj = nullptr;
    ULONG numReturned = 0;

    HRESULT res = _enumerator->Next(2500, 1, &obj, &numReturned);
#if 0
    // this portion of code is used as embedded testing tool
    // looks terrible, still usable
    namespace fs = std::filesystem;
    std::error_code ec;
    if (fs::exists("timeout.txt", ec) || GlobalTimeout) res = WBEM_S_TIMEDOUT;
#endif

    switch (res) {
        case WBEM_NO_ERROR:
            _current.reset(obj, releaseInterface);
            return true;
        case WBEM_S_FALSE:
            // No more values. The current object remains at the last element so
            // that a call to get continues to work.
            return false;
        case WBEM_S_TIMEDOUT:
            // A timeout occurred before getting the object.
            throw Timeout("WMItimeout");
        default:
            // Any of the four possible errors: WBEM_E_INVALID_PARAMETER,
            // WBEM_E_OUT_OF_MEMORY, WBEM_E_UNEXPECTED or
            // WBEM_E_TRANSPORT_FAILURE. In this case the "current" object isn't
            // changed to guarantee that the Result remains valid.
            _last_error = res;
            return false;
    }
}

// this is correct function, but NOT TESTED
template <>
uint32_t Variant::get() const {
    switch (_value.vt) {
        // 8 bits values
        case VT_UI1:
            return static_cast<uint32_t>(_value.bVal);
        case VT_I1:
            return static_cast<uint32_t>(_value.cVal);
        // 16 bits values
        case VT_UI2:
            return static_cast<uint32_t>(_value.uiVal);
        case VT_I2:
            return static_cast<uint32_t>(_value.iVal);
        // 32 bits values
        case VT_UI4:
            return _value
                .uintVal;  // no conversion here, we expect good type here
        case VT_I4:
            return static_cast<uint32_t>(_value.intVal);

        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
bool Variant::get() const {
    switch (_value.vt) {
        case VT_BOOL:
            return _value.boolVal;
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

// this is original and weird function from the Agent.
// Used to avoid negative numbers in output. Sometimes.
// And satisfy integration tests.
// Microsoft is stupid, because VT_I4 must be interpreted as UNSIGNED sometimes.
// ******************************************************************
// We will use this function in LA just to satisfy integration tests.
// #TODO rename this function to something more clear
template <>
int64_t Variant::get() const {
    switch (_value.vt) {
        case VT_I1:                // has a char
            return _value.iVal;    // load short
        case VT_I2:                // has a short
            return _value.intVal;  // load int32
        case VT_I4:                // has a int32
            return _value.llVal;   // load in64
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
int32_t Variant::get() const {
    switch (_value.vt) {
        // 8 bits values
        case VT_UI1:
            return static_cast<int32_t>(_value.bVal);
        case VT_I1:
            return static_cast<int32_t>(_value.cVal);
        // 16 bits values
        case VT_UI2:
            return static_cast<int32_t>(_value.uiVal);
        case VT_I2:
            return static_cast<int32_t>(_value.iVal);
        // 32 bits values
        case VT_UI4:
            return static_cast<int32_t>(_value.uintVal);
        case VT_I4:
            return _value
                .intVal;  // no conversion here, we expect good type here

        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
uint64_t Variant::get() const {
    switch (_value.vt) {
        case VT_UI8:
            return _value.ullVal;
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
string Variant::get() const {
    switch (_value.vt) {
        case VT_BSTR:
            return to_utf8(_value.bstrVal);
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
float Variant::get() const {
    switch (_value.vt) {
        case VT_R4:
            return _value.fltVal;
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

template <>
double Variant::get() const {
    switch (_value.vt) {
        case VT_R4:
            return _value.fltVal;
        case VT_R8:
            return _value.dblVal;
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

VARTYPE Variant::type() const { return _value.vt; }

template <>
wstring Variant::get() const {
    if (_value.vt & VT_ARRAY) {
        return L"<array>";
    }
    if (_value.vt & VT_VECTOR) {
        return L"<vector>";
    }

    switch (_value.vt) {
        case VT_BSTR:
            return wstring(_value.bstrVal);
        case VT_R4:
            return std::to_wstring(get<float>());
        case VT_R8:
            return std::to_wstring(get<double>());

        case VT_I1:
        case VT_I2:
        case VT_I4:
            // call of *weird* function:
            // in fact it is abs(_value) with extremely high probability
            // We have to use by default uint64_t, because almost all WMI are
            // defined as unsigned.
            return std::to_wstring(get<int64_t>());
        case VT_UI1:
        case VT_UI2:
        case VT_UI4:
            return std::to_wstring(get<uint32_t>());

        case VT_UI8:
            return std::to_wstring(get<uint64_t>());

        case VT_BOOL:
            return std::to_wstring(get<bool>());
        case VT_NULL:
            return L"";
        default:
            throw ComTypeException(string("wrong value type requested: ") +
                                   to_string(_value.vt));
    }
}

class COMManager {
public:
    static void init(Logger *logger, const WinApiInterface &winapi) {
        // this is apparently thread safe in C++11 and in gcc even before that
        // see §6.4 in C++11 standard or §6.7 in C++14
        static COMManager s_Instance(logger, winapi);
    }

    ~COMManager() {
        Debug(_logger) << "COMManager::~COMManager";
        _winapi.CoUninitialize();
    }

private:
    COMManager(Logger *logger, const WinApiInterface &winapi)
        : _logger(logger), _winapi(winapi) {
        Debug(_logger) << "COMManager::COMManager";
        // Dr.Memory reports a memory leak here, despite the fact CoUninitialize
        // does get called. Am I doing something wrong?
        HRESULT res = _winapi.CoInitializeEx(0, COINIT_MULTITHREADED);
        if (FAILED(res)) {
            throw ComException("Failed to initialize COM", res, _winapi);
        }

        res = _winapi.CoInitializeSecurity(
            nullptr,                      // security descriptor
            -1,                           // authentication
            nullptr,                      // authentication services
            nullptr,                      // reserved
            RPC_C_AUTHN_LEVEL_DEFAULT,    // authentication level
            RPC_C_IMP_LEVEL_IMPERSONATE,  // impersonation level
            nullptr,                      // authentication info
            EOAC_NONE,                    // additional capabilities
            nullptr);                     // reserved
        if (FAILED(res)) {
            throw ComException("Failed to initialize COM security", res,
                               _winapi);
        }
    }

    Logger *_logger;
    const WinApiInterface &_winapi;
};

Helper::Helper(Logger *logger, const WinApiInterface &winapi, LPCWSTR path)
    : _locator(nullptr), _path(path), _logger(logger), _winapi(winapi) {
    COMManager::init(logger, winapi);

    _locator = getWBEMLocator();
    _services = connectServer(_locator);
}

Helper::~Helper() {
    if (_locator != nullptr) {
        _locator->Release();
    }
    if (_services != nullptr) {
        _services->Release();
    }
}

IWbemLocator *Helper::getWBEMLocator() {
    IWbemLocator *locator = nullptr;

    HRESULT res =
        _winapi.CoCreateInstance(CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER,
                                 IID_IWbemLocator, (LPVOID *)&locator);

    if (FAILED(res)) {
        throw ComException("Failed to create locator object", res, _winapi);
    }
    return locator;
}

IWbemServices *Helper::connectServer(IWbemLocator *locator) {
    IWbemServices *services = nullptr;

    HRESULT res = locator->ConnectServer(BSTR(_path.c_str()),  // WMI path
                                         nullptr,              // user name
                                         nullptr,              // user password
                                         0,                    // locale
                                         0,                    // security flags
                                         0,                    // authority
                                         0,                    // context object
                                         &services);           // services proxy

    if (FAILED(res)) {
        throw ComException("Failed to connect", res, _winapi);
    }
    return services;
}

void Helper::setProxyBlanket(IWbemServices *services) {
    HRESULT res = _winapi.CoSetProxyBlanket(
        services,                     // the proxy to set
        RPC_C_AUTHN_WINNT,            // authentication service
        RPC_C_AUTHZ_NONE,             // authorization service
        nullptr,                      // server principal name
        RPC_C_AUTHN_LEVEL_CALL,       // authentication level
        RPC_C_IMP_LEVEL_IMPERSONATE,  // impersonation level
        nullptr,                      // client identity
        EOAC_NONE);                   // proxy capabilities

    if (FAILED(res)) {
        throw ComException("Failed to set proxy blanket", res, _winapi);
    }
}

Result Helper::query(LPCWSTR query) {
    IEnumWbemClassObject *enumerator = nullptr;
    // WBEM_FLAG_RETURN_IMMEDIATELY makes the call semi-synchronous which means
    // we can return to caller immediately, iterating the result may break until
    // data is available. WBEM_FLAG_FORWARD_ONLY allows wmi to free the memory
    // of results already iterated, thus reducing memory usage
    HRESULT res = _services->ExecQuery(
        BSTR(L"WQL"), BSTR(query),
        WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY, nullptr,
        &enumerator);

    if (FAILED(res)) {
        throw ComException(
            string("Failed to execute query \"") + to_utf8(query) + "\"", res,
            _winapi);
    }
    return Result(enumerator, _logger, _winapi);
}

Result Helper::getClass(LPCWSTR className) {
    IEnumWbemClassObject *enumerator = nullptr;
    HRESULT res = _services->CreateInstanceEnum(
        BSTR(className), WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,
        nullptr, &enumerator);
    if (FAILED(res)) {
        throw ComException(
            string("Failed to enum class \"") + to_utf8(className) + "\"", res,
            _winapi);
    }
    return Result(enumerator, _logger, _winapi);
}
