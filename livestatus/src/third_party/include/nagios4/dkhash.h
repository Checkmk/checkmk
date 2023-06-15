#ifndef LIBNAGIOS_dkhash_h__
#define LIBNAGIOS_dkhash_h__
#include <errno.h>

/**
 * @file dkhash.h
 * @brief Dual-key hash functions for Nagios
 *
 * Having a dual-key hash function is pretty unusual, but since so
 * much data in Nagios pertains to services (which are uniquely
 * identified based on both host_name and service_description), it
 * makes sense here.
 *
 * @{
 */

/** return flags usable from the callback function of dkhash_walk_data() */
#define DKHASH_WALK_REMOVE 1 /**< Remove the most recently visited object */
#define DKHASH_WALK_STOP   2 /**< Cause walking to stop */

/** return values for dkhash_insert() */
#define DKHASH_OK     0         /**< Success */
#define DKHASH_EDUPE  (-EPERM)  /**< duplicate insert attempted */
#define DKHASH_EPERM  (-EPERM)  /**< duplicate insert attempted */
#define DKHASH_EINVAL (-EINVAL) /**< Invalid parameters passed */
#define DKHASH_ENOMEM (-ENOMEM) /**< Memory allocation failed */

struct dkhash_table;
/** opaque type */
typedef struct dkhash_table dkhash_table;

/**
 * Create a dual-keyed hash-table of the given size
 * Note that it's generally useful to make the table 25-30% larger
 * than the number of items you intend to store, and also note that
 * the 'size' arguments gets rounded up to the nearest power of 2.
 * @param size The desired size of the hash-table.
 */
extern dkhash_table *dkhash_create(unsigned int size);

/**
 * Destroy a dual-keyed hash table
 * @param t The table to destroy
 * @return 0 on success, -1 on errors
 */
extern int dkhash_destroy(dkhash_table *t);

/**
 * Fetch the data associated with a particular key
 * @param t The table to get the data from
 * @param k1 The first key
 * @param k2 The second key
 * @return The data on success, NULL on errors or if data isn't found
 */
extern void *dkhash_get(dkhash_table *t, const char *k1, const char *k2);

/**
 * Insert a new entry into the hash table
 * @param t The hash table
 * @param k1 The first key
 * @param k2 The second key (may be null)
 * @param data The data to insert
 * @return 0 on success, < 0 on errors
 */
extern int dkhash_insert(dkhash_table *t, const char *k1, const char *k2, void *data);

/**
 * Remove data from the hash table
 * Note that this does not free() the pointer to the data stored in the
 * table. It just destroys containers for that data in the hash table.
 * @param t The hash table
 * @param k1 The first key
 * @param k2 The second key
 * @return The removed data on success, or NULL on errors
 */
extern void *dkhash_remove(dkhash_table *t, const char *k1, const char *k2);

/**
 * Call a function once for each item in the hash-table
 * The callback function can return DKHASH_WALK_{REMOVE,STOP} or any
 * OR'ed combination thereof to control the walking procedure, and
 * should return 0 on the normal case.
 * @param t The hash table
 * @param walker The callback function to send the data to
 */
extern void dkhash_walk_data(dkhash_table *t, int (*walker)(void *data));


/**
 * Get number of collisions in hash table
 * Many collisions is a sign of a too small hash table or
 * poor hash-function.
 * @param t The hash table to report on
 * @return The total number of collisions (not duplicates) from inserts
 */
extern unsigned int dkhash_collisions(dkhash_table *t);

/**
 * Get number of items in the hash table
 * @param t The hash table
 * @return Number of items currently in the hash-table
 */
extern unsigned int dkhash_num_entries(dkhash_table *t);

/**
 * Get max number of items stored in the hash table
 * @param t The hash table
 * @return Max number of items stored in hash-table
 */
extern unsigned int dkhash_num_entries_max(dkhash_table *t);

/**
 * Get number of entries added to hash table
 * Note that some of them may have been removed.
 * @param t The hash table
 * @return The number of items added to the table
 */
extern unsigned int dkhash_num_entries_added(dkhash_table *t);

/**
 * Get number of removed items from hash table
 * @param t The hash table
 * @return Number of items removed from hash table
 */
extern unsigned int dkhash_num_entries_removed(dkhash_table *t);

/**
 * Get actual table size (in number of buckets)
 * @param t The hash table
 * @return Number of bucket-slots in hash table
 */
extern unsigned int dkhash_table_size(dkhash_table *t);
/** @} */
#endif /* LIBNAGIOS_dkhash_h__ */
