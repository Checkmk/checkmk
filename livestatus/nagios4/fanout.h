#ifndef LIBNAGIOS_fanout_h__
#define LIBNAGIOS_fanout_h__
#include "lnag-utils.h"

/**
 * @file fanout.h
 * @brief Simple fanout table implementation
 *
 * Fanouts are useful to hold short-lived integer-indexed data where
 * the keyspan between smallest and largest key can be too large and
 * change too often for it to be practical to maintain a growing array.
 * If you think of it as a hash-table optimized for unsigned longs you've
 * got the right idea.
 *
 * @{
 */

NAGIOS_BEGIN_DECL

/** Primary (opaque) type for this api */
typedef struct fanout_table fanout_table;

/**
 * Create a fanout table
 * @param[in] size The size of the table. Preferrably a power of 2
 * @return Pointer to a newly created table
 */
extern fanout_table *fanout_create(unsigned long size);

/**
 * Destroy a fanout table, with optional destructor.
 * This function will iterate over all the entries in the fanout
 * table and remove them, one by one. If 'destructor' is not NULL,
 * it will be called on each and every object in the table. Note that
 * 'free' is a valid destructor.
 *
 * @param[in] t The fanout table to destroy
 * @param[in] destructor Function to call on data pointers in table
 */
extern void fanout_destroy(fanout_table *t, void (*destructor)(void *));

/**
 * Return a pointer from the fanout table t
 *
 * @param[in] t table to fetch from
 * @param[in] key key to fetch
 * @return NULL on errors; Pointer to data on success
 */
extern void *fanout_get(fanout_table *t, unsigned long key);

/**
 * Add an entry to the fanout table.
 * Note that we don't check if the key is unique. If it isn't,
 * fanout_remove() will remove the latest added first.
 *
 * @param[in] t fanout table to add to
 * @param[in] key Key for this entry
 * @param[in] data Data to add. Must not be NULL
 * @return 0 on success, -1 on errors
 */
extern int fanout_add(fanout_table *t, unsigned long key, void *data);

/**
 * Remove an entry from the fanout table and return its data.
 *
 * @param[in] t fanout table to look in
 * @param[key] The key whose data we should locate
 * @return Pointer to the data stored on success; NULL on errors
 */
extern void *fanout_remove(fanout_table *t, unsigned long key);
NAGIOS_END_DECL
/** @} */
#endif
