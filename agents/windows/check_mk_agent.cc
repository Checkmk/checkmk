// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
// 
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
// 
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.


// Looking for documentation on Win32-API? Here are some of the
// documents that I used:

// Registry:
// http://msdn.microsoft.com/en-us/library/ms724897.aspx

// Performance-Counters:
// http://msdn.microsoft.com/en-us/library/aa373178(VS.85).aspx

// Eventlogs:
// http://msdn.microsoft.com/en-us/library/aa363672(VS.85).aspx
// http://msdn.microsoft.com/en-us/library/bb427356(VS.85).aspx

// System Error Codes:
// http://msdn.microsoft.com/en-us/library/ms681381(VS.85).aspx

// This program needs at least windows version 0x0500
// (Window 2000 / Windows XP)
#define WINVER 0x0500

#include <stdio.h>
#include <windows.h>
#include <winbase.h>
#include <winreg.h>    // performance counters from registry
#include <tlhelp32.h>  // list of processes
#include <winsock2.h>
#include <stdarg.h>
#include <time.h>
#include <string.h>
#include <locale.h>

#define CHECK_MK_VERSION "1.1.4atlas4"
#define CHECK_MK_AGENT_PORT 6556
#define SERVICE_NAME "Check_MK_Agent"
#define KiloByte 1024

bool do_tcp = false;
bool should_terminate = false;
bool logwatch_send_initial_entries = false;

bool logwatch_suppress_info = true;

// dynamic buffer for event log entries. Grows with the
// time as needed. Never shrinked.
char *eventlog_buffer = 0;
int eventlog_buffer_size = 0;

// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far. We do not want to make use of C++ features
// here so sorry for the mess...
unsigned num_eventlogs = 0;
#define  MAX_EVENTLOGS 128
DWORD    known_record_numbers[MAX_EVENTLOGS];
char    *eventlog_names[MAX_EVENTLOGS];
bool     newly_found[MAX_EVENTLOGS];


#ifdef DEBUG
void debug(char *text)
{
    FILE *debugout = fopen("C:\\check_mk_agent.log", "a");
    if (debugout) {
	fprintf(debugout, "%s\n", text);
	fflush(debugout);
	fclose(debugout);
    }
}
#else
#define debug(C) 
#endif

bool verbose_mode = false;
void verbose(const char *format, ...)
{
    if (!verbose_mode)
	return;

    va_list ap;
    va_start(ap, format);
    printf("DEBUG: ");
    vprintf(format, ap);
    printf("\n");
    fflush(stdout);
}
   


void outputCounter(SOCKET &out, BYTE *datablock, int counter, 
		   PERF_OBJECT_TYPE *objectPtr, PERF_COUNTER_DEFINITION *counterPtr);
void outputCounterValue(SOCKET &out, PERF_COUNTER_BLOCK *counterBlockPtr, int size, unsigned offset);
double current_time();


// determine system root by reading the environment variable
// %SystemRoot%. This variable is used in the registry entries
// that describe eventlog messages.
const char *system_root()
{
    static char root[128];
    if (0 < GetWindowsDirectory(root, sizeof(root)))
	return root;
    else
	return "C:\\WINDOWS";
}


char *llu_to_string(unsigned long long value)
{
    static char buffer[64];

    if (value == 0) {
	strcpy(buffer, "0");
        return buffer;
    }

    buffer[63] = 0;
    
    char *write = buffer + 63;
    while (value > 0) {
    	if (write <= buffer) {
	    strcpy(buffer, "(invalid)");
	    return buffer;
	}
    	char digit = (value % 10) + '0';
    	*--write = digit;
    	value = value / 10;
    }
    return write;
}



void output(SOCKET &out, const char *format, ...)
{
    static char outbuffer[4096];

    va_list ap;
    va_start(ap, format);
    int len = vsnprintf(outbuffer, sizeof(outbuffer), format, ap);
    if (do_tcp) {
	while (!should_terminate) {
	    int result = send(out, outbuffer, len, 0);
	    if (result == SOCKET_ERROR) {
		debug("send() failed");
		int error = WSAGetLastError();
		if (error == WSAEINTR) {
		    debug("INTR. Nochmal...");
		    continue;
		}
		else if (error == WSAEINPROGRESS) {
		    debug("INPROGRESS. Nochmal...");
		    continue;
		}
		else if (error == WSAEWOULDBLOCK) {
		    debug("WOULDBLOCK. Komisch. Breche ab...");
		    break;
		}
		else {
		    debug("Anderer Fehler. Gebe auf\n");
		    break;
		}
	    }
	    else if (result == 0)
		debug("send() returned 0");
	    else if (result != len)
		debug("send() sent too few bytes");
	    break;
	}
    }    
    else
	fwrite(outbuffer, len, 1, stdout);
}


void section_df(SOCKET &out)
{
    output(out, "<<<df>>>\n");
    TCHAR buffer[4096];
    DWORD len = GetLogicalDriveStrings(sizeof(buffer), buffer);

    TCHAR *end = buffer + len;
    TCHAR *drive = buffer;
    while (drive < end) {
	UINT drvType = GetDriveType(drive);
	if (drvType == DRIVE_FIXED)  // only process local harddisks
	{
	    ULARGE_INTEGER free_avail, total, free;
	    free_avail.QuadPart = 0;
	    total.QuadPart = 0;
	    free.QuadPart = 0;
	    int returnvalue = GetDiskFreeSpaceEx(drive, &free_avail, &total, &free);
	    if (returnvalue > 0) {
		double perc_used = 0;
		if (total.QuadPart > 0)
		    perc_used = 100 - (100 * free_avail.QuadPart / total.QuadPart);
		
		TCHAR fsname[128];
		if (!GetVolumeInformation(drive, 0, 0, 0, 0, 0, fsname, 128))
		    fsname[0] = 0;
		
		output(out, "%-10s %-8s ", drive, fsname);
		output(out, "%s ", llu_to_string(total.QuadPart / KiloByte));
		output(out, "%s ", llu_to_string((total.QuadPart - free_avail.QuadPart) / KiloByte));
		output(out, "%s ", llu_to_string(free_avail.QuadPart / KiloByte));
		output(out, "%3.0f%% ", perc_used);
		output(out, "%s\n", drive);
	    }
	}
	drive += strlen(drive) + 1;
    }
}


