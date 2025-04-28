#include <string>

class ListenSocket {
public:
    ListenSocket(int port, bool supportIPV6);

    bool supportsIPV4() const;
    bool supportsIPV6() const;

    SOCKET acceptConnection() const;

    sockaddr_storage address(SOCKET connection) const;

private:
    SOCKET init_listen_socket(int port);
    bool check_only_from(const SOCKADDR &ip) const;
    SOCKET RemoveSocketInheritance(SOCKET oldsocket) const;

    const bool _use_ipv6;
    SOCKET _socket;
    bool _supports_ipv4;
};

ListenSocket::ListenSocket(int port, bool supportIPV6)
    : _use_ipv6(supportIPV6)
    , _socket(init_listen_socket(port))
    , _supports_ipv4(true) {}

bool ListenSocket::supportsIPV4() const { return _supports_ipv4; }

bool ListenSocket::supportsIPV6() const { return _use_ipv6; }

SOCKET ListenSocket::RemoveSocketInheritance(SOCKET oldsocket) const {
    HANDLE newhandle;
    // FIXME: this may not work on some setups!
    //   sockets are no simple handles, they may have additional information
    //   attached by layered
    //   service providers. This drops all of that information!
    //   Also, sockets are supposedly non-inheritable anyway
    ::DuplicateHandle(::GetCurrentProcess(), (HANDLE)oldsocket,
                      ::GetCurrentProcess(), &newhandle, 0, FALSE,
                      DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);
    return (SOCKET)newhandle;
}

bool ListenSocket::check_only_from(const SOCKADDR &ip) const {
    return true;  // no restriction set
}

SOCKET ListenSocket::init_listen_socket(int port) {
    // We need to create a socket which listens for incoming connections
    // but we do not want that it is inherited to child processes
    // (local/plugins)
    // Therefore we open the socket - this one is inherited by default
    // Now we duplicate this handle and explicitly say that inheritance is
    // forbidden
    // and use the duplicate from now on
    SOCKET tmp_s = ::socket(_use_ipv6 ? AF_INET6 : AF_INET, SOCK_STREAM, 0);
    if (tmp_s == INVALID_SOCKET) {
        int error_id = ::WSAGetLastError();
        exit(1);
    }
    SOCKET s = RemoveSocketInheritance(tmp_s);

    int addr_size = 0;
    SOCKADDR *addr = nullptr;
    SOCKADDR_IN6 addr6{0};
    SOCKADDR_IN addr4{0};

    int optval = 1;
    ::setsockopt(s, SOL_SOCKET, SO_REUSEADDR,
                 reinterpret_cast<const char *>(&optval), sizeof(optval));
    if (_use_ipv6) {
        addr6.sin6_port = htons(port);
        int v6only = 0;
        if (::setsockopt(s, IPPROTO_IPV6, IPV6_V6ONLY, (char *)&v6only,
                         sizeof(int)) != 0) {
            _supports_ipv4 = false;
        }
        addr = reinterpret_cast<SOCKADDR *>(&addr6);
        addr->sa_family = AF_INET6;
        addr_size = sizeof(SOCKADDR_IN6);
    } else {
        addr4.sin_port = ::htons(port);
        addr4.sin_addr.S_un.S_addr = ADDR_ANY;
        addr = reinterpret_cast<SOCKADDR *>(&addr4);
        addr->sa_family = AF_INET;
        addr_size = sizeof(SOCKADDR_IN);
    }

    if (SOCKET_ERROR == ::bind(s, addr, addr_size)) {
        int error_id = ::WSAGetLastError();
        exit(1);
    }

    if (SOCKET_ERROR == ::listen(s, 5)) {
        exit(1);
    }

    return s;
}

sockaddr_storage ListenSocket::address(SOCKET connection) const {
    sockaddr_storage addr;
    int addrlen = sizeof(sockaddr_storage);
    ::getpeername(connection, (sockaddr *)&addr, &addrlen);
    return addr;
}

SOCKET ListenSocket::acceptConnection() const {
    // Loop forever.
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(_socket, &fds);
    TIMEVAL timeout = {0, 500000};

    // FIXME: every failed connect resets the timeout so technically this may
    // never return
    while (1 == ::select(1, &fds, NULL, NULL, &timeout)) {
        int addr_len = 0;
        SOCKADDR *remoteAddr = nullptr;
        SOCKADDR_IN6 addr6{0};
        SOCKADDR_IN addr4{0};

        if (_use_ipv6) {
            remoteAddr = reinterpret_cast<SOCKADDR *>(&addr6);
            remoteAddr->sa_family = AF_INET6;
            addr_len = sizeof(SOCKADDR_IN6);
        } else {
            remoteAddr = reinterpret_cast<SOCKADDR *>(&addr4);
            remoteAddr->sa_family = AF_INET;
            addr_len = sizeof(SOCKADDR_IN);
        }

        SOCKET rawSocket = ::accept(_socket, remoteAddr, &addr_len);
        auto connection = RemoveSocketInheritance(rawSocket);
        if (connection && check_only_from(*remoteAddr)) {
            return connection;
        }
    }

    return {};
}

int ExternalPort::xmain(int PORT) {
    int server_fd, new_socket;
    sockaddr_in address{};
    int opt = 1;
    int addrlen = sizeof(address);
    char buffer[1024] = {0};
    const char *hello = "Hello from server\nEND\n";

    // Creating socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Forcefully attaching socket to the port 8080
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (char *)&opt,
                   sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Forcefully attaching socket to the port 8080
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }
    if (listen(server_fd, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }
    if ((new_socket = accept(server_fd, (struct sockaddr *)&address,
                             (socklen_t *)&addrlen)) < 0) {
        perror("accept");
        exit(EXIT_FAILURE);
    }
    send(new_socket, hello, strlen(hello), 0);
    closesocket(new_socket);

    return 0;
}

