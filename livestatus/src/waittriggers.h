#ifndef waittriggers_h
#define waittriggers_h

#include "pthread.h"

#define WT_NONE         -1
#define WT_ALL           0
#define WT_CHECK         1
#define WT_STATE         2
#define WT_LOG           3
#define WT_DOWNTIME      4
#define WT_COMMENT       5
#define WT_COMMAND       6
#define WT_NUM_TRIGGERS  7

extern const char *wt_names[];
extern pthread_cond_t g_wait_cond[];
extern pthread_mutex_t g_wait_mutex;


#endif // waittriggers_h

