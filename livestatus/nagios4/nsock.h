#ifndef LIBNAGIOS_nsock_h__
#define LIBNAGIOS_nsock_h__
#include <errno.h>

/**
 * @file nsock.h
 * @brief Nagios socket helper library
 *
 * This is a pretty stupid library, but since so many addons and
 * now Nagios core itself makes use of sockets, we might as well
 * have some simple wrappers for it that handle the most common
 * cases.
 *
 * @{
 */

#define NSOCK_EBIND    (-1)     /**< failed to bind() */
#define NSOCK_ELISTEN  (-2)     /**< failed to listen() */
#define NSOCK_ESOCKET  (-3)     /**< failed to socket() */
#define NSOCK_EUNLINK  (-4)     /**< failed to unlink() */
#define NSOCK_ECONNECT (-5)     /**< failed to connect() */
#define NSOCK_EFCNTL   (-6)     /**< failed to fcntl() */
#define NSOCK_EINVAL (-EINVAL) /**< -22, normally */

/* flags for the various create calls */
#define NSOCK_TCP     (1 << 0)  /**< use tcp mode */
#define NSOCK_UDP     (1 << 1)  /**< use udp mode */
#define NSOCK_UNLINK  (1 << 2)  /**< unlink existing path (only nsock_unix) */
#define NSOCK_REUSE   (1 << 2)  /**< reuse existing address */
#define NSOCK_CONNECT (1 << 3)  /**< connect rather than create */
#define NSOCK_BLOCK   (1 << 4)  /**< socket should be in blocking mode */

/**
 * Grab an error string relating to nsock_unix()
 * @param code The error code return by the nsock library
 * @return An error string describing the error
 */
extern const char *nsock_strerror(int code);

/**
 * Create or connect to a unix socket
 * To control permissions on sockets when NSOCK_LISTEN is specified,
 * callers will have to modify their umask() before (and possibly
 * after) the nsock_unix() call.
 *
 * @param path The path to connect to or create
 * @param flags Various options controlling the mode of the socket
 * @return An NSOCK_E macro on errors, the created socket on succes
 */
extern int nsock_unix(const char *path, unsigned int flags);

/**
 * Write a nul-terminated message to the socket pointed to by sd.
 * This isn't quite the same as dprintf(), which doesn't include
 * the terminating nul byte.
 * @note This function may block, so poll(2) for writability
 * @param sd The socket to write to
 * @param fmt The format string
 * @return Whatever write() returns
 */
extern int nsock_printf_nul(int sd, const char *fmt, ...)
	__attribute__((__format__(__printf__, 2, 3)));

/**
 * Write a printf()-formatted string to the socket pointed to by sd.
 * This is identical to dprintf(), which is unfortunately GNU only.
 * @note This function may block, so poll(2) for writability
 * @param sd The socket to write to
 * @param fmt The format string
 * @return Whatever write() returns
 */
extern int nsock_printf(int sd, const char *fmt, ...)
	__attribute__((__format__(__printf__, 2, 3)));

/** @} */
#endif /* LIBNAGIOS_nsock_h__ */
