#ifndef LIBNAGIOS_nspath_h__
#define LIBNAGIOS_nspath_h__
#ifndef _GNU_SOURCE
# ifndef NODOXY
#  define _GNU_SOURCE 1
# endif
#endif
#include <errno.h>
#include <sys/stat.h>
#include "snprintf.h"

/**
 * @file nspath.h
 * @brief path handling functions
 *
 * This library handles path normalization and resolution. It's nifty
 * if you want to turn relative paths into absolute ones, or if you
 * want to make insane ones sane, but without chdir()'ing your way
 * around the filesystem.
 *
 * @{
 */

/**
 * Normalize a path
 * By "normalize", we mean that we convert dot-slash and dot-dot-slash
 * embedded components into a legible continuous string of characters.
 * Leading and trailing slashes are kept exactly as they are in input,
 * but with sequences of slashes reduced to a single one.
 *
 * "foo/bar/.././lala.txt" becomes "foo/lala.txt"
 * "../../../../bar/../foo/" becomes "/foo/"
 * "////foo////././bar" becomes "/foo/bar"
 * @param orig_path The path to normalize
 * @return A newly allocated string containing the normalized path
 */
extern char *nspath_normalize(const char *orig_path);

/**
 * Make the "base"-relative path "rel_path" absolute.
 * Turns the relative path "rel_path" into an absolute path and
 * resolves it as if we were currently in "base". If "base" is
 * NULL, the current working directory is used. If "base" is not
 * null, it should be an absolute path for the result to make
 * sense.
 *
 * @param rel_path The relative path to convert
 * @param base The base directory (if NULL, we use current working dir)
 * @return A newly allocated string containing the absolute path
 */
extern char *nspath_absolute(const char *rel_path, const char *base);

/**
 * Canonicalize the "base"-relative path "rel_path".
 * errno gets properly set in case of errors.
 * @param rel_path The path to transform
 * @param base The base we should operate relative to
 * @return Newly allocated canonical path on succes, NULL on errors
 */
extern char *nspath_real(const char *rel_path, const char *base);

/**
 * Get absolute dirname of "path", relative to "base"
 * @param path Full path to target object (file or subdir)
 * @param base The base directory (if NULL, we use current working dir)
 * @return NULL on errors, allocated absolute directory name on success
 */
extern char *nspath_absolute_dirname(const char *path, const char *base);


/**
 * Recursively create a directory, just like mkdir_p would.
 * @note This function *will* taint errno with ENOENT if any path
 * component has to be created.
 * @note If "path" has a trailing slash, NSPATH_MKDIR_SKIP_LAST
 * won't have any effect. That's considered a feature, since the
 * option is designed so one can send a file-path to the function
 * and have it create the directory structure for it.
 * @param path Path to create, in normalized form
 * @param mode Filemode (same as mkdir() takes)
 * @param options Options flag. See NSPATH_MKDIR_* for or-able options
 * @return 0 on success, -1 on errors and errno will hold error code
 *   from either stat() or mkdir().
 */
extern int nspath_mkdir_p(const char *path, mode_t mode, int options);

/** Don't mkdir() last element of path when calling nspath_mkdir_p() */
#define NSPATH_MKDIR_SKIP_LAST (1 << 0)

/** @} */
#endif
