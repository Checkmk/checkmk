// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// This program enumerates all 16-bit tasks on the system and tries
// to find the program name specified by the first argument

// Can be included as mrpe script

// On success it returns with exit code 0
// {program} is running. Path of executable: {Path of program}

// On failure it returns with exit code 2
// {program} not running.

// Note: It seems that the 16 Bit program threads runnning inside ntvdm.exe
//       are always uppercase. Because of this fact the program name is
//       internally converted to uppercase.


#include <stdafx.h>
#include <windows.h>
#include <stdio.h>
#include <iostream>
#include <string>
#include <vdmdbg.h>

using namespace std;

BOOL WINAPI ProcessVDMs( DWORD, DWORD, LPARAM );
BOOL WINAPI ProcessTasks( DWORD, WORD, WORD, PSZ, PSZ, LPARAM );

#pragma comment( lib, "vdmdbg.lib" )

void usage() {
	printf("Usage: check_16bit_process.exe {program}");
}

string program_to_check;

void main(int argc, char* argv[])
{
	if (argc != 2) {
		usage();
		exit(1);
	}

	program_to_check = string(argv[1]);
	for (unsigned int k = 0; k < program_to_check.length(); k++)
		program_to_check[k] = toupper(program_to_check[k]);

    // Enumerate VDMs
    VDMEnumProcessWOW(
        (PROCESSENUMPROC)ProcessVDMs,
        (LPARAM)NULL
    );

	printf("%s is not running", program_to_check.c_str());
	exit(2);
}

BOOL WINAPI ProcessVDMs( DWORD dwProcessId, DWORD dwAttrib,
    LPARAM t )
{
	// Might be useful some day
    // printf("\nProcess ID: %d\n", dwProcessId);

    // Use process ID of VDM to enumerate through its tasks
    VDMEnumTaskWOWEx(
        dwProcessId,
        (TASKENUMPROCEX)ProcessTasks,
        (LPARAM)NULL
    );

    // Keep enumerating
    return FALSE;
}

BOOL WINAPI ProcessTasks( DWORD dwThreadId, WORD hMod16, WORD hTask16,
    PSZ pszModName, PSZ pszFileName, LPARAM lParam )
{
	//Task's information
	//Might be useful some day
    //printf("Thread ID: %d\n", dwThreadId);
    //printf("Module handle: %d\n", hMod16);
    //printf("Task handle: %d\n", hTask16);
    //printf("Module Name: %s\n", pszModName);
    //printf("File Name: %s\n", pszFileName);

	string thread_filename = string(pszFileName);
	if (0 == thread_filename.compare(thread_filename.length() - program_to_check.length(),
		program_to_check.length(), program_to_check)) {
			printf("%s is running. Path of executable: %s", program_to_check.c_str(), thread_filename.c_str());
			exit(0);
	}


    // Keep enumerating
    return FALSE;
}

