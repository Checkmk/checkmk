#ifndef INCLUDE__shared_h__
#define INCLUDE__shared_h__

#include <time.h>
#include "libnagios.h"

NAGIOS_BEGIN_DECL

/* mmapfile structure - used for reading files via mmap() */
typedef struct mmapfile_struct {
	char *path;
	int mode;
	int fd;
	unsigned long file_size;
	unsigned long current_position;
	unsigned long current_line;
	void *mmap_buf;
	} mmapfile;

/* official count of first-class objects */
struct object_count {
	unsigned int commands;
	unsigned int timeperiods;
	unsigned int hosts;
	unsigned int hostescalations;
	unsigned int hostdependencies;
	unsigned int services;
	unsigned int serviceescalations;
	unsigned int servicedependencies;
	unsigned int contacts;
	unsigned int contactgroups;
	unsigned int hostgroups;
	unsigned int servicegroups;
	};

extern struct object_count num_objects;

extern void timing_point(const char *fmt, ...); /* print a message and the time since the first message */
extern char *my_strtok(char *buffer, const char *tokens);
extern char *my_strsep(char **stringp, const char *delim);
extern mmapfile *mmap_fopen(const char *filename);
extern int mmap_fclose(mmapfile *temp_mmapfile);
extern char *mmap_fgets(mmapfile *temp_mmapfile);
extern char *mmap_fgets_multiline(mmapfile * temp_mmapfile);
extern void strip(char *buffer);
extern int hashfunc(const char *name1, const char *name2, int hashslots);
extern int compare_hashdata(const char *val1a, const char *val1b, const char *val2a,
                            const char *val2b);
extern void get_datetime_string(time_t *raw_time, char *buffer,
                                int buffer_length, int type);
extern void get_time_breakdown(unsigned long raw_time, int *days, int *hours,
                               int *minutes, int *seconds);

NAGIOS_END_DECL
#endif
