#include "waittriggers.h"

const char *wt_names[WT_NUM_TRIGGERS] = 
{
    "all", 
    "check", 
    "state", 
    "log", 
    "downtime", 
    "comment",
    "command",
    "program",
};

pthread_cond_t g_wait_cond[] = {
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
    PTHREAD_COND_INITIALIZER,
};

pthread_mutex_t g_wait_mutex = PTHREAD_MUTEX_INITIALIZER;
