// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

/* --------------------------------------------------------------------
   This version of check_icmp has been derived from Andreas Ericsson's
   check_icmp plugin from the Nagios Plugins, which has again been
   derived from another "check_icmp" program, that again was a hack of
   fping.

   We which to thank all of those authors for their work, which saved
   me a lot of time. Long live open source!
 -------------------------------------------------------------------- */

#define DEFAULT_SOCKET_TIMEOUT 10
#define STATE_OK 0
#define STATE_WARNING 1
#define STATE_CRITICAL 2

#define _GNU_SOURCE
#define __USE_BSD

#include <stdint.h>

#ifndef u_int
typedef unsigned int u_int;
typedef unsigned char u_char;
typedef unsigned short u_short;
#endif

#if HAVE_SYS_SOCKIO_H
#include <sys/sockio.h>
#endif
#include <sys/ioctl.h>
#include <sys/time.h>
#include <sys/types.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
#include <ctype.h>
#include <netdb.h>
#include <sys/socket.h>
#include <net/if.h>
#include "/usr/include/netinet/ip_icmp.h"
// #include <netinet/ip_icmp.h>
#include <netinet/in_systm.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <arpa/inet.h>
#include <signal.h>
#include <float.h>

// Stuff needed for livecheck
#include <setjmp.h>
static jmp_buf exit_jmp;
static int exit_code;

/** sometimes undefined system macros (quite a few, actually) **/
#ifndef MAXTTL
# define MAXTTL	255
#endif
#ifndef INADDR_NONE
# define INADDR_NONE (in_addr_t)(-1)
#endif

#ifndef SOL_IP
#define SOL_IP 0
#endif

/* we bundle these in one #ifndef, since they're all from BSD
 * Put individual #ifndef's around those that bother you */
#ifndef ICMP_UNREACH_NET_UNKNOWN
# define ICMP_UNREACH_NET_UNKNOWN 6
# define ICMP_UNREACH_HOST_UNKNOWN 7
# define ICMP_UNREACH_ISOLATED 8
# define ICMP_UNREACH_NET_PROHIB 9
# define ICMP_UNREACH_HOST_PROHIB 10
# define ICMP_UNREACH_TOSNET 11
# define ICMP_UNREACH_TOSHOST 12
#endif
/* tru64 has the ones above, but not these */
#ifndef ICMP_UNREACH_FILTER_PROHIB
# define ICMP_UNREACH_FILTER_PROHIB 13
# define ICMP_UNREACH_HOST_PRECEDENCE 14
# define ICMP_UNREACH_PRECEDENCE_CUTOFF 15
#endif

#ifndef DBL_MAX
# define DBL_MAX 9.9999999999e999
#endif

typedef unsigned short range_t;  /* type for get_range() -- unimplemented */

typedef struct rta_host {
	unsigned short id;           /* id in **table, and icmp pkts */
	char *name;                  /* arg used for adding this host */
	char *msg;                   /* icmp error message, if any */
	struct sockaddr_in saddr_in; /* the address of this host */
	struct in_addr error_addr;   /* stores address of error replies */
	unsigned long long time_waited; /* total time waited, in usecs */
	unsigned int icmp_sent, icmp_recv, icmp_lost; /* counters */
	unsigned char icmp_type, icmp_code; /* type and code from errors */
	unsigned short flags;        /* control/status flags */
	double rta;                  /* measured RTA */
	double rtmax;                /* max rtt */
	double rtmin;                /* min rtt */
	unsigned char pl;            /* measured packet loss */
	struct rta_host *next;       /* linked list */
} rta_host;

#define FLAG_LOST_CAUSE 0x01  /* decidedly dead target. */

/* threshold structure. all values are maximum allowed, exclusive */
typedef struct threshold {
	unsigned char pl;    /* max allowed packet loss in percent */
	unsigned int rta;  /* roundtrip time average, microseconds */
} threshold;

/* the data structure */
typedef struct icmp_ping_data {
	struct timeval stime;	/* timestamp (saved in protocol struct as well) */
	unsigned short ping_id;
} icmp_ping_data;



#define MIN_PING_DATA_SIZE sizeof(struct icmp_ping_data)
#define MAX_IP_PKT_SIZE 65536	/* (theoretical) max IP packet size */
#define IP_HDR_SIZE 20
#define MAX_PING_DATA (MAX_IP_PKT_SIZE - IP_HDR_SIZE - ICMP_MINLEN)
#define DEFAULT_PING_DATA_SIZE (MIN_PING_DATA_SIZE + 44)

