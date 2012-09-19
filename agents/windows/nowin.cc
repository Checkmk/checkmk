#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s MINUTES\n", argv[0]);
        exit(1);
    }
    int minutes = atoi(argv[1]);
    time_t now = time(0);
    time_t then = now + minutes * 60;

    struct tm *t;
    char out[64];
    t = localtime(&now);
    strftime(out, sizeof(out), "%Y-%m-%d %H:%M", t);
    printf("%s ", out);
    t = localtime(&then);
    strftime(out, sizeof(out), "%Y-%m-%d %H:%M", t);
    printf("%s\n", out);
}

