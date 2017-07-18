// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef OutputProxy_h
#define OutputProxy_h

#include <winsock2.h>
#include <cstdio>
#include <vector>
#include "Crypto.h"

class LoggerAdaptor;

class OutputProxy {
public:
    virtual void output(const char *format, ...) = 0;

    // write data without any modification to underlying buffer
    virtual void writeBinary(const char *buffer, size_t size) = 0;
    virtual void flush(bool last) = 0;
};

class FileOutputProxy : public OutputProxy {
    FILE *_file;

public:
    FileOutputProxy(FILE *file);

    virtual void output(const char *format, ...) override;
    virtual void writeBinary(const char *buffer, size_t size) override;
    virtual void flush(bool last) override;
};

class BufferedSocketProxy : public OutputProxy {
    SOCKET _socket;
    std::vector<char> _buffer;
    size_t _length{0};
    size_t _collect_size;
    const LoggerAdaptor &_logger;

protected:
    std::vector<char> &buffer() { return _buffer; }
    size_t length() const { return _length; }

public:
    static const size_t DEFAULT_BUFFER_SIZE = 16384L;

public:
    BufferedSocketProxy(SOCKET socket,
			const LoggerAdaptor &logger);

    void setSocket(SOCKET socket);

    virtual void output(const char *format, ...) override;
    virtual void writeBinary(const char *buffer, size_t size) override;
    virtual void flush(bool last) override;

protected:
    bool flushInt();

private:
    BufferedSocketProxy(const BufferedSocketProxy &reference) = delete;
    BufferedSocketProxy &operator=(const BufferedSocketProxy &reference) =
        delete;
};

// can you feel the java?
class EncryptingBufferedSocketProxy : public BufferedSocketProxy {
    Crypto _crypto;

    std::vector<char> _plain;
    size_t _blockSize;
    size_t _written;

public:
    EncryptingBufferedSocketProxy(SOCKET socket, const std::string &passphrase,
				  const LoggerAdaptor &logger);
    virtual void output(const char *format, ...) override;
    // writeBinary is NOT overridden so calls to it are not encrypted!
    virtual void flush(bool last) override;
};

#endif  // OutputProxy_h
