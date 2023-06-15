#ifndef LIBNAGIOS_nsutils_h__
#define LIBNAGIOS_nsutils_h__
#include <sys/types.h>

/**
 * @file nsutils.h
 * @brief Non-Standard (or Nagios) utility functions and macros.
 *
 * This is where we house all helpers and macros that fall outside
 * the "standard-ish" norm. The prefixes "nsu_" and NSU_ are
 * reserved for this purpose, so we avoid clashing with other
 * applications that may have similarly-acting functions with
 * identical names.
 *
 * The functions already here lack the nsu_ prefix for backwards
 * compatibility reasons. It's possible we'll have to fix that
 * some day, but let's leave that for later.
 *
 * @{
 */

/** Macro for dynamically increasing vector lengths */
#define alloc_nr(x) (((x)+16)*3/2)

/**
 * Check if a number is a power of 2
 * @param x The number to check
 * @return 1 if the number is a power of 2, 0 if it's not
 */
static inline int nsu_ispow2(unsigned int x)
{
	return x > 1 ? !(x & (x - 1)) : 0;
}

/**
 * Round up to a power of 2
 * Yes, this is the most cryptic function name in all of Nagios, but I
 * like it, so shush.
 * @param r The number to round up
 * @return r, rounded up to the nearest power of 2.
 */
static inline unsigned int rup2pof2(unsigned int r)
{
	r--;
	if (!r)
		return 2;
	r |= r >> 1;
	r |= r >> 2;
	r |= r >> 4;
	r |= r >> 8;
	r |= r >> 16;

	return r + 1;
}

/**
 * Grab a random unsigned int in the range between low and high.
 * Note that the PRNG has to be seeded prior to calling this.
 * @param low The lower bound, inclusive
 * @param high The higher bound, inclusive
 * @return An unsigned integer in the mathematical range [low, high]
 */
static inline unsigned int ranged_urand(unsigned int low, unsigned int high)
{
	return low + (rand() * (1.0 / (RAND_MAX + 1.0)) * (high - low));
}

/**
 * Get number of online cpus
 * @return Active cpu cores detected on success. 0 on failure.
 */
extern int real_online_cpus(void);

/**
 * Wrapper for real_online_cpus(), returning 1 in case we can't
 * detect any active cpus.
 * @return Number of active cpu cores on success. 1 on failure.
 */
extern int online_cpus(void);

/**
 * Create a short-lived string in stack-allocated memory
 * The number and size of strings is limited (currently to 256 strings of
 * 32 bytes each), so beware and use this sensibly. Intended for
 * number-to-string conversion and other short strings.
 * @note The returned string must *not* be free()'d!
 * @param[in] fmt The format string
 * @return A pointer to the formatted string on success. Undefined on errors
 */
extern const char *mkstr(const char *fmt, ...)
	__attribute__((__format__(__printf__, 1, 2)));

/**
 * Calculate the millisecond delta between two timeval structs
 * @param[in] start The start time
 * @param[in] stop The stop time
 * @return The millisecond delta between the two structs
 */
extern int tv_delta_msec(const struct timeval *start, const struct timeval *stop);


/**
 * Get timeval delta as seconds
 * @param start The start time
 * @param stop The stop time
 * @return time difference in fractions of seconds
 */
extern float tv_delta_f(const struct timeval *start, const struct timeval *stop);

/** @} */
#endif /* LIBNAGIOS_nsutils_h__ */
