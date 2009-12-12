#ifndef tables_h
#define tables_h

#ifndef EXTERN
#define EXTERN extern
#endif

class TableContacts;
EXTERN TableContacts      *g_table_contacts;
class TableCommands;
EXTERN TableCommands      *g_table_commands;
class TableHosts;
EXTERN TableHosts         *g_table_hosts;
class TableServices;
EXTERN TableServices      *g_table_services;
class TableHostgroups;
EXTERN TableHostgroups    *g_table_hostgroups;
class TableServicegroups;
EXTERN TableServicegroups *g_table_servicegroups;
class TableDownComm;
EXTERN TableDownComm      *g_table_downtimes;
class TableDownComm;
EXTERN TableDownComm      *g_table_comments;
class TableStatus;
EXTERN TableStatus        *g_table_status;
class TableColumns;
EXTERN TableColumns       *g_table_columns;

#endif // tables_h

