/* Replace passwords in command line from Check_MK password store */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void cmk_bail_out(const char *reason)
{
    fprintf(stderr, "Invalid --pwstore= option: %s\n", reason);
    exit(3);
}


char *cmk_lookup_password(const char *pw_id)
{
    const char *omd_root = getenv("OMD_ROOT");
    if (!omd_root)
        cmk_bail_out("Environment variable OMD_ROOT is missing.");

    char path[512];
    snprintf(path, sizeof(path), "%s/var/check_mk/stored_passwords", omd_root);
    FILE *file = fopen(path, "r");
    if (!file)
        cmk_bail_out("Cannot open stored_passwords file.");

    static char line[512];
    while (NULL != fgets(line, sizeof(line), file)) {
        if (strlen(line) == 0)
            cmk_bail_out("Invalid zero sized line in stored_passwords file.");
        line[strlen(line)-1] = 0; /* Remove \n */
        if (strncmp(line, pw_id, strlen(pw_id)))
            continue;
        if (line[strlen(pw_id)] != ':')
            continue;
        fclose(file);
        return line + strlen(pw_id) + 1;
    }
    fclose(file);
    return NULL;
}


char **cmk_replace_passwords(int *argc, char **argv)
{
    if (*argc < 2)
        return argv; /* command line too short */
    else if (strncmp(argv[1], "--pwstore=", 10))
        return argv; /* no password store in use */

    /* --pwstore=4@4@web,6@0@foo
      In the 4th argument at char 4 replace the following bytes
      with the passwords stored under the ID 'web'
      In the 6th argument at char 0 insert the password with the ID 'foo'
    */

    /* Create copy of arguments and drop first argument */
    char **new_argv = (char **)malloc(sizeof(char *) * (*argc + 1));
    new_argv[0] = argv[0];
    unsigned i;
    for (i=2; i<*argc; i++)
        new_argv[i-1] = argv[i]; /* drop first option */
    new_argv[*argc] = NULL;
    *argc = (*argc) - 1; /* first option was dropped */

    /* Create copy of stuff afgter --pwstore=... so that we can strtok around there */
    char *info = strdup(argv[1] + 10);
    char *p = info;
    char *saveptr;
    while (true) {
        char *tok = strtok_r(p, "@", &saveptr);
        if (tok == NULL)
            break; // finished
        p = NULL; /* subsequent calls to strtok with NULL pointer */
        int argv_index = atoi(tok);
        if (argv_index >= *argc) {
            cmk_bail_out("Invalid argument index");
        }

        tok = strtok_r(NULL, "@", &saveptr);
        if (tok == NULL)
            cmk_bail_out("Missing second @");
        int char_index = atoi(tok);
        if (0 && char_index > strlen(argv[argv_index]))
            cmk_bail_out("Invalid character index");

        char *pw_id = strtok_r(NULL, ",", &saveptr);
        if (pw_id == NULL)
            cmk_bail_out("Missing password ID");

        char *new_arg = strdup(new_argv[argv_index]);
        char *password = cmk_lookup_password(pw_id);
        if (!password)
            cmk_bail_out("No password with that ID found.");
        if (strlen(password) + char_index > strlen(new_arg))
            cmk_bail_out("Password is too long for argument.");
        memcpy(new_arg + char_index, password, strlen(password));
        new_argv[argv_index] = new_arg;
    }
    free(info);
    return new_argv;
}


#define CMK_REPLACE_PASSWORDS do { argv = cmk_replace_passwords(&argc, argv); } while (false);