/* various target states */
#define TSTATE_INACTIVE 0x01	/* don't ping this host anymore */
#define TSTATE_WAITING 0x02		/* unanswered packets on the wire */
#define TSTATE_ALIVE 0x04       /* target is alive (has answered something) */
#define TSTATE_UNREACH 0x08

/** prototypes **/
void print_help (void);
void print_usage (void);
static u_int get_timevar(const char *);
static u_int get_timevaldiff(struct timeval *, struct timeval *);
static in_addr_t get_ip_address(const char *);
static int wait_for_reply(int, u_int);
static int recvfrom_wto(int, void *, unsigned int, struct sockaddr *, u_int *);
static int send_icmp_ping(int, struct rta_host *);
static int get_threshold(char *str, threshold *th);
static void run_checks(void);
static void set_source_ip(char *);
static int add_target(char *);
static int add_target_ip(char *, struct in_addr *);
static int handle_random_icmp(unsigned char *, struct sockaddr_in *);
static unsigned short icmp_checksum(unsigned short *, int);
static void finish(int);
static void crash(const char *, ...);

/** external **/
extern int optind, opterr, optopt;
extern char *optarg;

/** global variables **/
static struct rta_host **table, *cursor, *list;
static threshold crit = {80, 500000}, warn = {40, 200000};
static int timeout = 10;
static unsigned short icmp_data_size = DEFAULT_PING_DATA_SIZE;
static unsigned short icmp_pkt_size = DEFAULT_PING_DATA_SIZE + ICMP_MINLEN;

static unsigned int icmp_sent = 0, icmp_recv = 0, icmp_lost = 0;
static unsigned short targets_down = 0, targets = 0, packets = 0;
static unsigned int retry_interval, pkt_interval, target_interval;
static int status = STATE_OK;
extern int icmp_sock;
static pid_t pid;
static struct timezone tz;
static struct timeval prog_start;
static unsigned long long max_completion_time = 0;
static unsigned char ttl = 0;	/* outgoing ttl */
static unsigned int warn_down = 1, crit_down = 1; /* host down threshold values */
static int min_hosts_alive = -1;
float pkt_backoff_factor = 1.5;
float target_backoff_factor = 1.5;

#define targets_alive (targets - targets_down)
#define icmp_pkts_en_route (icmp_sent - (icmp_recv + icmp_lost))

char *g_output_buffer;
int g_output_buffer_size;
char *g_output_pointer;

void init_global_variables()
{
    crit.pl = 80;
    crit.rta = 500000;
    warn.pl = 40;
    warn.rta = 200000;
    timeout = 10;
    icmp_data_size = DEFAULT_PING_DATA_SIZE;
    icmp_pkt_size = DEFAULT_PING_DATA_SIZE + ICMP_MINLEN;

    icmp_sent = 0;
    icmp_recv = 0;
    icmp_lost = 0;
    targets_down = 0;
    targets = 0;
    packets = 0;
    status = STATE_OK;
    max_completion_time = 0;
    ttl = 0;
    warn_down = 1;
    crit_down = 1;
    min_hosts_alive = -1;
    pkt_backoff_factor = 1.5;
    target_backoff_factor = 1.5;
}

void do_output(int crash, char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    int place_left = g_output_buffer + g_output_buffer_size - g_output_pointer - 1;
    g_output_pointer += vsnprintf(g_output_pointer, place_left, format, ap);
    va_end(ap);
    *g_output_pointer = 0;
    if (crash) {
        exit_code = 3;
        longjmp(exit_jmp, 1);
    }
}
void do_output_char(char c)
{
    *g_output_pointer++ = c;
}

