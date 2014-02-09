/************************************************************************
 *
 * SKIPLIST.H - Skiplist data structures and functions
 *
 *
 * License:
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 ************************************************************************/

#ifndef LIBNAGIOS_skiplist_h__
#define LIBNAGIOS_skiplist_h__
#include "lnag-utils.h"

/**
 * @file skiplist.h
 * @brief Skiplist library functions
 *
 * http://en.wikipedia.org/wiki/Skiplist
 *
 * @{
 */

#define SKIPLIST_OK              0 /**< A ok */
#define SKIPLIST_ERROR_ARGS      1 /**< Bad arguments */
#define SKIPLIST_ERROR_MEMORY    2 /**< Memory error */
#define SKIPLIST_ERROR_DUPLICATE 3 /**< Trying to insert non-unique item */

NAGIOS_BEGIN_DECL

struct skiplist_struct;
typedef struct skiplist_struct skiplist;

/**
 * Return number of items currently in the skiplist
 * @param list The list to investigate
 * @return number of items in list
 */
unsigned long skiplist_num_items(skiplist *list);

/**
 * Create a new skiplist
 * @param max_levels Number of "ups" we have.
 * This Should be kept close to lg2 of the number of items to store.
 * @param level_probability Ignored
 * @param allow_duplicates Allow duplicates in this list
 * @param append_duplicates Append rather than prepend duplicates
 * @param compare_function Comparison function for data entries
 * @return pointer to a new skiplist on success, NULL on errors
 */
skiplist *skiplist_new(int max_levels, float level_probability, int allow_duplicates, int append_duplicates, int (*compare_function)(void *, void *));

/**
 * Insert an item into a skiplist
 * @param list The list to insert to
 * @param data The data to insert
 * @return SKIPLIST_OK on success, or an error code
 */
int skiplist_insert(skiplist *list, void *data);

/**
 * Empty the skiplist of all data
 * @param list The list to empty
 * @return ERROR on failures. OK on success
 */
int skiplist_empty(skiplist *list);

/**
 * Free all nodes (but not all data) in a skiplist
 * This is similar to skiplist_empty(), but also free()'s the head node
 * @param list The list to free
 * @return OK on success, ERROR on failures
 */
int skiplist_free(skiplist **list);

/**
 * Get the first item in the skiplist
 * @param list The list to peek into
 * @return The first item, or NULL if there is none
 */
void *skiplist_peek(skiplist *list);

/**
 * Pop the first item from the skiplist
 * @param list The list to pop from
 */
void *skiplist_pop(skiplist *list);

/**
 * Get first node of skiplist
 * @param list The list to search
 * @param[out] node_ptr State variable for skiplist_get_next()
 * @return The data-item of the first node on success, NULL on errors
 */
void *skiplist_get_first(skiplist *list, void **node_ptr);

/**
 * Get next item from node_ptr
 * @param[out] node_ptr State variable primed from an earlier call to
 * skiplist_get_first() or skiplist_get_next()
 * @return The next data-item matching node_ptr on success, NULL on errors
 */
void *skiplist_get_next(void **node_ptr);

/**
 * Find first entry in skiplist matching data
 * @param list The list to search
 * @param data Comparison object used to search
 * @param[out] node_ptr State variable for future lookups with
 * skiplist_find_next()
 * @return The first found data-item, of NULL if none could be found
 */
void *skiplist_find_first(skiplist *list, void *data, void **node_ptr);

/**
 * Find next entry in skiplist matching data
 * @param list The list to search
 * @param data The data to compare against
 * @param[out] node_ptr State var primed from earlier call to
 * skiplist_find_next() or skiplist_find_first()
 * @return The next found data-item, or NULL if none could be found
 */
void *skiplist_find_next(skiplist *list, void *data, void **node_ptr);

/**
 * Delete all items matching 'data' from skiplist
 * @param list The list to delete from
 * @param data Comparison object used to find the real node
 * @return OK on success, ERROR on errors
 */
int skiplist_delete(skiplist *list, void *data);

/**
 * Delete first item matching 'data' from skiplist
 * @param list The list to delete from
 * @param data Comparison object used to search the list
 * @return OK on success, ERROR on errors.
 */
int skiplist_delete_first(skiplist *list, void *data);

/**
 * Delete a particular node from the skiplist
 * @param list The list to search
 * @param node_ptr The node to delete
 * @return OK on success, ERROR on errors.
 */
int skiplist_delete_node(skiplist *list, void *node_ptr);

NAGIOS_END_DECL
/* @} */
#endif
