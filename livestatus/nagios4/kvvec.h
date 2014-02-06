#ifndef LIBNAGIOS_kvvec_h__
#define LIBNAGIOS_kvvec_h__

/**
 * @file kvvec.h
 * @brief Key/value vector library function and type declarations
 *
 * The kvvec library is nifty as either a configuration meta-format
 * or for IPC purposes. Take a look at the buf2kvvec() and kvvec2buf()
 * pair of functions for the latter.
 * @{
 */

/**
 * key/value pair
 * One of the two major components of the kvvec api
 */
struct key_value {
	char *key;     /**< The key */
	char *value;   /**< The value */
	int key_len;   /**< Length of key */
	int value_len; /**< Length of value */
};

/**
 * key/value vector buffer. Actually just a buffer, but one that gets
 * used as return value and internal tracker for kvvec2buf()
 */
struct kvvec_buf {
	char *buf;             /**< The buffer */
	unsigned long buflen;  /**< Length of buffer */
	unsigned long bufsize; /**< Size of buffer (includes overalloc) */
};

/**
 * key/value vector struct
 * This is the main component of the kvvec library
 * @note This should be made opaque, with a kvvec_foreach() using a
 * callback to iterate over key/value pairs.
 */
struct kvvec {
	struct key_value *kv; /**< The key/value array */
	int kv_alloc;         /**< Allocated size of key/value array */
	int kv_pairs;         /**< Number of key/value pairs */
	int kvv_sorted;        /**< Determines if this kvvec has been sorted */
};

/** Portable initializer for stack-allocated key/value vectors */
#define KVVEC_INITIALIZER { NULL, 0, 0, 0 }

/** Parameters for kvvec_destroy() */
#define KVVEC_FREE_KEYS   1 /**< Free keys when destroying a kv vector */
#define KVVEC_FREE_VALUES 2 /**< Free values when destroying a kv vector */
/** Free both keys and values when destroying a kv vector */
#define KVVEC_FREE_ALL    (KVVEC_FREE_KEYS | KVVEC_FREE_VALUES)

#define KVVEC_ASSIGN      0 /**< Assign from buf in buf2kvvec_prealloc() */
#define KVVEC_COPY        1 /**< Copy from buf in buf2kvvec_prealloc() */
#define KVVEC_APPEND      2 /**< Don't reset kvvec in buf2kvvec_prealloc() */

/**
 * Initialize a previously allocated key/value vector
 *
 * @param kvv The key/value vector to initialize
 * @param hint Number of key/value pairs we expect to store
 * @return Pointer to a struct kvvec, properly initialized
 */
extern struct kvvec *kvvec_init(struct kvvec *kvv, int hint);

/**
 * Create a key/value vector
 *
 * @param hint Number of key/value pairs we expect to store
 * @return Pointer to a struct kvvec, properly initialized
 */
extern struct kvvec *kvvec_create(int hint);

/**
 * Resize a key/value vector
 * Used by kvvec_grow(). If size is smaller than the current number of
 * used key/value slots, -1 is returned.
 *
 * @param[in] kvv The key/value vector to resize
 * @param[in] size The size to grow to
 * @return 0 on success, < 0 on errors
 */
extern int kvvec_resize(struct kvvec *kvv, int size);

/**
 * Grow a key/value vector.
 * Used internally as needed by the kvvec api. If 'hint' is zero, the
 * key/value capacity is increased by a third of the current capacity
 * plus a small constant number. This uses kvvec_resize() internally.
 *
 * @param kvv The key/value vector to grow
 * @param hint The amount of key/value slots we should grow by
 * @return 0 on success, < 0 on errors
 */
extern int kvvec_grow(struct kvvec *kvv, int hint);

/**
 * Return remaining storage capacity of key/value vector
 * @param[in] kvv The key/value vector to check
 * @return Number of key/value pairs that can be stored without growing
 */
extern unsigned int kvvec_capacity(struct kvvec *kvv);

/**
 * Sort a key/value vector alphabetically by key name
 * @param kvv The key/value vector to sort
 * @return 0
 */