static const char *
get_icmp_error_msg(unsigned char icmp_type, unsigned char icmp_code)
{
	const char *msg = "unreachable";

	switch(icmp_type) {
	case ICMP_UNREACH:
		switch(icmp_code) {
		case ICMP_UNREACH_NET: msg = "Net unreachable"; break;
		case ICMP_UNREACH_HOST:	msg = "Host unreachable"; break;
		case ICMP_UNREACH_PROTOCOL: msg = "Protocol unreachable (firewall?)"; break;
		case ICMP_UNREACH_PORT: msg = "Port unreachable (firewall?)"; break;
		case ICMP_UNREACH_NEEDFRAG: msg = "Fragmentation needed"; break;
		case ICMP_UNREACH_SRCFAIL: msg = "Source route failed"; break;
		case ICMP_UNREACH_ISOLATED: msg = "Source host isolated"; break;
		case ICMP_UNREACH_NET_UNKNOWN: msg = "Unknown network"; break;
		case ICMP_UNREACH_HOST_UNKNOWN: msg = "Unknown host"; break;
		case ICMP_UNREACH_NET_PROHIB: msg = "Network denied (firewall?)"; break;
		case ICMP_UNREACH_HOST_PROHIB: msg = "Host denied (firewall?)"; break;
		case ICMP_UNREACH_TOSNET: msg = "Bad TOS for network (firewall?)"; break;
		case ICMP_UNREACH_TOSHOST: msg = "Bad TOS for host (firewall?)"; break;
		case ICMP_UNREACH_FILTER_PROHIB: msg = "Prohibited by filter (firewall)"; break;
		case ICMP_UNREACH_HOST_PRECEDENCE: msg = "Host precedence violation"; break;
		case ICMP_UNREACH_PRECEDENCE_CUTOFF: msg = "Precedence cutoff"; break;
		default: msg = "Invalid code"; break;
		}
		break;

	case ICMP_TIMXCEED:
		/* really 'out of reach', or non-existant host behind a router serving
		 * two different subnets */
		switch(icmp_code) {
		case ICMP_TIMXCEED_INTRANS: msg = "Time to live exceeded in transit"; break;
		case ICMP_TIMXCEED_REASS: msg = "Fragment reassembly time exceeded"; break;
		default: msg = "Invalid code"; break;
		}
		break;

	case ICMP_SOURCEQUENCH: msg = "Transmitting too fast"; break;
	case ICMP_REDIRECT: msg = "Redirect (change route)"; break;
	case ICMP_PARAMPROB: msg = "Bad IP header (required option absent)"; break;

		/* the following aren't error messages, so ignore */
	case ICMP_TSTAMP:
	case ICMP_TSTAMPREPLY:
	case ICMP_IREQ:
	case ICMP_IREQREPLY:
	case ICMP_MASKREQ:
	case ICMP_MASKREPLY:
	default: msg = ""; break;
	}

	return msg;
}

static int
handle_random_icmp(unsigned char *packet, struct sockaddr_in *addr)
{
	struct icmp p, sent_icmp;
	struct rta_host *host = NULL;

	memcpy(&p, packet, sizeof(p));
	if(p.icmp_type == ICMP_ECHO && ntohs(p.icmp_id) == pid) {
		/* echo request from us to us (pinging localhost) */
		return 0;
	}

	/* only handle a few types, since others can't possibly be replies to
	 * us in a sane network (if it is anyway, it will be counted as lost
	 * at summary time, but not as quickly as a proper response */
	/* TIMXCEED can be an unreach from a router with multiple IP's which
	 * serves two different subnets on the same interface and a dead host
	 * on one net is pinged from the other. The router will respond to
	 * itself and thus set TTL=0 so as to not loop forever.  Even when
	 * TIMXCEED actually sends a proper icmp response we will have passed
	 * too many hops to have a hope of reaching it later, in which case it
	 * indicates overconfidence in the network, poor routing or both. */
	if(p.icmp_type != ICMP_UNREACH && p.icmp_type != ICMP_TIMXCEED &&
	   p.icmp_type != ICMP_SOURCEQUENCH && p.icmp_type != ICMP_PARAMPROB)
	{
		return 0;
	}

	/* might be for us. At least it holds the original package (according
	 * to RFC 792). If it isn't, just ignore it */
	memcpy(&sent_icmp, packet + 28, sizeof(sent_icmp));
	if(sent_icmp.icmp_type != ICMP_ECHO || ntohs(sent_icmp.icmp_id) != pid ||
	   ntohs(sent_icmp.icmp_seq) >= targets*packets)
	{
		return 0;
	}

	/* it is indeed a response for us */
	host = table[ntohs(sent_icmp.icmp_seq)/packets];

	icmp_lost++;
	host->icmp_lost++;
	/* don't spend time on lost hosts any more */
	if(host->flags & FLAG_LOST_CAUSE) return 0;

	/* source quench means we're sending too fast, so increase the
	 * interval and mark this packet lost */
	if(p.icmp_type == ICMP_SOURCEQUENCH) {
		pkt_interval *= pkt_backoff_factor;
		target_interval *= target_backoff_factor;
	}
	else {
		targets_down++;
		host->flags |= FLAG_LOST_CAUSE;
	}
	host->icmp_type = p.icmp_type;
	host->icmp_code = p.icmp_code;
	host->error_addr.s_addr = addr->sin_addr.s_addr;

	return 0;
}


