#ifndef LIBNAGIOS_squeue_h__
#define LIBNAGIOS_squeue_h__
#include <sys/time.h>
#include <time.h>
#include "pqueue.h"
/**
 * @file squeue.h
 * @brief Scheduling queue function declarations
 *
 * This library is based on the pqueue api, which implements a
 * priority queue based on a binary heap, providing O(lg n) times
 * for insert() and remove(), and O(1) time for peek().
 * @note There is no "find". Callers must maintain pointers to their
 * scheduled events if they wish to be able to remove them.
 *
 * @{
 */

/*
 * All opaque types here.
 * The pqueue library can be useful on its own though, so we
 * don't block that from user view.
 */
typedef pqueue_t squeue_t;
struct squeue_event;
typedef struct squeue_event squeue_event;

/**
 * Options for squeue_destroy()'s flag parameter
 */
#define SQUEUE_FREE_DATA (1 << 0) /** Call free() on all data pointers */

/**
 * Get the scheduled runtime of this event
 * @param[in] evt The event to get runtime of
 * @return struct timeval on success, NULL on errors
 */
extern const struct timeval *squeue_event_runtime(squeue_event *evt);

/**
 * Get data of an squeue_event struct
 * @param[in] evt The event to operate on
 * @return The data object pointed to by the event
 */
extern void *squeue_event_data(squeue_event *evt);

/**
 * Creates a scheduling queue optimized for handling events within
 * the given timeframe. Callers should take care to create a queue
 * of a decent but not overly large size, as too small or too large
 * a queue will impact performance negatively. A queue can hold any
 * number of events. A good value for "horizon" would be the max
 * seconds into the future one expects to schedule things, although
 * with few scheduled items in that timeframe you'd be better off
 * using a more narrow horizon.
 *
 * @param size Hint about how large this queue will get
 * @return A pointer to a scheduling queue
 */
extern squeue_t *squeue_create(unsigned int size);

/**
 * Destroys a scheduling queue completely
 * @param[in] q The doomed queue
 * @param[in] flags Flags determining the the level of destruction
 */
extern void squeue_destroy(squeue_t *q, int flags);

/**
 * Enqueue an event with microsecond precision.
 * It's up to the caller to keep the event pointer in case he/she
 * wants to remove the event from the queue later.
 *
 * @param q The scheduling queue to add to
 * @param tv When this event should occur
 * @param data Pointer to any kind of data
 * @return The complete scheduled event
 */
extern squeue_event *squeue_add_tv(squeue_t *q, struct timeval *tv, void *data);

/**
 * Adds an event to the scheduling queue.
 * See notes for squeue_add_tv() for details
 *
 * @param q The scheduling queue to add to
 * @param when The unix timestamp when this event is to occur
 * @param data Pointer to any kind of data
 * @return The complete scheduled event
 */
extern squeue_event *squeue_add(squeue_t *q, time_t when, void *data);

/**
 * Adds an event to the scheduling queue with millisecond precision
 * See notes on squeue_add_tv() for details
 *
 * @param[in] q The scheduling queue to add to
 * @param[in] when Unix timestamp when this event should occur
 * @param[in] usec Millisecond of above this event should occur
 * @param[in] data Pointer to any kind of data
 * @return NULL on errors. squeue_event pointer on success
 */
extern squeue_event *squeue_add_usec(squeue_t *q, time_t when, time_t usec, void *data);

/**
 * Adds an event to the scheduling queue with millisecond precision
 * See notes on squeue_add_tv() for details
 *
 * @param[in] q The scheduling queue to add to
 * @param[in] when Unix timestamp when this event should occur
 * @param[in] msec Millisecond of above this event should occur
 * @param[in] data Pointer to any kind of data
 * @return NULL on errors. squeue_event pointer on success
 */
extern squeue_event *squeue_add_msec(squeue_t *q, time_t when, time_t msec, void *data);

/**
 * Returns the data of the next scheduled event from the scheduling
 * queue without removing it from the queue.
 *
 * @param q The scheduling queue to peek into
 */
extern void *squeue_peek(squeue_t *q);

/**
 * Pops the next scheduled event from the scheduling queue and
 * returns the data for it.
 * This is equivalent to squeue_peek() + squeue_pop()
 * @note This causes the squeue_event to be free()'d.
 *
 * @param q The scheduling queue to pop from
 */
extern void *squeue_pop(squeue_t *q);

/**
 * Removes the given event from the scheduling queue
 * @note This causes the associated squeue_event() to be free()'d.
 * @param[in] q The scheduling queue to remove from
 * @param[in] evt The event to remove
 */
extern int squeue_remove(squeue_t *q, squeue_event *evt);

/**
 * Returns the number of events in the scheduling queue. This
 * function never fails.
 *
 * @param[in] q The scheduling queue to inspect
 * @return number of events in the inspected queue
 */
extern unsigned int squeue_size(squeue_t *q);


/**
 * Returns true if passed timeval is after the time for the event
 *
 * @param[in] evt The queue event to inspect
 * @param[in] reftime The reference time to compare to the queue event time
 * @return 1 if reftime > event time, 0 otherwise
 */
extern int squeue_evt_when_is_after(squeue_event *evt, struct timeval *reftime);
#endif
/** @} */
