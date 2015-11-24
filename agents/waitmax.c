// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#include <errno.h>
#include <getopt.h>
#include <signal.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int g_pid;
static int g_timeout = 0;
static int g_signum = 15;

static void out(const char *buf)
{
    size_t bytes_to_write = strlen(buf);
    while (bytes_to_write > 0) {
        ssize_t written = write(STDERR_FILENO, buf, bytes_to_write);
        if (written == -1) {
            if (errno == EINTR) continue;
            return;
        }
        buf += written;
        bytes_to_write -= written;
    }
}

static void version()
{
    out(
        "waitmax version 1.1\n"
        "Copyright Mathias Kettner 2008\n"
        "This is free software; see the source for copying conditions.  "
        "There is NO\n"
        "warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR "
        "PURPOSE.\n");
    exit(0);
}

static void usage()
{
    out(
        "Usage: waitmax [-s SIGNUM] MAXTIME PROGRAM [ARGS...]\n"
        "\n"
        "Execute PROGRAM as a subprocess. If PROGRAM does not exit before "
        "MAXTIME\n"
        "seconds, it will be killed with SIGTERM or an alternative signal.\n"
        "\n"
        "   -s, --signal SIGNUM   kill with SIGNUM on timeout\n"
        "   -h, --help            this help\n"
        "   -V, --version         show version an exit\n\n");
    exit(1);
}

static void signalhandler(int signum __attribute__((__unused__)))
{
    if (kill(g_pid, g_signum) == 0) g_timeout = 1;
}

static struct option long_options[] = {{"version", no_argument, 0, 'V'},
                                       {"help", no_argument, 0, 'h'},
                                       {"signal", required_argument, 0, 's'},
                                       {0, 0, 0, 0}};

int main(int argc, char **argv)
{
    int indexptr = 0;
    int ret;
    setenv("POSIXLY_CORRECT", "true", 0);
    while (0 <=
           (ret = getopt_long(argc, argv, "Vhs:", long_options, &indexptr))) {
        switch (ret) {
            case 'V': version();

            case 'h': usage();

            case 's':
                g_signum = strtoul(optarg, 0, 10);
                if (g_signum < 1 || g_signum > 32) {
                    out("Signalnumber must be between 1 and 32.\n");
                    exit(1);
                }
                break;

            default: usage(); exit(1);
        }
    }

    if (optind + 1 >= argc) usage();

    int maxtime = atoi(argv[optind]);
    if (maxtime <= 0) usage();

    g_pid = fork();
    if (g_pid == 0) {
        signal(SIGALRM, signalhandler);
        execvp(argv[optind + 1], argv + optind + 1);
        out("Cannot execute ");
        out(argv[optind + 1]);
        out(": ");
        out(strerror(errno));
        out("\n");
        exit(253);
    }

    signal(SIGALRM, signalhandler);
    alarm(maxtime);

    int status;
    while (waitpid(g_pid, &status, 0) == -1) {
        if (errno != EINTR) {
            out("Strange: waitpid() fails: ");
            out(strerror(errno));
            out("\n");
            exit(1);
        }
    }

    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return g_timeout ? 255 : 128 + WTERMSIG(status);
    out("Strange: program did neither exit nor was signalled.\n");
    return 254;
}