extern int kvvec_sort(struct kvvec *kvv);

/**
 * Add a key/value pair to an existing key/value vector, with
 * lengths of strings already calculated
 * @param kvv The key/value vector to add this key/value pair to
 * @param key The key
 * @param keylen Length of the key
 * @param value The value
 * @param valuelen Length of the value
 * @return 0 on success, < 0 on errors
 */
extern int kvvec_addkv_wlen(struct kvvec *kvv, const char *key, int keylen, const char *value, int valuelen);

/**
 * Shortcut to kvvec_addkv_wlen() when lengths aren't known
 * @param kvv The key/value vector to add this key/value pair to
 * @param key The key
 * @param value The value
 * @return 0 on success, < 0 on errors
 */
#define kvvec_addkv(kvv, key, value) kvvec_addkv_wlen(kvv, key, 0, value, 0)

/**
 * Walk each key/value pair in a key/value vector, sending them
 * as arguments to a callback function. The callback function has
 * no control over the iteration process and must not delete or
 * modify the key/value vector it's operating on.
 * @param kvv The key/value vector to walk
 * @param arg Extra argument to the callback function
 * @param callback Callback function
 * @return 0 on success, < 0 on errors
 */
extern int kvvec_foreach(struct kvvec *kvv, void *arg, int (*callback)(struct key_value *, void *));

/**
 * Destroy a key/value vector
 * @param kvv The key/value vector to destroy
 * @param flags or'ed combination of KVVEC_FREE_{KEYS,VALUES}, or KVVEC_FREE_ALL
 * @return 0 on success, < 0 on errors
 */
extern int kvvec_destroy(struct kvvec *kvv, int flags);

/**
 * Free key/value pairs associated with a key/value vector
 * @param kvv The key/value vector to operate on
 * @param flags flags or'ed combination of KVVEC_FREE_{KEYS,VALUES}, or KVVEC_FREE_ALL
 */
void kvvec_free_kvpairs(struct kvvec *kvv, int flags);

/**
 * Create a linear buffer of all the key/value pairs and
 * return it as a kvvec_buf. The caller must free() all
 * pointers in the returned kvvec_buf
 * (FIXME: add kvvec_buf_destroy(), or move this and its counterpart
 * out of the kvvec api into a separate one)
 *
 * @param kvv The key/value vector to convert
 * @param kv_sep Character separating keys and their values
 * @param pair_sep Character separating key/value pairs
 * @param overalloc Integer determining how much extra data we should
 *                  allocate. The overallocated memory is filled with
 *                  nul bytes.
 * @return A pointer to a newly created kvvec_buf structure
 */
extern struct kvvec_buf *kvvec2buf(struct kvvec *kvv, char kv_sep, char pair_sep, int overalloc);

/**
 * Create a key/value vector from a pre-parsed buffer. Immensely
 * useful for ipc in combination with kvvec2buf().
 *
 * @param str The buffer to convert to a key/value vector
 * @param len Length of buffer to convert
 * @param kvsep Character separating key and value
 * @param pair_sep Character separating key/value pairs
 * @param flags bitmask. See KVVEC_{ASSIGN,COPY,APPEND} for values
 * @return The created key/value vector
 */
extern struct kvvec *buf2kvvec(char *str, unsigned int len, const char kvsep, const char pair_sep, int flags);

/**
 * Parse a buffer into the pre-allocated key/value vector. Immensely
 * useful for ipc in combination with kvvec2buf().
 *
 * @param kvv A pre-allocated key/value vector to populate
 * @param str The buffer to convert to a key/value vector
 * @param len Length of buffer to convert
 * @param kvsep Character separating key and value
 * @param pair_sep Character separating key/value pairs
 * @param flags bitmask. See KVVEC_{ASSIGN,COPY,APPEND} for values
 * @return The number of pairs in the created key/value vector
 */
extern int buf2kvvec_prealloc(struct kvvec *kvv, char *str, unsigned int len, const char kvsep, const char pair_sep, int flags);
/** @} */
#endif /* INCLUDE_kvvec_h__ */