/* This was the main() function of the original check_icmp. */
int check_icmp(int argc, char **argv, char *output, int size)
{
    init_global_variables();

    g_output_buffer = output;
    g_output_buffer_size = size;
    g_output_pointer = output;

    icmp_sock = socket(PF_INET, SOCK_RAW, IPPROTO_ICMP);

    exit_code = 3;
    if (setjmp(exit_jmp)) {
        close(icmp_sock);
        struct rta_host *h = list;
        while (h) {
            free(h->name);
            struct rta_host *n = h->next;
            free(h);
            h = n;
        }
        if (table)
            free(table);
        return exit_code;
    }

    int i;
    char *ptr;
    long int arg;
    int icmp_sockerrno;
    int result;
    struct rta_host *host;

    /* we only need to be setsuid when we get the sockets, so do
     * that before pointer magic (esp. on network data) */
    icmp_sockerrno = 0;

    /* POSIXLY_CORRECT might break things, so unset it (the portable way) */
    unsetenv("POSIXLY_CORRECT");

    /* use the pid to mark packets as ours */
    /* Some systems have 32-bit pid_t so mask off only 16 bits */
    pid = getpid() & 0xffff;

    cursor = list = NULL;
    table = NULL;

    crit.rta = 500000;
    crit.pl = 80;
    warn.rta = 200000;
    warn.pl = 40;
    pkt_interval = 80000;  /* 80 msec packet interval by default */
    packets = 5;


    /* parse the arguments */
    for(i = 1; i < argc; i++) {
    	while((arg = getopt(argc, argv, "w:c:n:p:t:H:s:i:b:I:l:m:")) != EOF) {
    		long size;
    		switch(arg) {
    		case 'b':
    			size = strtol(optarg,NULL,0);
    			if (size >= (sizeof(struct icmp) + sizeof(struct icmp_ping_data)) &&
    			    size < MAX_PING_DATA) {
    				icmp_data_size = size;
    				icmp_pkt_size = size + ICMP_MINLEN;
    			}
                            break;
    		case 'i':
    			pkt_interval = get_timevar(optarg);
    			break;
    		case 'I':
    			target_interval = get_timevar(optarg);
    			break;
    		case 'w':
    			get_threshold(optarg, &warn);
    			break;
    		case 'c':
    			get_threshold(optarg, &crit);
    			break;
    		case 'n':
    		case 'p':
    			packets = strtoul(optarg, NULL, 0);
    			break;
    		case 't':
    			timeout = strtoul(optarg, NULL, 0);
    			if(!timeout) timeout = 10;
    			break;
    		case 'H':
    			add_target(optarg);
    			break;
    		case 'l':
    			ttl = (unsigned char)strtoul(optarg, NULL, 0);
    			break;
    		case 'm':
    			min_hosts_alive = (int)strtoul(optarg, NULL, 0);
    			break;
    		case 'd': /* implement later, for cluster checks */
    			warn_down = (unsigned char)strtoul(optarg, &ptr, 0);
    			if(ptr) {
    				crit_down = (unsigned char)strtoul(ptr + 1, NULL, 0);
    			}
    			break;
    		case 's': /* specify source IP address */
    			set_source_ip(optarg);
    			break;
    		}
    	}
    }

    argv = &argv[optind];
    while(*argv) {
    	add_target(*argv);
    	argv++;
    }
    if(!targets) {
    	errno = 0;
    	do_output(1, "No hosts to check");
        exit_code = 3;
        longjmp(exit_jmp, 1);
    }

    if(!ttl) ttl = 64;

    if(icmp_sock) {
    	result = setsockopt(icmp_sock, SOL_IP, IP_TTL, &ttl, sizeof(ttl));
    }

    /* stupid users should be able to give whatever thresholds they want
     * (nothing will break if they do), but some anal plugin maintainer
     * will probably add some printf() thing here later, so it might be
     * best to at least show them where to do it. ;) */
    if(warn.pl > crit.pl) warn.pl = crit.pl;
    if(warn.rta > crit.rta) warn.rta = crit.rta;
    if(warn_down > crit_down) crit_down = warn_down;

    signal(SIGINT, finish);
    signal(SIGHUP, finish);
    signal(SIGTERM, finish);
    signal(SIGALRM, finish);
    alarm(timeout);

    /* make sure we don't wait any longer than necessary */
    gettimeofday(&prog_start, &tz);
    max_completion_time =
    	((targets * packets * pkt_interval) + (targets * target_interval)) +
    	(targets * packets * crit.rta) + crit.rta;

    if(packets > 20) {
    	errno = 0;
    	do_output(1, "packets is > 20 (%d)", packets);
    }

    if(min_hosts_alive < -1) {
    	errno = 0;
    	do_output(1, "minimum alive hosts is negative (%i)", min_hosts_alive);
    }

    host = list;
    table = malloc(sizeof(struct rta_host **) * (argc - 1));
    i = 0;
    while(host) {
    	host->id = i*packets;
    	table[i] = host;
    	host = host->next;
    	i++;
    }

    run_checks();

    errno = 0;
    finish(0);

    exit_code = 0;
    longjmp(exit_jmp, 1);
}

