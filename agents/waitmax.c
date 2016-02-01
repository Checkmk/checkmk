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

static pid_t g_pid = 0;
static int g_timeout = 0;
static int g_signum = SIGTERM;

static void out(const char *buf) {
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

static void exit_with(const char *message, int err, int status) {
    out(message);
    if (err != 0) {
        out(": ");
        out(strerror(errno));
    }
    out("\n");
    exit(status);
}

static void version() {
    exit_with(
        "waitmax version 1.1\n"
        "Copyright Mathias Kettner 2008\n"
        "This is free software; see the source for copying conditions.  "
        "There is NO\n"
        "warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR "
        "PURPOSE.",
        0, 0);
}

static void usage(int status) {
    exit_with(
        "Usage: waitmax [-s SIGNUM] MAXTIME PROGRAM [ARGS...]\n"
        "\n"
        "Execute PROGRAM as a subprocess. If PROGRAM does not exit before "
        "MAXTIME\n"
        "seconds, it will be killed with SIGTERM or an alternative signal.\n"
        "\n"
        "   -s, --signal SIGNUM   kill with SIGNUM on timeout\n"
        "   -h, --help            this help\n"
        "   -V, --version         show version an exit\n",
        0, status);
}

static void kill_group(pid_t pid, int signum) {
    /* The child might have become a process group leader itself, so send the
       signal directly to it. */
    kill(pid, signum);

    /* Guard against harakiri... */
    signal(signum, SIG_IGN);

    /* Send the signal to all processes in our fresh process group. */
    kill(0, signum);
}

static void signalhandler(int signum) {
    if (signum == SIGALRM) {
        /* The child took too long, so remember that we timed out and send the
           configured signal instead of SIGALRM. */
        g_timeout = 1;
        signum = g_signum;
    }

    /* Are we the child process or has the child not been execvp'd yet? */
    if (g_pid == 0) exit(signum + 128);

    /* Send the configure signal to our process group. */
    kill_group(g_pid, signum);

    /* Make sure the children actually react on the signal. */
    if (signum != SIGKILL && signum != SIGCONT) kill_group(g_pid, SIGCONT);
}

static void setup_signal_handlers() {
    struct sigaction sa;
    sigemptyset(&sa.sa_mask);
    sa.sa_handler = signalhandler;
    sa.sa_flags = SA_RESTART; /* just to be sure... */
    sigaction(g_signum, &sa, NULL);
    sigaction(SIGALRM, &sa, NULL);
    sigaction(SIGHUP, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGQUIT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    /* Guard against a background child doing I/O on the tty. */
    sa.sa_handler = SIG_IGN;
    sigaction(SIGTTIN, &sa, NULL);
    sigaction(SIGTTOU, &sa, NULL);

    /* Make sure that waitpid won't fail. */
    sa.sa_handler = SIG_DFL;
    sigaction(SIGCHLD, &sa, NULL);
}

static void unblock_signal(int signum) {
    sigset_t signals_to_unblock;
    sigemptyset(&signals_to_unblock);
    sigaddset(&signals_to_unblock, signum);
    if (sigprocmask(SIG_UNBLOCK, &signals_to_unblock, NULL) == -1)
        exit_with("sigprocmask failed", errno, 1);
}

static struct option long_options[] = {{"version", no_argument, 0, 'V'},
                                       {"help", no_argument, 0, 'h'},
                                       {"signal", required_argument, 0, 's'},
                                       {0, 0, 0, 0}};

int main(int argc, char **argv) {
    /* Note: setenv calls malloc, and 'diet' warns about that. */
    if (getenv("POSIXLY_CORRECT") == NULL) putenv("POSIXLY_CORRECT=true");
    int ret;
    while ((ret = getopt_long(argc, argv, "Vhs:", long_options, NULL)) != -1) {
        switch (ret) {
            case 'V':
                version();
                break;

            case 'h':
                usage(0);
                break;

            case 's':
                g_signum = atoi(optarg);
                if (g_signum < 1 || g_signum > 32)
                    exit_with("Signalnumber must be between 1 and 32.", 0, 1);
                break;

            default:
                usage(1);
                break;
        }
    }

    if (optind + 1 >= argc) usage(1);

    int maxtime = atoi(argv[optind]);
    if (maxtime <= 0) usage(1);

    /* Create a new process group with ourselves as the process group
       leader. This way we can send a signal to all subprocesses later (unless
       some non-direct descendant creates its own process group). Doing this in
       the parent process already simplifies things, because we don't have to
       worry about foreground/background groups then. */
    setpgid(0, 0);

    /* Setting up signal handlers before forking avoids race conditions with the
       child. */
    setup_signal_handlers();

    g_pid = fork();
    if (g_pid == -1) exit_with("fork() failed", errno, 1);

    if (g_pid == 0) {
        /* Restore tty behavior in the child. */
        struct sigaction sa;
        sigemptyset(&sa.sa_mask);
        sa.sa_flags = SA_RESTART; /* just to be sure... */
        sa.sa_handler = SIG_DFL;
        sigaction(SIGTTIN, &sa, NULL);
        sigaction(SIGTTOU, &sa, NULL);

        execvp(argv[optind + 1], argv + optind + 1);
        exit_with(argv[optind + 1], errno, 253);
    }

    /* Make sure SIGALRM is not blocked (e.g. by parent). */
    unblock_signal(SIGALRM);
    alarm(maxtime);

    int status;
    while (waitpid(g_pid, &status, 0) == -1) {
        if (errno != EINTR) exit_with("waitpid() failed", errno, 1);
    }

    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return g_timeout ? 255 : 128 + WTERMSIG(status);
    exit_with("Program did neither exit nor was signalled.", 0, 254);
    return 0; /* Make GCC happy. */
}
