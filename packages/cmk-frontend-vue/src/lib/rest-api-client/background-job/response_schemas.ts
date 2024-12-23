/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface BackgroundJobSnapshotObject {
  domain_type: 'background_job'
  extensions: BackgroundJobSnapshot
}

interface BackgroundJobSnapshot {
  status: BackgroundJobStatus
  active: boolean
}

interface BackgroundJobStatus {
  state: string
}

export interface BackgroundJobSpawnResponse {
  job_id: string
  domain_type: 'background_job'
}