static void
run_checks()
{
	u_int i, t, result;
	u_int final_wait, time_passed;

	/* this loop might actually violate the pkt_interval or target_interval
	 * settings, but only if there aren't any packets on the wire which
	 * indicates that the target can handle an increased packet rate */
	for(i = 0; i < packets; i++) {
		for(t = 0; t < targets; t++) {
			/* don't send useless packets */
			if(!targets_alive) finish(0);
			if(table[t]->flags & FLAG_LOST_CAUSE) {
				continue;
			}

			/* we're still in the game, so send next packet */
			(void)send_icmp_ping(icmp_sock, table[t]);
			result = wait_for_reply(icmp_sock, target_interval);
		}
		result = wait_for_reply(icmp_sock, pkt_interval * targets);
	}

	if(icmp_pkts_en_route && targets_alive) {
		time_passed = get_timevaldiff(NULL, NULL);
		final_wait = max_completion_time - time_passed;

		if(time_passed > max_completion_time) {
			finish(0);
		}

		/* catch the packets that might come in within the timeframe, but
		 * haven't yet */
		result = wait_for_reply(icmp_sock, final_wait);
	}
}

/* response structure:
 * ip header   : 20 bytes
 * icmp header : 28 bytes
 * icmp echo reply : the rest
 */
static int
wait_for_reply(int sock, u_int t)
{
	int n, hlen;
	static unsigned char buf[4096];
	struct sockaddr_in resp_addr;
	struct ip *ip;
	struct icmp icp;
	struct rta_host *host;
	struct icmp_ping_data data;
	struct timeval wait_start, now;
	u_int tdiff, i, per_pkt_wait;

	/* if we can't listen or don't have anything to listen to, just return */
	if(!t || !icmp_pkts_en_route) return 0;

	gettimeofday(&wait_start, &tz);

	i = t;
	per_pkt_wait = t / icmp_pkts_en_route;
	while(icmp_pkts_en_route && get_timevaldiff(&wait_start, NULL) < i) {
		t = per_pkt_wait;

		/* wrap up if all targets are declared dead */
		if(!targets_alive ||
		   get_timevaldiff(&prog_start, NULL) >= max_completion_time)
		{
			finish(0);
		}

		/* reap responses until we hit a timeout */
		n = recvfrom_wto(sock, buf, sizeof(buf),
						 (struct sockaddr *)&resp_addr, &t);
		if(!n) {
			continue;	/* timeout for this one, so keep trying */
		}
		if(n < 0) {
			return n;
		}

		ip = (struct ip *)buf;

/* obsolete. alpha on tru64 provides the necessary defines, but isn't broken */
/* #if defined( __alpha__ ) && __STDC__ && !defined( __GLIBC__ ) */
		/* alpha headers are decidedly broken. Using an ansi compiler,
		 * they provide ip_vhl instead of ip_hl and ip_v, so we mask
		 * off the bottom 4 bits */
/* 		hlen = (ip->ip_vhl & 0x0f) << 2; */
/* #else */
		hlen = ip->ip_hl << 2;
/* #endif */

		if(n < (hlen + ICMP_MINLEN)) {
			do_output(1, "received packet too short for ICMP (%d bytes, expected %d) from %s\n",
				  n, hlen + icmp_pkt_size, inet_ntoa(resp_addr.sin_addr));
		}

		/* check the response */
		memcpy(&icp, buf + hlen, sizeof(icp));

		if(ntohs(icp.icmp_id) != pid || icp.icmp_type != ICMP_ECHOREPLY ||
		   ntohs(icp.icmp_seq) >= targets*packets) {
			handle_random_icmp(buf + hlen, &resp_addr);
			continue;
		}

		/* this is indeed a valid response */
		memcpy(&data, icp.icmp_data, sizeof(data));

		host = table[ntohs(icp.icmp_seq)/packets];
		gettimeofday(&now, &tz);
		tdiff = get_timevaldiff(&data.stime, &now);

		host->time_waited += tdiff;
		host->icmp_recv++;
		icmp_recv++;
		if (tdiff > host->rtmax)
			host->rtmax = tdiff;
		if (tdiff < host->rtmin)
			host->rtmin = tdiff;
	}

	return 0;
}