void section_ps(SOCKET &out)
{
    output(out, "<<<ps>>>\n");
    HANDLE hProcessSnap;
    PROCESSENTRY32 pe32;
  
    hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hProcessSnap != INVALID_HANDLE_VALUE) 
    {
	pe32.dwSize = sizeof(PROCESSENTRY32);
	if (Process32First(hProcessSnap, &pe32)) {
	    do {
		output(out, "%s\n", pe32.szExeFile);
	    } while (Process32Next(hProcessSnap, &pe32));
	}
	CloseHandle(hProcessSnap);
    }
}


void section_services(SOCKET &out)
{
    output(out, "<<<services>>>\n");
    SC_HANDLE scm = OpenSCManager(0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);
    if (scm != INVALID_HANDLE_VALUE) {
	DWORD bytes_needed = 0;
	DWORD num_services = 0;
	// first determine number of bytes needed
	EnumServicesStatusEx(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL, 
			     NULL, 0, &bytes_needed, &num_services, 0, 0);
	if (GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
	    BYTE *buffer = (BYTE *)malloc(bytes_needed);
	    if (buffer) {
		if (EnumServicesStatusEx(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL, 
					 buffer, bytes_needed, 
					 &bytes_needed, &num_services, 0, 0))
		{
		    ENUM_SERVICE_STATUS_PROCESS *service = (ENUM_SERVICE_STATUS_PROCESS *)buffer;
		    for (unsigned i=0; i<num_services; i++) {
			DWORD state = service->ServiceStatusProcess.dwCurrentState;
			const char *state_name = "unknown";
			switch (state) {
			case SERVICE_CONTINUE_PENDING: state_name = "continuing"; break;
			case SERVICE_PAUSE_PENDING:    state_name = "pausing"; break;
			case SERVICE_PAUSED:           state_name = "paused"; break;
			case SERVICE_RUNNING:          state_name = "running"; break;
			case SERVICE_START_PENDING:    state_name = "starting"; break;
			case SERVICE_STOP_PENDING:     state_name = "stopping"; break;
			case SERVICE_STOPPED:          state_name = "stopped"; break;
			}

			// The service name usually does not contain spaces. But
			// in some cases it does. We replace them with _ in order
			// the keep it in one space-separated column. Since we own
			// the buffer, we can simply change the name inplace.
			for (char *w=(char *)(service->lpServiceName); *w; w++) {
			    if (*w == ' ')
				*w = '_';
			}			
			
			output(out, "%-18s %-8s %s\n", 
			       service->lpServiceName, state_name,
			       service->lpDisplayName);
			service ++;
		    }
		}
		free(buffer);
	    }
	}
	CloseServiceHandle(scm);
    }
}

#define DEFAULT_BUFFER_SIZE 40960L

// Hilfsfunktionen zum Navigieren in den Performance-Counter Binaerdaten
PERF_OBJECT_TYPE *FirstObject(PERF_DATA_BLOCK *dataBlock) { 
    return (PERF_OBJECT_TYPE *) ((BYTE *)dataBlock + dataBlock->HeaderLength); 
}
PERF_OBJECT_TYPE *NextObject(PERF_OBJECT_TYPE *act) {
    return (PERF_OBJECT_TYPE *) ((BYTE *)act + act->TotalByteLength); 
}
PERF_COUNTER_DEFINITION *FirstCounter(PERF_OBJECT_TYPE *perfObject) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfObject + perfObject->HeaderLength); 
}
PERF_COUNTER_DEFINITION *NextCounter(PERF_COUNTER_DEFINITION *perfCounter) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfCounter + perfCounter->ByteLength); 
}
PERF_COUNTER_BLOCK *GetCounterBlock(PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_COUNTER_BLOCK *) ((BYTE *)pInstance + pInstance->ByteLength); 
}
PERF_INSTANCE_DEFINITION *FirstInstance (PERF_OBJECT_TYPE *pObject) {
    return (PERF_INSTANCE_DEFINITION *)  ((BYTE *) pObject + pObject->DefinitionLength); 
}
PERF_INSTANCE_DEFINITION *NextInstance (PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_INSTANCE_DEFINITION *) ((BYTE *)pInstance + pInstance->ByteLength + GetCounterBlock(pInstance)->ByteLength); 
}


