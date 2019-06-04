//
// THIS is pre-compiled header for Engine Project
//
#pragma once
#ifndef ENGINE_STDAFX_H__
#define ENGINE_STDAFX_H__

#if defined(_MSC_VER)
// more agressive warning
#pragma warning(3 : 4062)
#endif

#include "stdafx_defines.h"  // shared use, watest!

// settings for the LWA
#define _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING
#define SI_SUPPORT_IOSTREAMS
#define USE_EXPERIMENTAL_FILESYSTEM  // #TODO recheck with 2019

#include "asio.h"
#include "common/cfg_info.h"  // internal tracing and dumping
#include "common/version.h"
#include "logger.h"
#include "tools/_raii.h"  // ON_OUT_OF_SCOPE
#include "tools/_xlog.h"  // internal tracing and dumping

#endif  // ENGINE_STDAFX_H__
