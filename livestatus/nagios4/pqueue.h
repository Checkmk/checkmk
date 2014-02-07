/*
 * Copyright 2010 Volkan Yazıcı <volkan.yazici@gmail.com>
 * Copyright 2006-2010 The Apache Software Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
#ifndef LIBNAGIOS_pqueue_h__
#define LIBNAGIOS_pqueue_h__
#include <stdio.h>

/**
 * @file  pqueue.h
 * @brief Priority Queue function declarations
 *
 * This priority queue library was originally written by Volkan Yazici
 * <volkan.yazici@gmail.com>. It was lated adapted for Nagios by
 * Andreas Ericsson <ae@op5.se>. Changes compared to the original
 * version are pretty much limited to changing pqueue_pri_t to be
 * an unsigned long long instead of a double, since ULL comparisons
 * are 107 times faster on my 64-bit laptop.
 *
 * @{
 */


/** priority data type (used to be double, but ull is 107 times faster) */
typedef unsigned long long pqueue_pri_t;

/** callback functions to get/set/compare the priority of an element */
typedef pqueue_pri_t (*pqueue_get_pri_f)(void *a);
typedef void (*pqueue_set_pri_f)(void *a, pqueue_pri_t pri);
typedef int (*pqueue_cmp_pri_f)(pqueue_pri_t next, pqueue_pri_t curr);


/** callback functions to get/set the position of an element */
typedef unsigned int (*pqueue_get_pos_f)(void *a);
typedef void (*pqueue_set_pos_f)(void *a, unsigned int pos);


/** debug callback function to print a entry */
typedef void (*pqueue_print_entry_f)(FILE *out, void *a);


/** the priority queue handle */
typedef struct pqueue_t
{
    unsigned int size;       /**< number of elements in this queue */
    unsigned int avail;      /**< slots available in this queue */
    unsigned int step;       /**< growth stepping setting */
    pqueue_cmp_pri_f cmppri; /**< callback to compare nodes */
    pqueue_get_pri_f getpri; /**< callback to get priority of a node */
    pqueue_set_pri_f setpri; /**< callback to set priority of a node */
    pqueue_get_pos_f getpos; /**< callback to get position of a node */
    pqueue_set_pos_f setpos; /**< callback to set position of a node */
    void **d;                /**< The actualy queue in binary heap form */
} pqueue_t;


/**
 * initialize the queue
 *
 * @param n the initial estimate of the number of queue items for which memory
 *          should be preallocated
 * @param cmppri The callback function to run to compare two elements
 *    This callback should return 0 for 'lower' and non-zero
 *    for 'higher', or vice versa if reverse priority is desired
 * @param setpri the callback function to run to assign a score to an element
 * @param getpri the callback function to run to set a score to an element
 * @param getpos the callback function to get the current element's position
 * @param setpos the callback function to set the current element's position
 *
 * @return the handle or NULL for insufficent memory
 */
pqueue_t *
pqueue_init(unsigned int n,
            pqueue_cmp_pri_f cmppri,
            pqueue_get_pri_f getpri,
            pqueue_set_pri_f setpri,
            pqueue_get_pos_f getpos,
            pqueue_set_pos_f setpos);


/**
 * free all memory used by the queue
 * @param q the queue
 */
void pqueue_free(pqueue_t *q);


/**
 * return the size of the queue.
 * @param q the queue
 */
unsigned int pqueue_size(pqueue_t *q);


/**
 * insert an item into the queue.
 * @param q the queue
 * @param d the item
 * @return 0 on success
 */
int pqueue_insert(pqueue_t *q, void *d);


/**
 * move an existing entry to a different priority
 * @param q the queue
 * @param new_pri the new priority
 * @param d the entry
 */
void
pqueue_change_priority(pqueue_t *q,
                       pqueue_pri_t new_pri,
                       void *d);


/**
 * pop the highest-ranking item from the queue.
 * @param q the queue
 * @return NULL on error, otherwise the entry
 */
void *pqueue_pop(pqueue_t *q);


/**
 * remove an item from the queue.
 * @param q the queue
 * @param d the entry
 * @return 0 on success
 */
int pqueue_remove(pqueue_t *q, void *d);


/**
 * access highest-ranking item without removing it.
 * @param q the queue
 * @return NULL on error, otherwise the entry
 */
void *pqueue_peek(pqueue_t *q);


/**
 * print the queue
 * @internal
 * DEBUG function only
 * @param q the queue
 * @param out the output handle
 * @param the callback function to print the entry
 */
void
pqueue_print(pqueue_t *q, FILE *out, pqueue_print_entry_f print);


/**
 * dump the queue and it's internal structure
 * @internal
 * debug function only
 * @param q the queue
 * @param out the output handle
 * @param the callback function to print the entry
 */
void pqueue_dump(pqueue_t *q, FILE *out, pqueue_print_entry_f print);


/**
 * checks that the pq is in the right order, etc
 * @internal
 * debug function only
 * @param q the queue
 */
int pqueue_is_valid(pqueue_t *q);

#endif
/** @} */