void dump_performance_counters(SOCKET &out, unsigned counter)
{
    // registry entry is ascii representation of counter index
    char counter_index_name[8];
    snprintf(counter_index_name, sizeof(counter_index_name), "%u", counter);

    // allocate block to store counter data block
    DWORD size = DEFAULT_BUFFER_SIZE;
    BYTE *data = new BYTE[DEFAULT_BUFFER_SIZE];
    DWORD type;
    DWORD ret;

    // Holt zu einem bestimmten Counter den kompletten Binärblock aus der
    // Registry. Da man vorher nicht weiß, wie groß der Puffer sein muss,
    // kann man nur mit irgendeiner Größe anfangen und dann diesen immer
    // wieder größer machen, wenn er noch zu klein ist. >:-P
    while ((ret = RegQueryValueEx(HKEY_PERFORMANCE_DATA, counter_index_name, 
				 0, &type, data, &size)) != ERROR_SUCCESS) 
    {
	if (ret == ERROR_MORE_DATA) // WIN32 API sucks...
	{
	    // Der Puffer war zu klein. Toll. Also den Puffer größer machen
	    // und das ganze nochmal probieren.
	    size += DEFAULT_BUFFER_SIZE;
	    debug("Buffer for RegQueryValueEx too small. Resizing...");
	    delete [] data;
	    data = new BYTE [size];
	} else {
	    // Es ist ein anderer Fehler aufgetreten. Abbrechen.
	    delete [] data;
	    return;
	}
    }

    PERF_DATA_BLOCK *dataBlockPtr = (PERF_DATA_BLOCK *)data;
  
    // Determine first object in list of objects
    PERF_OBJECT_TYPE *objectPtr = FirstObject(dataBlockPtr);
  
    // Now walk through the list of objects. The bad news is:
    // even if we expect only one object, windows might send
    // us more that one object. We need to scan a list of objects
    // in order to find the one we have asked for. >:-P
    for (unsigned int a=0 ; a < dataBlockPtr->NumObjectTypes ; a++) 
    {
	// Have we found the object we seek? 
	if (objectPtr->ObjectNameTitleIndex == counter)
	{
	    // Yes. Great. Now: each object consist of a lot of counters.
	    // We walk through the list of counters in this object:
	  
	    // get pointer to first counter
	    PERF_COUNTER_DEFINITION *counterPtr = FirstCounter(objectPtr);

	    // Now we make a first quick walk through all counters, only in order
	    // to find the beginning of the data block (which comes after the
	    // counter definitions)
	    PERF_COUNTER_DEFINITION *last_counter = FirstCounter(objectPtr);
	    for(unsigned int b=0 ; b < objectPtr->NumCounters ; b++) 
		last_counter = NextCounter(last_counter);
	    BYTE *datablock = (BYTE *)last_counter;

	    // Now walk through the counter list a second time and output
	    // all non-zero counters
	    for(unsigned int b=0 ; b < objectPtr->NumCounters ; b++) 
	    {
		outputCounter(out, datablock, counter, objectPtr, counterPtr);
		counterPtr = NextCounter(counterPtr);
	    }
	}
	// naechstes Objekt in der Liste
	objectPtr = NextObject(objectPtr);
    }
    delete [] data;
}


void outputCounter(SOCKET &out, BYTE *datablock, int counter, 
		   PERF_OBJECT_TYPE *objectPtr, PERF_COUNTER_DEFINITION *counterPtr)
{
    int num_instances = objectPtr->NumInstances;
    unsigned offset = counterPtr->CounterOffset;
    int size = counterPtr->CounterSize;

    // determine the type of the counter (for verbose output)
    const char *countertypename = "(unknown)";
    switch (counterPtr->CounterType) {
    case PERF_COUNTER_COUNTER:                countertypename = "counter"; break;
    case PERF_COUNTER_QUEUELEN_TYPE:          countertypename = "queuelen_type" ; break;
    case PERF_SAMPLE_COUNTER:                 countertypename = "sample_counter"; break;
//  case PERF_OBJ_TIME_TIMER:                 countertypename = "obj_time_timer"; break;
//  case PERF_COUNTER_100NS_QUEUELEN_TYPE:    countertypename = "100ns_queuelen_type"; break;
//  case PERF_COUNTER_OBJ_TIME_QUEUELEN_TYPE: countertypename = "obj_time_queuelen_type"; break;
    case PERF_COUNTER_TIMER:                  countertypename = "timer"; break;
    case PERF_COUNTER_TIMER_INV:              countertypename = "timer_inv"; break;
    case PERF_COUNTER_BULK_COUNT:             countertypename = "bulk_count"; break;
//  case PERF_COUNTER_LARGE_QUEUELEN_TYPE:    countertypename = "large_queuelen_type"; break;
    case PERF_COUNTER_MULTI_TIMER:            countertypename = "multi_timer"; break;
    case PERF_COUNTER_MULTI_TIMER_INV:        countertypename = "multi_timer_inv"; break;
    case PERF_COUNTER_RAWCOUNT:               countertypename = "rawcount"; break;
    case PERF_COUNTER_RAWCOUNT_HEX:           countertypename = "rawcount_hex"; break;
//  case PERF_COUNTER_DELTA:                  countertypename = "delta"; break;
    case PERF_COUNTER_LARGE_RAWCOUNT:         countertypename = "large_rawcount"; break;
    case PERF_COUNTER_LARGE_RAWCOUNT_HEX:     countertypename = "large_rawcount_hex"; break;
//  case PERF_COUNTER_LARGE_DELTA:            countertypename = "large_delta"; break;
    case PERF_100NSEC_TIMER:                  countertypename = "100nsec_timer"; break;
    case PERF_100NSEC_TIMER_INV:              countertypename = "100nsec_timer_inv"; break;
    case PERF_100NSEC_MULTI_TIMER:            countertypename = "100nsec_multi_timer"; break;
    case PERF_100NSEC_MULTI_TIMER_INV:        countertypename = "100nsec_multi_timer_inv"; break;
    case PERF_SAMPLE_FRACTION:                countertypename = "sample_fraction"; break;
    case PERF_RAW_FRACTION:                   countertypename = "raw_fraction"; break;
//  case PERF_LARGE_RAW_FRACTION:             countertypename = "large_raw_fraction"; break;
//  case PERF_PRECISION_SYSTEM_TIMER:         countertypename = "precision_system_timer"; break;
//  case PERF_PRECISION_100NS_TIMER:          countertypename = "precision_100ns_timer"; break;
//  case PERF_PRECISION_OBJECT_TIMER:         countertypename = "precision_object_timer"; break;
    case PERF_AVERAGE_TIMER:                  countertypename = "average_timer"; break;
    case PERF_AVERAGE_BULK:                   countertypename = "average_bulk"; break;
    case PERF_SAMPLE_BASE:        	      countertypename = "sample_base"; break;
    case PERF_AVERAGE_BASE:       	      countertypename = "average_base"; break;
    case PERF_COUNTER_MULTI_BASE: 	      countertypename = "multi_base"; break;
    case PERF_RAW_BASE:           	      countertypename = "raw_base"; break;
//  case PERF_LARGE_RAW_BASE:     	      countertypename = "large_raw_base"; break;
    case PERF_ELAPSED_TIME:       	      countertypename = "elapsed_time"; break;
    case PERF_COUNTER_TEXT:       	      countertypename = "text"; break;
    case PERF_COUNTER_NODATA:     	      countertypename = "nodata"; break;
    case PERF_COUNTER_HISTOGRAM_TYPE:         countertypename = "histogram_type"; break;
    }
	      
    // Output index of counter object and counter, and timestamp
    output(out, "%d:%d %.2f", counter, counterPtr->CounterNameTitleIndex, current_time());

    // If this is a multi-instance-counter, loop over the instances
    if (num_instances >= 0) 
    {
	// get pointer to first instance
	PERF_INSTANCE_DEFINITION *instancePtr = FirstInstance(objectPtr);
		  
	for(int b=0 ; b<objectPtr->NumInstances ; b++) 
	{
	    // PERF_COUNTER_BLOCK dieser Instanz ermitteln.
	    PERF_COUNTER_BLOCK *counterBlockPtr = GetCounterBlock(instancePtr);
	    outputCounterValue(out, counterBlockPtr, size, offset);
	    instancePtr = NextInstance(instancePtr);
	}

    }
    else { // instanceless counter
	PERF_COUNTER_BLOCK *counterBlockPtr = (PERF_COUNTER_BLOCK *) datablock;
	outputCounterValue(out, counterBlockPtr, size, offset);
    }
    output(out, " %s\n", countertypename);
}