/* the ping functions */
static int
send_icmp_ping(int sock, struct rta_host *host)
{
        char buf[icmp_pkt_size]; // avoid malloc
	static union {
		void *buf; /* re-use so we prevent leaks */
		struct icmp *icp;
		u_short *cksum_in;
	} packet = { NULL };
        packet.buf = buf;

	long int len;
	struct icmp_ping_data data;
	struct timeval tv;
	struct sockaddr *addr;

	if(sock == -1) {
		errno = 0;
		do_output(1, "Attempt to send on bogus socket");
		return -1;
	}
	addr = (struct sockaddr *)&host->saddr_in;

        // Mathias -> Andreas: how can packet.buf be != 0 here?
	memset(packet.buf, 0, icmp_pkt_size);

	if((gettimeofday(&tv, &tz)) == -1) return -1;

	data.ping_id = 10; /* host->icmp.icmp_sent; */
	memcpy(&data.stime, &tv, sizeof(tv));
	memcpy(&packet.icp->icmp_data, &data, sizeof(data));
	packet.icp->icmp_type = ICMP_ECHO;
	packet.icp->icmp_code = 0;
	packet.icp->icmp_cksum = 0;
	packet.icp->icmp_id = htons(pid);
	packet.icp->icmp_seq = htons(host->id++);
	packet.icp->icmp_cksum = icmp_checksum(packet.cksum_in, icmp_pkt_size);


	len = sendto(sock, packet.buf, icmp_pkt_size, 0, (struct sockaddr *)addr,
				 sizeof(struct sockaddr));
	if(len < 0 || (unsigned int)len != icmp_pkt_size) {
		return -1;
	}

	icmp_sent++;
	host->icmp_sent++;
	return 0;
}

static int
recvfrom_wto(int sock, void *buf, unsigned int len, struct sockaddr *saddr,
			 u_int *timo)
{
	u_int slen;
	int n;
	struct timeval to, then, now;
	fd_set rd, wr;

	if(!*timo) {
		return 0;
	}

	to.tv_sec = *timo / 1000000;
	to.tv_usec = (*timo - (to.tv_sec * 1000000));

	FD_ZERO(&rd);
	FD_ZERO(&wr);
	FD_SET(sock, &rd);
	errno = 0;
	gettimeofday(&then, &tz);
	n = select(sock + 1, &rd, &wr, NULL, &to);
	if(n < 0) do_output(1, "select() in recvfrom_wto");
	gettimeofday(&now, &tz);
	*timo = get_timevaldiff(&then, &now);

	if(!n) return 0;				/* timeout */

	slen = sizeof(struct sockaddr);

	return recvfrom(sock, buf, len, 0, saddr, &slen);
}

