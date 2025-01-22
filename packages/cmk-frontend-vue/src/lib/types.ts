/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface MaybeRestApiCrashReport {
  ext?: {
    details?: {
      crash_report_url?: {
        href?: string
      }
    }
  }
}

export interface MaybeRestApiError {
  detail?: string
  title?: string
}