void outputCounterValue(SOCKET &out, PERF_COUNTER_BLOCK *counterBlockPtr, int size, unsigned offset)
{
    if (size == 4) {
	DWORD value = *((DWORD *)((BYTE *)counterBlockPtr) + offset);
	output(out, " %lu", value);
    }
    else if (size == 8) {
	DWORD *data_at = (DWORD *)(((BYTE *)counterBlockPtr) + offset);
	DWORDLONG value = (DWORDLONG)*data_at + ((DWORDLONG)*(data_at + 1) << 32);
	output(out, " %s", llu_to_string(value));
    }
    else
	output(out, " unknown");
}


double current_time()
{
    SYSTEMTIME systime;
    FILETIME filetime;
    GetSystemTime(&systime);
    SystemTimeToFileTime(&systime, &filetime);
    unsigned long long ft = (unsigned long long)(filetime.dwLowDateTime)
	+ (((unsigned long long)filetime.dwHighDateTime) << 32);
    return ft / 10000000.0;
}


void grow_eventlog_buffer(int newsize)
{
    delete [] eventlog_buffer;
    eventlog_buffer = new char[newsize];
    eventlog_buffer_size = newsize;
}


bool output_eventlog_entry(SOCKET &out, char *dllpath, EVENTLOGRECORD *event, char type_char, 
			   const char *logname, const char *source_name, char **strings)
{
    char msgbuffer[2048]; 
    char dll_realpath[128];
    HINSTANCE dll;

    // if no dllpath is NULL, we output the message without text conversion and
    // always succeed. If a dll pathpath is given, we only succeed if the conversion
    // is successfull.

    if (dllpath) {
	// to make it even more difficult, dllpath may contain %SystemRoot%, which
	// must be replaced with the environment variable %SystemRoot% (most probably - 
	// but not entirely for sure - C:\WINDOWS
	if (strncasecmp(dllpath, "%SystemRoot%", 12) == 0)
	    snprintf(dll_realpath, sizeof(dll_realpath), "%s%s", system_root(), dllpath + 12);
	else
	    snprintf(dll_realpath, sizeof(dll_realpath), "%s", dllpath);
	
	// I found this path in the official API documentation. I hope
	// it's correct for all windows versions
	dll =  LoadLibrary(dll_realpath);
	if (!dll) {
	    return false;
	}
    }
    else
	dll = NULL;
    DWORD len = FormatMessage(
	FORMAT_MESSAGE_ARGUMENT_ARRAY | 
	FORMAT_MESSAGE_FROM_HMODULE | 
	FORMAT_MESSAGE_FROM_SYSTEM,
	dll,                        
	event->EventID,                 
	0, // accept any language
	(LPTSTR)msgbuffer,         
	sizeof(msgbuffer),         
	strings);

    if (dll)
	FreeLibrary(dll);
   
    if (len == 0) // message could not be converted
    {
        // if conversion was not successfull while trying to load a DLL, we return a 
        // failure. Our parent function will then retry later without a DLL path.
	if (dllpath) 
	    return false;

	// if message cannot be converted, then at least output the text strings.
	// We render all messages one after the other into msgbuffer, separated
	// by spaces.
	memset(msgbuffer, 0, sizeof(msgbuffer)); // avoids problems with 0-termination
	char *w = msgbuffer;
	int sizeleft = sizeof(msgbuffer) - 1; // leave one byte for termination
	int n = 0;
	while (strings[n]) // string array is zero terminated
	{
	    char *s = strings[n];
	    int l = strlen(s);
	    if (l + 1 < sizeleft) {
		strcpy(w, s);
		w += l;
		*w++ = ' ';
		sizeleft -= l + 1;
	    }
	    n++;
	}
    }
    
    // replace newlines with spaces. check_mk expects one message each line.
    char *w = msgbuffer;
    while (*w) {
	if (*w == '\n' || *w == '\r') *w = ' ';
	w++;
    }
    
    // convert UNIX timestamp to local time
    time_t time_generated = (time_t)event->TimeGenerated;
    struct tm *t = localtime(&time_generated);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);
    
    output(out, "%c %s %lu %s %s\n", type_char, timestamp, event->EventID, source_name, msgbuffer);
    return true;
}