static void
finish(int sig)
{
	u_int i = 0;
	unsigned char pl;
	double rta;
	struct rta_host *host;
	const char *status_string[] =
	{"OK", "WARNING", "CRITICAL", "UNKNOWN", "DEPENDENT"};
	int hosts_ok = 0;
	int hosts_warn = 0;

	alarm(0);

	/* iterate thrice to calculate values, give output, and print perfparse */
	host = list;
	while(host) {
		if(!host->icmp_recv) {
			/* rta 0 is ofcourse not entirely correct, but will still show up
			 * conspicuosly as missing entries in perfparse and cacti */
			pl = 100;
			rta = 0;
			status = STATE_CRITICAL;
			/* up the down counter if not already counted */
			if(!(host->flags & FLAG_LOST_CAUSE) && targets_alive) targets_down++;
		}
		else {
			pl = ((host->icmp_sent - host->icmp_recv) * 100) / host->icmp_sent;
			rta = (double)host->time_waited / host->icmp_recv;
		}
		host->pl = pl;
		host->rta = rta;
		if(pl >= crit.pl || rta >= crit.rta) {
			status = STATE_CRITICAL;
		}
		else if(!status && (pl >= warn.pl || rta >= warn.rta)) {
			status = STATE_WARNING;
			hosts_warn++;
		}
		else {
			hosts_ok++;
		}

		host = host->next;
	}
	/* this is inevitable */
	if(!targets_alive) status = STATE_CRITICAL;
	if(min_hosts_alive > -1) {
		if(hosts_ok >= min_hosts_alive) status = STATE_OK;
		else if((hosts_ok + hosts_warn) >= min_hosts_alive) status = STATE_WARNING;
	}
	do_output(0, "%s - ", status_string[status]);

	host = list;
	while(host) {
		if(i) {
			if(i < targets) do_output(0, " :: ");
			else do_output(0, "\n");
		}
		i++;
		if(!host->icmp_recv) {
			status = STATE_CRITICAL;
			if(host->flags & FLAG_LOST_CAUSE) {
				do_output(0, "%s: %s @ %s. rta nan, lost %d%%",
					   host->name,
					   get_icmp_error_msg(host->icmp_type, host->icmp_code),
					   inet_ntoa(host->error_addr),
					   100);
			}
			else { /* not marked as lost cause, so we have no flags for it */
				do_output(0, "%s: rta nan, lost 100%%", host->name);
			}
		}
		else {	/* !icmp_recv */
			do_output(0, "%s: rta %0.3fms, lost %u%%",
				   host->name, host->rta / 1000, host->pl);
		}

		host = host->next;
	}

	/* iterate once more for pretty perfparse output */
        do_output_char('|');
	i = 0;
	host = list;
	while(host) {
		do_output(0, "%srta=%0.3fms;%0.3f;%0.3f;0; %spl=%u%%;%u;%u;; %srtmax=%0.3fms;;;; %srtmin=%0.3fms;;;; ",
			   (targets > 1) ? host->name : "",
			   host->rta / 1000, (float)warn.rta / 1000, (float)crit.rta / 1000,
			   (targets > 1) ? host->name : "", host->pl, warn.pl, crit.pl,
			   (targets > 1) ? host->name : "", (float)host->rtmax / 1000,
			   (targets > 1) ? host->name : "", (host->rtmin < DBL_MAX) ? (float)host->rtmin / 1000 : (float)0);

		host = host->next;
	}

	if(min_hosts_alive > -1) {
		if(hosts_ok >= min_hosts_alive) status = STATE_OK;
		else if((hosts_ok + hosts_warn) >= min_hosts_alive) status = STATE_WARNING;
	}

	/* finish with an empty line */
        do_output_char('\n');

        exit_code = status;
        longjmp(exit_jmp, 1);
}

static u_int
get_timevaldiff(struct timeval *early, struct timeval *later)
{
	u_int ret;
	struct timeval now;

	if(!later) {
		gettimeofday(&now, &tz);
		later = &now;
	}
	if(!early) early = &prog_start;

	/* if early > later we return 0 so as to indicate a timeout */
	if(early->tv_sec > later->tv_sec ||
	   (early->tv_sec == later->tv_sec && early->tv_usec > later->tv_usec))
	{
		return 0;
	}

	ret = (later->tv_sec - early->tv_sec) * 1000000;
	ret += later->tv_usec - early->tv_usec;

	return ret;
}

static int
add_target_ip(char *arg, struct in_addr *in)
{
	struct rta_host *host;

	/* disregard obviously stupid addresses */
	if(in->s_addr == INADDR_NONE || in->s_addr == INADDR_ANY)
		return -1;

	/* no point in adding two identical IP's, so don't. ;) */
	host = list;
	while(host) {
		if(host->saddr_in.sin_addr.s_addr == in->s_addr) {
			return -1;
		}
		host = host->next;
	}

	/* add the fresh ip */
	host = malloc(sizeof(struct rta_host));
	if(!host) {
		do_output(1, "add_target_ip(%s, %s): malloc(%d) failed",
			  arg, inet_ntoa(*in), sizeof(struct rta_host));
	}
	memset(host, 0, sizeof(struct rta_host));

	/* set the values. use calling name for output */
	host->name = strdup(arg);

	/* fill out the sockaddr_in struct */
	host->saddr_in.sin_family = AF_INET;
	host->saddr_in.sin_addr.s_addr = in->s_addr;

	host->rtmin = DBL_MAX;

	if(!list) list = cursor = host;
	else cursor->next = host;

	cursor = host;
	targets++;

	return 0;
}

/* wrapper for add_target_ip */
static int
add_target(char *arg)
{
	int i;
	struct hostent *he;
	struct in_addr *in, ip;

	/* don't resolve if we don't have to */
	if((ip.s_addr = inet_addr(arg)) != INADDR_NONE) {
		/* don't add all ip's if we were given a specific one */
		return add_target_ip(arg, &ip);
		/* he = gethostbyaddr((char *)in, sizeof(struct in_addr), AF_INET); */
		/* if(!he) return add_target_ip(arg, in); */
	}
	else {
		errno = 0;
		he = gethostbyname(arg);
		if(!he) {
			errno = 0;
			do_output(1, "Failed to resolve %s", arg);
			return -1;
		}
	}

	/* possibly add all the IP's as targets */
	for(i = 0; he->h_addr_list[i]; i++) {
		in = (struct in_addr *)he->h_addr_list[i];
		add_target_ip(arg, in);
		break;
	}

	return 0;
}

