// agent_modbus 1.0
//
// vincent.tacquet@gmail.com
// http://www.tacquet.be

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <iostream>
#include <modbus/modbus.h>

void print_usage(int exitcode)

{
  printf("-----------------------------------------------------------------\n");
  printf("agent_modbus - Vincent Tacquet - 2013 - vincent.tacquet@gmail.com\n");
  printf("version 1.0\n\n");
  printf("usage:   agent_modbus <host ip> <host port> <address:#words(1 or 2):counter|gauge:name> (<address:#words(1 or 2):counter|gauge:name>) ...\n");
  printf("example: agent_modbus 192.168.0.1 502 856:2:counter:active_energy 790:2:gauge:active_power\n");
  printf("-----------------------------------------------------------------\n\n");
  exit(exitcode);

}

int main(int argc, char *argv[])
{
  modbus_t *mb;
  uint16_t tab_reg[32];
  uint32_t mb_doubleword;
  int rc;
  int tcp_port, mb_address, mb_words;
  char* mb_cg;
  char* mb_name;

  if (argc < 4)
    print_usage(2);

  tcp_port = atoi(argv[2]);

  mb = modbus_new_tcp(argv[1], tcp_port);
  modbus_connect(mb);

  int args = 3;

  while (args < argc)
  {
    char* chk;
    chk = strtok(argv[args],":");
    int counter = 0;

    while (chk != NULL)
    {
      counter++;
      if (counter == 1)
        mb_address = atoi(chk);
      else if (counter == 2)
        mb_words = atoi(chk);
      else if (counter == 3)
        mb_cg = chk;
      else if (counter == 4)
        mb_name = chk;
      else
        print_usage(2);
      chk = strtok(NULL,":");
    }


    if (counter == 4)
    {
      rc = modbus_read_registers(mb, mb_address, mb_words, tab_reg);
      if (rc == -1)
      {
        fprintf(stderr, "error:   %s\n", modbus_strerror(errno));
        return -1;
      }

      if (args == 3)
      {
        printf("<<<modbus_value>>>\n");
      }

      if (mb_words == 1)
      {
        printf("%d %d %s %s\n", mb_address, tab_reg[0], mb_cg, mb_name);
      }
      else if (mb_words == 2)
      {
        mb_doubleword = 0;
        mb_doubleword = tab_reg[0] << 16;
        mb_doubleword += tab_reg[1];
        printf("%d %d %s %s\n", mb_address, mb_doubleword, mb_cg, mb_name);
      }
      else
      {
        exit(2);
      }
    }
    else
    {
      exit(2);
    }
    args++;
  }
  modbus_close(mb);
  modbus_free(mb);
  exit(0);
}