void process_eventlog_entries(SOCKET &out, const char *logname, char *buffer, 
			      DWORD bytesread, DWORD *record_number, bool just_find_end,
			      int *worst_state)
{
    char *strings[64];
    char regpath[128];
    BYTE dllpath[128];
    char source_name[128];

    EVENTLOGRECORD *event = (EVENTLOGRECORD *)buffer;
    while (bytesread > 0) 
    {
	*record_number = event->RecordNumber;
	
	char type_char;
	int this_state;
	switch (event->EventType) {
	case EVENTLOG_ERROR_TYPE:
	    type_char = 'C'; this_state = 2; break;
	case EVENTLOG_WARNING_TYPE:
	    type_char = 'W'; this_state = 1; break;
	case EVENTLOG_INFORMATION_TYPE:
	    type_char = '.'; this_state = 0; break;
	case EVENTLOG_AUDIT_SUCCESS:
	    type_char = '.'; this_state = 0; break;
	case EVENTLOG_AUDIT_FAILURE:
	    type_char = 'C'; this_state = 2; break;
	default:
	    type_char = 'u'; this_state = 1; break;
	}
	if (*worst_state < this_state)
	    *worst_state = this_state;

	// If we are not just scanning for the current end and the worst state,
	// we output the event message
	if (!just_find_end) 
	{
	    // The source name is the name of the application that produced the event
	    LPCTSTR lpSourceName = (LPCTSTR) ((LPBYTE) event + sizeof(EVENTLOGRECORD));
	    
	    // prepare source name without spaces (for check_mk output)
	    strncpy(source_name, lpSourceName, sizeof(source_name)-1);
	    source_name[sizeof(source_name)-1] = 0; // strncpy does not zero-terminate, if buffer is too small!
	    char *w = source_name;
	    while (*w) {
		if (*w == ' ') *w = '_';
		*w++;
	    }
	    
	    // prepare array of zero terminated strings to be inserted
	    // into message template.
	    DWORD num_strings = event->NumStrings;
	    char *s = ((char *)event) + event->StringOffset;
	    unsigned ns;
	    for (ns = 0; ns < num_strings; ns++) {
		if (ns >= 63) break;
		strings[ns] = s;
		s += strlen(s) + 1;
	    }
	    strings[ns] = 0; // end marker in array
	    
	    // Windows eventlog entries refer to texts stored in a DLL >:-P
	    // We need to load this DLL. First we need to look up which
	    // DLL to load in the registry. Hard to image how one could
	    // have contrieved this more complicated...
	    snprintf(regpath, sizeof(regpath), 
		     "SYSTEM\\CurrentControlSet\\Services\\Eventlog\\%s\\%s",
		     logname, lpSourceName);

	    HKEY key;
	    DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0, KEY_READ, &key);

	    bool success = false;
	    if (ret == ERROR_SUCCESS) // could open registry key
	    {
	        DWORD size = sizeof(dllpath) - 1; // leave space for 0 termination
	        memset(dllpath, 0, sizeof(dllpath));
		if (ERROR_SUCCESS == RegQueryValueEx(key, "EventMessageFile", NULL, NULL, dllpath, &size))
		{
		    // Answer may contain more than one DLL. They are separated
		    // by semicola. Not knowing which one is the correct one, I have to try
		    // all...
		    char *token = strtok((char *)dllpath, ";");
		    while (token) {
			if (output_eventlog_entry(out, token, event, type_char, logname, source_name, strings)) {
			    success = true;
			    break;
			}
			token = strtok(NULL, ";");
		    }
		}
		RegCloseKey(key);
	    }
	    // No text conversion succeeded. Output without text anyway
	    if (!success)
	       output_eventlog_entry(out, NULL, event, type_char, logname, source_name, strings);

	} // type_char != '.'
	    
	bytesread -= event->Length;
	event = (EVENTLOGRECORD *) ((LPBYTE) event + event->Length);
    }
}


