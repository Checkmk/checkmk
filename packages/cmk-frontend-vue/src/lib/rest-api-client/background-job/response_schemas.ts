/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

interface BackgroundJobStatus {
  state: string
  log_info: {
    JobProgressUpdate: string[]
    JobResult: string[]
    JobException: string[]
  }
}

interface BackgroundJobSnapshot {
  status: BackgroundJobStatus
  active: boolean
}

export interface BackgroundJobSpawnResponse {
  id: string
  domainType: 'background_job'
  extensions: BackgroundJobSnapshot
}
export interface BackgroundJobSnapshotObject {
  domainType: 'background_job'
  extensions: BackgroundJobSnapshot
}
