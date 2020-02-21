// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef wmiHelper_h
#define wmiHelper_h

#include <winsock2.h>
#include <wbemidl.h>
#include <windows.h>
#include <cstddef>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
#include "WinApiInterface.h"
#include "stringutil.h"

#include <cstdint>

class Logger;
class WinApiInterface;

namespace wmi {

class ComException : public std::runtime_error {
public:
    ComException(const std::string &message, HRESULT result,
                 const WinApiInterface &winapi);
    static std::string resolveError(HRESULT result,
                                    const WinApiInterface &winapi);

private:
    static IErrorInfo *getErrorInfo(const WinApiInterface &winapi);
    std::string toStringHex(HRESULT res);
};

struct ComTypeException : public std::runtime_error {
    ComTypeException(const std::string &message);
};

class Timeout : public std::runtime_error {
public:
    explicit Timeout(const std::string &msg) : std::runtime_error(msg) {}
};

class Variant {
public:
    Variant(const VARIANT &val, Logger *logger, const WinApiInterface &winapi);
    ~Variant();

    template <typename T>
    T get() const;

    VARTYPE type() const;

private:
    VARIANT _value;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

template <>
int32_t Variant::get() const;
template <>
bool Variant::get() const;
template <>
uint32_t Variant::get() const;

template <>
uint64_t Variant::get() const;

template <>
std::string Variant::get() const;
template <>
std::wstring Variant::get() const;
template <>
float Variant::get() const;
template <>
double Variant::get() const;

class ObjectWrapper {
    friend class Helper;

public:
    ObjectWrapper(IWbemClassObject *object, Logger *logger,
                  const WinApiInterface &winapi);

    ObjectWrapper(const ObjectWrapper &reference);
    ~ObjectWrapper() noexcept;
    ObjectWrapper &operator=(const ObjectWrapper &) = delete;

    bool contains(const wchar_t *key) const;

    // retrieve the id of the data type at the specified key. Please see
    // https://msdn.microsoft.com/en-us/library/windows/desktop/ms221170%28v=vs.85%29.aspx
    // for the meaning of the returned id
    int typeId(const wchar_t *key) const;

    // retrieve the value at the specified column key in the current row.
    // if the value can't be converted to the specified data type, an exception
    // is
    // thrown.
    template <typename T>
    T get(const wchar_t *key) const;

protected:
    std::shared_ptr<IWbemClassObject> _current;
    Logger *_logger;
    const WinApiInterface &_winapi;

private:
    VARIANT getVarByKey(const wchar_t *key) const;
};

template <typename T>
T ObjectWrapper::get(const wchar_t *key) const {
    Variant value(getVarByKey(key), _logger, _winapi);
    try {
        return value.get<T>();
    } catch (const ComTypeException &e) {
        throw ComTypeException(std::string("failed to retrieve ") +
                               to_utf8(key) + ": " + e.what());
    }
}

class Result : public ObjectWrapper {
public:
    Result(Logger *logger, const WinApiInterface &winapi);
    Result(IEnumWbemClassObject *enumerator, Logger *logger,
           const WinApiInterface &winapi);
    Result(const Result &reference);
    ~Result() noexcept;

    Result &operator=(const Result &reference);

    std::vector<std::wstring> names() const;

    // proceed to the next element. returns true on success, false if there are
    // no more elements. An exception is thrown if an error happens (i.e.
    // timeout in the query). unless true is returned, the current element is
    // not changed, to once the end of the result has been reached, the iterator
    // stays there.
    bool next();

    // returns the last error that occured during iteration
    HRESULT last_error() const { return _last_error; }

    // return true if this is a valid result. Please note that
    // once a result is valid it remains so, it doesn't become invalid
    // if an error during iteration happens or the last row has been reached.
    bool valid() const;

private:
    std::shared_ptr<IEnumWbemClassObject> _enumerator{NULL};
    HRESULT _last_error{S_OK};
};

class Helper {
public:
    Helper(Logger *logger, const WinApiInterface &winapi,
           LPCWSTR path = L"Root\\Cimv2");

    Helper(const Helper &reference) = delete;
    Helper &operator=(const Helper &reference) = delete;

    ~Helper();

    Result query(LPCWSTR query);
    Result getClass(LPCWSTR className);

private:
    // get a locator that is used to look up WMI namespaces
    IWbemLocator *getWBEMLocator();

    // connect to a wmi namespace. returns a "proxy" to that namespace
    IWbemServices *connectServer(IWbemLocator *locator);

    // sets authentication information on the services proxy
    void setProxyBlanket(IWbemServices *services);

    IWbemLocator *_locator;
    IWbemServices *_services;
    std::wstring _path;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

}  // namespace wmi

#endif  // wmiHelper_h