static void
set_source_ip(char *arg)
{
	struct sockaddr_in src;

	memset(&src, 0, sizeof(src));
	src.sin_family = AF_INET;
	if((src.sin_addr.s_addr = inet_addr(arg)) == INADDR_NONE)
		src.sin_addr.s_addr = get_ip_address(arg);
	if(bind(icmp_sock, (struct sockaddr *)&src, sizeof(src)) == -1)
		do_output(1, "Cannot bind to IP address %s", arg);
}

/* TODO: Move this to netutils.c and also change check_dhcp to use that. */
static in_addr_t
get_ip_address(const char *ifname)
{
#if defined(SIOCGIFADDR)
	struct ifreq ifr;
	struct sockaddr_in ip;

	strncpy(ifr.ifr_name, ifname, sizeof(ifr.ifr_name) - 1);
	ifr.ifr_name[sizeof(ifr.ifr_name) - 1] = '\0';
	if(ioctl(icmp_sock, SIOCGIFADDR, &ifr) == -1)
		do_output(1, "Cannot determine IP address of interface %s", ifname);
	memcpy(&ip, &ifr.ifr_addr, sizeof(ip));
	return ip.sin_addr.s_addr;
#else
	errno = 0;
	do_output(1, "Cannot get interface IP address on this platform.");
#endif
}

/*
 * u = micro
 * m = milli
 * s = seconds
 * return value is in microseconds
 */
static u_int
get_timevar(const char *str)
{
	char p, u, *ptr;
	unsigned int len;
	u_int i, d;	            /* integer and decimal, respectively */
	u_int factor = 1000;    /* default to milliseconds */

	if(!str) return 0;
	len = strlen(str);
	if(!len) return 0;

	/* unit might be given as ms|m (millisec),
	 * us|u (microsec) or just plain s, for seconds */
	u = p = '\0';
	u = str[len - 1];
	if(len >= 2 && !isdigit((int)str[len - 2])) p = str[len - 2];
	if(p && u == 's') u = p;
	else if(!p) p = u;

	if(u == 'u') factor = 1;            /* microseconds */
	else if(u == 'm') factor = 1000;	/* milliseconds */
	else if(u == 's') factor = 1000000;	/* seconds */

	i = strtoul(str, &ptr, 0);
	if(!ptr || *ptr != '.' || strlen(ptr) < 2 || factor == 1)
		return i * factor;

	/* time specified in usecs can't have decimal points, so ignore them */
	if(factor == 1) return i;

	d = strtoul(ptr + 1, NULL, 0);

	/* d is decimal, so get rid of excess digits */
	while(d >= factor) d /= 10;

	/* the last parenthesis avoids floating point exceptions. */
	return ((i * factor) + (d * (factor / 10)));
}

/* not too good at checking errors, but it'll do (main() should barfe on -1) */
static int
get_threshold(char *str, threshold *th)
{
	char *p = NULL, i = 0;

	if(!str || !strlen(str) || !th) return -1;

	/* pointer magic slims code by 10 lines. i is bof-stop on stupid libc's */
	p = &str[strlen(str) - 1];
	while(p != &str[1]) {
		if(*p == '%') *p = '\0';
		else if(*p == ',' && i) {
			*p = '\0';	/* reset it so get_timevar(str) works nicely later */
			th->pl = (unsigned char)strtoul(p+1, NULL, 0);
			break;
		}
		i = 1;
		p--;
	}
	th->rta = get_timevar(str);

	if(!th->rta) return -1;

	if(th->rta > MAXTTL * 1000000) th->rta = MAXTTL * 1000000;
	if(th->pl > 100) th->pl = 100;

	return 0;
}

unsigned short
icmp_checksum(unsigned short *p, int n)
{
	register unsigned short cksum;
	register long sum = 0;

	while(n > 1) {
		sum += *p++;
		n -= 2;
	}

	/* mop up the occasional odd byte */
	if(n == 1) sum += (unsigned char)*p;

	sum = (sum >> 16) + (sum & 0xffff);	/* add hi 16 to low 16 */
	sum += (sum >> 16);			/* add carry */
	cksum = ~sum;				/* ones-complement, trunc to 16 bits */

	return cksum;
}