void output_eventlog(SOCKET &out, const char *logname, 
		     DWORD *record_number, bool just_find_end)
{
    if (eventlog_buffer_size == 0) {
	const int initial_size = 65536;
	eventlog_buffer = new char[initial_size];
	eventlog_buffer_size = initial_size;
    }

    HANDLE hEventlog = OpenEventLog(NULL, logname);
    DWORD bytesread = 0;
    DWORD bytesneeded = 0;
    if (hEventlog) {
	output(out, "[[[%s]]]\n", logname);
	int worst_state = 0;
	DWORD old_record_number = *record_number;

	// we scan all new entries twice. At the first run we check if
	// at least one warning/error message is present. Only if this
	// is the case we make a second run where we output *all* messages,
	// even the informational ones.
	for (int t=0; t<2; t++)
	{
	    *record_number = old_record_number;
	    verbose("Starting from entry number %u", old_record_number);
	    while (true) {
		DWORD flags;
		if (*record_number == 0) {
		    if (t == 1) {
			verbose("Need to reopen Logfile in order to find start again.");
			CloseEventLog(hEventlog);
			hEventlog = OpenEventLog(NULL, logname);
			if (!hEventlog) {
			    verbose("Failed to reopen event log. Bailing out.");
			    return;
			}
		    }
		    flags = EVENTLOG_SEQUENTIAL_READ | EVENTLOG_FORWARDS_READ;
		}
		else {
		    verbose("Previous record number was %d. Doing seek read.", *record_number);
		    flags = EVENTLOG_SEEK_READ | EVENTLOG_FORWARDS_READ;
		}
		    
		if (ReadEventLog(hEventlog, 
				 flags,
				 *record_number + 1,
				 eventlog_buffer,
				 eventlog_buffer_size,
				 &bytesread,
				 &bytesneeded))
		{
		    process_eventlog_entries(out, logname, eventlog_buffer, 
					     bytesread, record_number, just_find_end || t==0, &worst_state);
		}
		else {
		    DWORD error = GetLastError();
		    if (error == ERROR_INSUFFICIENT_BUFFER) {
			grow_eventlog_buffer(bytesneeded);
		    }
		    // found current end of log
		    else if (error == ERROR_HANDLE_EOF) {
			verbose("End of logfile reached at entry %u. Worst state is %d", 
				*record_number, worst_state);
			break;
		    }
		    // invalid parameter can also mean end of log
		    else if (error == ERROR_INVALID_PARAMETER) {
			verbose("Invalid parameter at entry %u (could mean end of logfile). Worst state is %d",
				*record_number, worst_state);
			break;
		    }
		    else {
			output(out, "ERROR: Cannot read eventlog '%s': error %u\n", logname, error);
			break;
		    }
		}
	    }
	    if (worst_state == 0 && logwatch_suppress_info) {
		break; // nothing important found. Skip second run
	    }
	}
	CloseEventLog(hEventlog);
    }
    else {
	output(out, "[[[%s:missing]]]\n", logname);
    }
}


// The output imitates that of the Linux agent. That makes
// a special check for check_mk unneccessary:
// <<<mem>>>.
// MemTotal:       514104 kB
// MemFree:         19068 kB
// SwapTotal:     1048568 kB
// SwapFree:      1043732 kB

void section_mem(SOCKET &out)
{
    output(out, "<<<mem>>>\n");

    MEMORYSTATUSEX statex;
    statex.dwLength = sizeof (statex);
    GlobalMemoryStatusEx (&statex);

    output(out, "MemTotal:  %11d kB\n", statex.ullTotalPhys     / 1024);
    output(out, "MemFree:   %11d kB\n", statex.ullAvailPhys     / 1024);
    output(out, "SwapTotal: %11d kB\n", (statex.ullTotalPageFile - statex.ullTotalPhys) / 1024);
    output(out, "SwapFree:  %11d kB\n", (statex.ullAvailPageFile - statex.ullAvailPhys) / 1024);
    output(out, "PageTotal: %11d kB\n", statex.ullTotalPageFile / 1024);
    output(out, "PageFree:  %11d kB\n", statex.ullAvailPageFile / 1024);
}


void section_winperf(SOCKET &out)
{

    output(out, "<<<winperf>>>\n");
  
    for (int i=0; i<700; i+=2) {
	if (i != 230 && i != 232 && i != 786 && i != 740)
	    dump_performance_counters(out, i);
    }
    // Terminalservices
    dump_performance_counters(out, 2102);
}


// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void register_eventlog(char *logname)
{
    if (num_eventlogs >= MAX_EVENTLOGS)
	return; // veeery unlikely

    // check if we already know this one...
    for (unsigned i=0; i < num_eventlogs; i++) {
	if (!strcmp(logname, eventlog_names[i])) {
	    newly_found[i] = true; // remember its still here
	    return;
	}
    }
    
    // yet unknown. register it.
    known_record_numbers[num_eventlogs] = 0;
    eventlog_names[num_eventlogs] = strdup(logname); 
    newly_found[num_eventlogs] = true;
    num_eventlogs ++;
}

void unregister_all_eventlogs()
{
    for (unsigned i=0; i < num_eventlogs; i++)
	free(eventlog_names[i]);
    num_eventlogs = 0;
}

/* Look into the registry in order to find out, which
   event logs are available. */
bool find_eventlogs(SOCKET &out)
{
    for (unsigned i=0; i<num_eventlogs; i++)
	newly_found[i] = 0;

    char regpath[128];
    snprintf(regpath, sizeof(regpath), 
	     "SYSTEM\\CurrentControlSet\\Services\\Eventlog");
    HKEY key;
    DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0, KEY_ENUMERATE_SUB_KEYS, &key);
    
    bool success = true;
    if (ret == ERROR_SUCCESS) 
    {
	DWORD i = 0;
	char buffer[128];
	DWORD len;
	while (true) 
	{
	    len = sizeof(buffer);
	    DWORD r = RegEnumKeyEx(key, i, buffer, &len, NULL, NULL, NULL, NULL);
	    if (r == ERROR_SUCCESS)
		register_eventlog(buffer);
	    else if (r != ERROR_MORE_DATA)
	    {
		if (r != ERROR_NO_MORE_ITEMS) {
		    output(out, "ERROR: Cannot enumerate over event logs: error code %d\n", r);
		    success = false;
		}
		break;
	    }
	    i ++;
	}
	RegCloseKey(key);
    }
    else {
	success = false;
	output(out, "ERROR: Cannot open registry key %s for enumeration: error code %d\n",
	       regpath, GetLastError());
    }
    return success;
}


// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_eventlog(SOCKET &out)
{
    // This agent remembers the record numbers
    // of the event logs up to which messages have
    // been processed. When started, the eventlog
    // is skipped to the end. Historic messages are
    // not been processed. 
    static bool first_run = true;

    output(out, "<<<logwatch>>>\n");
    if (find_eventlogs(out))
    {
	for (unsigned i=0; i < num_eventlogs; i++) {
	    if (!newly_found[i]) // not here any more!
		output(out, "[[[%s:missing]]]\n", eventlog_names[i]);
	    else
		output_eventlog(out, eventlog_names[i], &known_record_numbers[i], 
				first_run && !logwatch_send_initial_entries);
	}
    }
    first_run = false;
}


void output_data(SOCKET &out)
{
    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    output(out, "<<<check_mk>>>\n");
    output(out, "Version: %s\n", CHECK_MK_VERSION);
    section_df(out);
    section_ps(out);
    section_mem(out);
    section_services(out);
    section_winperf(out);
    section_eventlog(out);
}
    

void listen_tcp_loop()
{
    WSADATA wsa;
    if (0 != WSAStartup(MAKEWORD(2, 0), &wsa)) {
	fprintf(stderr, "Cannot initialize winsock.\n");
	exit(1);
    }

    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) {
	fprintf(stderr, "Cannot create socket.\n");
	exit(1);
    }
    
    SOCKADDR_IN addr;
    memset(&addr, 0, sizeof(SOCKADDR_IN));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(CHECK_MK_AGENT_PORT);
    addr.sin_addr.s_addr = ADDR_ANY;
    
    if (SOCKET_ERROR == bind(s, (SOCKADDR *)&addr, sizeof(SOCKADDR_IN))) {
	fprintf(stderr, "Cannot bind socket to port %d\n", CHECK_MK_AGENT_PORT);
	exit(1);
    }

    if (SOCKET_ERROR == listen(s, 5)) {
	fprintf(stderr, "Cannot listen to socket\n");
	exit(1);
    }

    SOCKET connection;
    // Loop for ever.
    debug("Die Schleife gestartet.");
    while (!should_terminate) 
    {
	// Das Dreckswindows kann nicht vernuenftig gleichzeitig auf
	// ein Socket und auf ein Event warten. Weil ich nicht extra
	// deswegen mit Threads arbeiten will, verwende ich einfach 
	// select() mit einem Timeout und polle should_terminate.

	fd_set fds;
	FD_ZERO(&fds);
	FD_SET(s, &fds);
	struct timeval timeout;
	timeout.tv_sec = 0;
	timeout.tv_usec = 500000;
	if (1 == select(1, &fds, NULL, NULL, &timeout)) 
	{
	    connection = accept(s, NULL, NULL);
	    debug("Habe accepted.");
	    if (connection != INVALID_SOCKET) {

		debug("socket ist auch da.");
		output_data(connection);

		closesocket(connection);
	    }
	}
	else if (!should_terminate) {
	    Sleep(1); // should never happen
	}
    }
    closesocket(s);
    WSACleanup();
}

void usage()
{
    fprintf(stderr, "Usage: \n"
	    "check_mk_agent version -- show version " CHECK_MK_VERSION " and exit\n"
	    "check_mk_agent install -- install as Windows NT service Check_Mk_Agent\n"
	    "check_mk_agent remove  -- remove Windows NT service\n"
	    "check_mk_agent adhoc   -- open TCP port %d and answer request until killed\n"
	    "check_mk_agent test    -- test output of plugin, do not open TCP port\n"
	    "check_mk_agent debug   -- similar to test, but with lots of debug output\n", CHECK_MK_AGENT_PORT);
    exit(1);
}



// Zeugs fuer Windows Service
TCHAR*                gszServiceName = (TCHAR *)TEXT(SERVICE_NAME);
SERVICE_STATUS        serviceStatus;
SERVICE_STATUS_HANDLE serviceStatusHandle = 0;


void WINAPI ServiceControlHandler( DWORD controlCode )
{
    switch ( controlCode )
    {
    case SERVICE_CONTROL_INTERROGATE:
	break;

    case SERVICE_CONTROL_SHUTDOWN:
    case SERVICE_CONTROL_STOP:
	should_terminate = true;
    	serviceStatus.dwCurrentState = SERVICE_STOP_PENDING;
	SetServiceStatus( serviceStatusHandle, &serviceStatus );
	return;

    case SERVICE_CONTROL_PAUSE:
	break;

    case SERVICE_CONTROL_CONTINUE:
	break;

    default:
	if ( controlCode >= 128 && controlCode <= 255 )
	    // user defined control code
	    break;
	else
	    // unrecognised control code
	    break;
    }

    SetServiceStatus( serviceStatusHandle, &serviceStatus );
}

