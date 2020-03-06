// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef OutputProxy_h
#define OutputProxy_h

#include <cstdio>
#include <vector>
#include "Crypto.h"

class Logger;
class WinApiInterface;

class OutputProxy {
public:
    virtual void output(const char *format, ...) = 0;

    // write data without any modification to underlying buffer
    virtual void writeBinary(const char *buffer, size_t size) = 0;
    virtual void flush(bool last) = 0;
};

class FileOutputProxy : public OutputProxy {
public:
    FileOutputProxy(FILE *file);

    virtual void output(const char *format, ...) override;
    virtual void writeBinary(const char *buffer, size_t size) override;
    virtual void flush(bool last) override;

private:
    FILE *_file;
};

class BufferedSocketProxy : public OutputProxy {
public:
    static const size_t DEFAULT_BUFFER_SIZE = 16384L;

    BufferedSocketProxy(SOCKET socket, Logger *logger,
                        const WinApiInterface &winapi);
    BufferedSocketProxy(const BufferedSocketProxy &) = delete;
    BufferedSocketProxy &operator=(const BufferedSocketProxy &) = delete;

    void setSocket(SOCKET socket);

    virtual void output(const char *format, ...) override;
    virtual void writeBinary(const char *buffer, size_t size) override;
    virtual void flush(bool last) override;

protected:
    std::vector<char> &buffer() { return _buffer; }
    size_t length() const { return _length; }
    bool flushInt();

private:
    SOCKET _socket;
    std::vector<char> _buffer;
    size_t _length{0};
    size_t _collect_size;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

// can you feel the java?
class EncryptingBufferedSocketProxy : public BufferedSocketProxy {
public:
    EncryptingBufferedSocketProxy(SOCKET socket, const std::string &passphrase,
                                  Logger *logger,
                                  const WinApiInterface &winapi);
    virtual void output(const char *format, ...) override;
    // writeBinary is NOT overridden so calls to it are not encrypted!
    virtual void flush(bool last) override;

private:
    Crypto _crypto;
    std::vector<char> _plain;
    size_t _blockSize;
    size_t _written;
};

#endif  // OutputProxy_h
