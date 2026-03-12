/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const BACKOFF_BASE_SECONDS = 10
const BACKOFF_MAX_SECONDS = 120

export class BackoffTracker {
  _consecutive_failures = 0
  _suspend_until = 0

  report_failure() {
    this._consecutive_failures++
    const backoff = Math.min(
      BACKOFF_BASE_SECONDS * Math.pow(2, this._consecutive_failures - 1),
      BACKOFF_MAX_SECONDS
    )
    this._suspend_until = Math.floor(Date.now() / 1000) + backoff
  }

  report_success() {
    this._consecutive_failures = 0
    this._suspend_until = 0
  }

  is_suspended(): boolean {
    return Math.floor(Date.now() / 1000) < this._suspend_until
  }
}