void WINAPI ServiceMain(DWORD, TCHAR* [] )
{
    // initialise service status
    serviceStatus.dwServiceType      	    = SERVICE_WIN32_OWN_PROCESS;
    serviceStatus.dwCurrentState     	    = SERVICE_STOPPED;
    serviceStatus.dwControlsAccepted 	    = 0;
    serviceStatus.dwWin32ExitCode    	    = NO_ERROR;
    serviceStatus.dwServiceSpecificExitCode = NO_ERROR;
    serviceStatus.dwCheckPoint              = 0;
    serviceStatus.dwWaitHint                = 0;
    
    serviceStatusHandle = RegisterServiceCtrlHandler( gszServiceName,
						      ServiceControlHandler );

    if ( serviceStatusHandle )
    {
	// service is starting
	serviceStatus.dwCurrentState = SERVICE_START_PENDING;
	SetServiceStatus( serviceStatusHandle, &serviceStatus );

	// Service running
	serviceStatus.dwControlsAccepted |= (SERVICE_ACCEPT_STOP |
					     SERVICE_ACCEPT_SHUTDOWN);
	serviceStatus.dwCurrentState = SERVICE_RUNNING;
	SetServiceStatus( serviceStatusHandle, &serviceStatus );

	do_tcp = true;
	listen_tcp_loop();

	// service is now stopped
	serviceStatus.dwControlsAccepted &= ~(SERVICE_ACCEPT_STOP |
					      SERVICE_ACCEPT_SHUTDOWN);
	serviceStatus.dwCurrentState = SERVICE_STOPPED;
	SetServiceStatus( serviceStatusHandle, &serviceStatus );
    }
}

void RunService()
{
    SERVICE_TABLE_ENTRY serviceTable[] =
	{
	    { gszServiceName, ServiceMain },
	    { 0, 0 }
	};
    
    StartServiceCtrlDispatcher( serviceTable );
}

void InstallService()
{
    SC_HANDLE serviceControlManager = OpenSCManager( 0, 0,
						     SC_MANAGER_CREATE_SERVICE );

    if ( serviceControlManager )
    {
 	char path[ _MAX_PATH + 1 ];
	if ( GetModuleFileName( 0, path, sizeof(path)/sizeof(path[0]) ) > 0 )
	{
	    SC_HANDLE service = CreateService( serviceControlManager,
					       gszServiceName, gszServiceName,
					       SERVICE_ALL_ACCESS, SERVICE_WIN32_OWN_PROCESS,
					       SERVICE_AUTO_START, SERVICE_ERROR_IGNORE, path,
					       0, 0, 0, 0, 0 );
	    if ( service )
	    {
		CloseServiceHandle( service );
		printf(SERVICE_NAME " Installed Successfully\n");
	    }
	    else
	    {
		if(GetLastError() == ERROR_SERVICE_EXISTS)
		    printf(SERVICE_NAME " Already Exists.\n");
		else
		    printf(SERVICE_NAME " Was not Installed Successfully. Error Code %d\n", (int)GetLastError());
	    }
	}

	CloseServiceHandle( serviceControlManager );
    }
}

void UninstallService()
{
    SC_HANDLE serviceControlManager = OpenSCManager( 0, 0,
						     SC_MANAGER_CONNECT );

    if ( serviceControlManager )
    {
	SC_HANDLE service = OpenService( serviceControlManager,
					 gszServiceName, SERVICE_QUERY_STATUS | DELETE );
	if ( service )
	{
	    SERVICE_STATUS serviceStatus;
	    if ( QueryServiceStatus( service, &serviceStatus ) )
	    {
		if ( serviceStatus.dwCurrentState == SERVICE_STOPPED )
		{
		    if(DeleteService( service ))
			printf(SERVICE_NAME " Removed Successfully\n");
		    else
		    {
			DWORD dwError;
			dwError = GetLastError();
			if(dwError == ERROR_ACCESS_DENIED)
			    printf("Access Denied While trying to Remove " SERVICE_NAME " \n");
			else if(dwError == ERROR_INVALID_HANDLE)
			    printf("Handle invalid while trying to Remove " SERVICE_NAME " \n");
			else if(dwError == ERROR_SERVICE_MARKED_FOR_DELETE)
			    printf(SERVICE_NAME " already marked for deletion\n");
		    }
		}
		else
		{
		    printf(SERVICE_NAME " is still Running.\n");
		}
	    }
	    CloseServiceHandle( service );
	}
	CloseServiceHandle( serviceControlManager );
    }
}


void do_test()
{
    do_tcp = false;
    SOCKET dummy;
    output_data(dummy);
}


void do_debug()
{
    verbose_mode = true;
    do_tcp = false;
    logwatch_send_initial_entries = true;
    logwatch_suppress_info = false;
    SOCKET dummy;
    find_eventlogs(dummy);
    //section_eventlog(dummy);
}

void do_adhoc()
{
    do_tcp = true;
    printf("Listening for TCP connections on port %d\n", CHECK_MK_AGENT_PORT);
    printf("Close window or press Ctrl-C to exit\n");
    fflush(stdout);

    should_terminate = false;
    listen_tcp_loop(); // runs for ever or until Ctrl-C
}

void do_install()
{
    InstallService();
}

void do_remove()
{
    UninstallService();
}

void cleanup()
{
    if (eventlog_buffer_size > 0)
	delete [] eventlog_buffer;
    unregister_all_eventlogs(); // frees a few bytes
}

void show_version()
{
    printf("Check_MK_Agent version %s\n", CHECK_MK_VERSION);
}

int main(int argc, char **argv)
{
    if (argc > 2)
	usage();
    else if (argc <= 1)
	RunService();
    else if (!strcmp(argv[1], "test"))
	do_test();
    else if (!strcmp(argv[1], "adhoc"))
	do_adhoc();
    else if (!strcmp(argv[1], "install"))
	do_install();
    else if (!strcmp(argv[1], "remove"))
	do_remove();
    else if (!strcmp(argv[1], "debug"))
	do_debug();
    else if (!strcmp(argv[1], "version"))
	show_version();
    else
	usage();

    cleanup();
}
