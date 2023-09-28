/* lib/iobroker.h.  Generated from iobroker.h.in by configure.  */
#ifndef LIBNAGIOS_iobroker_h__
#define LIBNAGIOS_iobroker_h__

/**
 * @file iobroker.h
 * @brief I/O broker library function declarations
 *
 * The I/O broker library handles multiplexing between hundreds or
 * thousands of sockets with a few simple calls. It's designed to
 * be as lightweight as possible so as to not cause memory bloat,
 * and is therefore highly suitable for use by processes that are
 * fork()-intensive.
 *
 * @{
 */

#define IOBROKER_USES_EPOLL 1
/* #undef IOBROKER_USES_POLL */
/* #undef IOBROKER_USES_SELECT */

#if (_POSIX_C_SOURCE - 0) >= 200112L
#include <poll.h>
# define IOBROKER_POLLIN POLLIN
# define IOBROKER_POLLPRI POLLPRI
# define IOBROKER_POLLOUT POLLOUT

# define IOBROKER_POLLERR POLLERR
# define IOBROKER_POLLHUP POLLHUP
# define IOBROKER_POLLNVAL POLLNVAL
#else
# define IOBROKER_POLLIN   0x001 /* there is data to read */
# define IOBROKER_POLLPRI  0x002 /* there is urgent data to read */
# define IOBROKER_POLLOUT  0x004 /* writing now will not block */

# define IOBROKER_POLLERR  0x008 /* error condition */
# define IOBROKER_POLLHUP  0x010 /* hung up */
# define IOBROKER_POLLNVAL 0x020 /* invalid polling request */
#endif

/** return codes */
#define IOBROKER_SUCCESS    0
#define IOBROKER_ENOSET   (-1)
#define IOBROKER_ENOINIT  (-2)
#define IOBROKER_ELIB     (-3)
#define IOBROKER_EALREADY (-EALREADY)
#define IOBROKER_EINVAL   (-EINVAL)


/** Flags for iobroker_destroy() */
#define IOBROKER_CLOSE_SOCKETS 1

/* Opaque type. Callers needn't worry about this */
struct iobroker_set;
typedef struct iobroker_set iobroker_set;

/**
 * Get a string describing the error in the last iobroker call.
 * The returned string must not be free()'d.
 * @param error The error code
 * @return A string describing the meaning of the error code
 */
extern const char *iobroker_strerror(int error);

/**
 * Create a new socket set
 * @return An iobroker_set on success. NULL on errors.
 */
extern iobroker_set *iobroker_create(void);

/**
 * Published utility function used to determine the max number of
 * file descriptors this process can keep open at any one time.
 * @return Max number of filedescriptors we can keep open
 */
extern int iobroker_max_usable_fds(void);

/**
 * Register a socket for input polling with the broker.
 *
 * @param iobs The socket set to add the socket to.
 * @param sd The socket descriptor to add
 * @param arg Argument passed to input handler on available input
 * @param handler The callback function to call when input is available
 *
 * @return 0 on succes. < 0 on errors.
 */
extern int iobroker_register(iobroker_set *iobs, int sd, void *arg, int (*handler)(int, int, void *));


/**
 * Register a socket for output polling with the broker
 * @note There's no guarantee that *ALL* data is writable just
 * because the socket won't block you completely.
 *
 * @param iobs The socket set to add the socket to.
 * @param sd The socket descriptor to add
 * @param arg Argument passed to output handler on ready-to-write
 * @param handler The function to call when output won't block
 *
 * @return 0 on success. < 0 on errors
 */
extern int iobroker_register_out(iobroker_set *iobs, int sd, void *arg, int (*handler)(int, int, void *));

/**
 * Check if a particular filedescriptor is registered with the iobroker set
 * @param[in] iobs The iobroker set the filedescriptor should be member of
 * @param[in] fd The filedescriptor to check for
 * @return 1 if the filedescriptor is registered and 0 otherwise
 */
extern int iobroker_is_registered(iobroker_set *iobs, int fd);

/**
 * Getter function for number of file descriptors registered in
 * the set specified.
 * @param iobs The io broker set to query
 * @return Number of file descriptors registered in the set
 */
extern int iobroker_get_num_fds(iobroker_set *iobs);

/**
 * Getter function for the maximum amount of file descriptors this
 * set can handle.
 * @param iobs The io broker set to query
 * @return Max file descriptor capacity for the set
 */
extern int iobroker_get_max_fds(iobroker_set *iobs);

/**
 * Unregister a socket for input polling with the broker.
 *
 * @param iobs The socket set to remove the socket from
 * @param sd The socket descriptor to remove
 * @return 0 on succes. < 0 on errors.
 */
extern int iobroker_unregister(iobroker_set *iobs, int sd);

/**
 * Deregister a socket for input polling with the broker
 * (this is identical to iobroker_unregister())
 * @param iobs The socket set to remove the socket from
 * @param sd The socket descriptor to remove
 * @return 0 on success. < 0 on errors.
 */
extern int iobroker_deregister(iobroker_set *iobs, int sd);

/**
 * Unregister and close(2) a socket registered for input with the
 * broker. This is a convenience function which exists only to avoid
 * doing multiple calls when read() returns 0, as closed sockets must
 * always be removed from the socket set to avoid consuming tons of
 * cpu power from iterating "too fast" over the file descriptors.
 *
 * @param iobs The socket set to remove the socket from
 * @param sd The socket descriptor to remove and close
 * @return 0 on success. < 0 on errors
 */
extern int iobroker_close(iobroker_set *iobs, int sd);

/**
 * Destroy a socket set as created by iobroker_create
 * @param iobs The socket set to destroy
 * @param flags If set, close(2) all registered sockets
 */
extern void iobroker_destroy(iobroker_set *iobs, int flags);

/**
 * Wait for input on any of the registered sockets.
 * @param iobs The socket set to wait for.
 * @param timeout Timeout in milliseconds. -1 is "wait indefinitely"
 * @return -1 on errors, or number of filedescriptors with input
 */
extern int iobroker_poll(iobroker_set *iobs, int timeout);
#endif /* INCLUDE_iobroker_h__ */
/** @} */
