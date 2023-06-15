#ifndef LIBNAGIOS_iocache_h__
#define LIBNAGIOS_iocache_h__
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>

/**
 * @file iocache.h
 * @brief I/O cache function declarations
 *
 * The I/O cache library is useful for reading large chunks of data
 * from sockets and utilizing parts of that data based on either
 * size or a magic delimiter.
 *
 * @{
 */

/** opaque type for iocache operations */
struct iocache;
typedef struct iocache iocache;

/**
 * Destroys an iocache object, freeing all memory allocated to it.
 * @param ioc The iocache object to destroy
 */
extern void iocache_destroy(iocache *ioc);

/**
 * Resets an iocache struct, discarding all data in it without free()'ing
 * any memory.
 *
 * @param[in] ioc The iocache struct to reset
 */
extern void iocache_reset(iocache *ioc);

/**
 * Resizes the buffer in an io cache
 * @param ioc The io cache to resize
 * @param new_size The new size of the io cache
 * @return 0 on success, -1 on errors
 */
extern int iocache_resize(iocache *ioc, unsigned long new_size);

/**
 * Grows an iocache object
 * This uses iocache_resize() internally
 * @param[in] ioc The iocache to grow
 * @param[in] increment How much to increase it
 * @return 0 on success, -1 on errors
 */
extern int iocache_grow(iocache *ioc, unsigned long increment);

/**
 * Returns the total size of the io cache
 * @param[in] ioc The iocache to inspect
 * @return The size of the io cache. If ioc is null, 0 is returned
 */
extern unsigned long iocache_size(iocache *ioc);

/**
 * Returns remaining read capacity of the io cache
 * @param ioc The io cache to operate on
 * @return The number of bytes available to read
 */
extern unsigned long iocache_capacity(iocache *ioc);

/**
 * Return the amount of unread but stored data in the io cache
 * @param ioc The io cache to operate on
 * @return Number of bytes available to read
 */
extern unsigned long iocache_available(iocache *ioc);

/**
 * Use a chunk of data from iocache based on size. The caller
 * must take care not to write beyond the end of the requested
 * buffer, or Bad Things(tm) will happen.
 *
 * @param ioc The io cache we should use data from
 * @param size The size of the data we want returned
 * @return NULL on errors (insufficient data, fe). pointer on success
 */
extern char *iocache_use_size(iocache *ioc, unsigned long size);

/**
 * Use a chunk of data from iocache based on delimiter. The
 * caller must take care not to write beyond the end of the
 * requested buffer, if any is returned, or Bad Things(tm) will
 * happen.
 *
 * @param ioc The io cache to use data from
 * @param delim The delimiter
 * @param delim_len Length of the delimiter
 * @param size Length of the returned buffer
 * @return NULL on errors (delimiter not found, insufficient data). pointer on success
 */
extern char *iocache_use_delim(iocache *ioc, const char *delim, size_t delim_len, unsigned long *size);

/**
 * Forget that a specified number of bytes have been used.
 * @param ioc The io cache that you want to un-use data in
 * @param size The number of bytes you want to forget you've seen
 * @return -1 if there was an error, 0 otherwise.
 */
extern int iocache_unuse_size(iocache *ioc, unsigned long size);

/**
 * Creates the iocache object, initializing it with the given size
 * @param size Initial size of the iocache buffer
 * @return Pointer to a valid iocache object
 */
extern iocache *iocache_create(unsigned long size);

/**
 * Read data into the iocache buffer
 * @param ioc The io cache we should read into
 * @param fd The filedescriptor we should read from
 * @return The number of bytes read on success. < 0 on errors
 */
extern int iocache_read(iocache *ioc, int fd);

/**
 * Add data to the iocache buffer
 * The data is copied, so it can safely be taken from the stack in a
 * function that returns before the data is used.
 * If the io cache is too small to hold the data, -1 will be returned.
 *
 * @param[in] ioc The io cache to add to
 * @param[in] buf Pointer to the data we should add
 * @param[in] len Length (in bytes) of data pointed to by buf
 * @return iocache_available(ioc) on success, -1 on errors
 */
extern int iocache_add(iocache *ioc, char *buf, unsigned int len);

/**
 * Like sendto(), but sends all cached data prior to the requested
 *
 * @param[in] ioc The iocache to send, or cache data in
 * @param[in] fd The file descriptor to send to
 * @param[in] buf Pointer to the data to send
 * @param[in] len Length (in bytes) of data to send
 * @param[in] flags Flags passed to sendto(2)
 * @param[in] dest_addr Destination address
 * @param[in] addrlen size (in bytes) of dest_addr
 * @return bytes sent on success, -ERRNO on errors
 */
extern int iocache_sendto(iocache *ioc, int fd, char *buf, unsigned int len, int flags, const struct sockaddr *dest_addr, socklen_t addrlen);

/**
 * Like send(2), but sends all cached data prior to the requested
 * This function uses iocache_sendto() internally, but can only be
 * used on connected sockets or open()'ed files.
 *
 * @param[in] ioc The iocache to send, or cache data in
 * @param[in] fd The file descriptor to send to
 * @param[in] buf Pointer to the data to send
 * @param[in] len Length (in bytes) of data to send
 * @param[in] flags Flags passed to sendto(2)
 * @return bytes sent on success, -ERRNO on errors
 */
static inline int iocache_send(iocache *ioc, int fd, char *buf, unsigned int len, int flags)
{
	return iocache_sendto(ioc, fd, buf, len, flags, NULL, 0);
}

/**
 * Like write(2), but sends all cached data prior to the requested
 * This function uses iocache_send() internally.
 *
 * @param[in] ioc The iocache to send, or cache data in
 * @param[in] fd The file descriptor to send to
 * @param[in] buf Pointer to the data to send
 * @param[in] len Length (in bytes) of data to send
 * @return bytes sent on success, -ERRNO on errors
 */
static inline int iocache_write(iocache *ioc, int fd, char *buf, unsigned int len)
{
	return iocache_send(ioc, fd, buf, len, 0);
}
#endif /* INCLUDE_iocache_h__ */
/** @} */
