/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface NumberOfPendingChangesResponse {
  number_of_pending_changes: number
}

export interface StatusPerSiteResponse {
  site: string
  phase: 'initialized' | 'queued' | 'started' | 'sync' | 'activate' | 'finishing' | 'done'
  state: 'warning' | 'success' | 'error'
  status_text: string
  status_details: string
  start_time: string
  end_time: string
}

// We only really care about the status_per_site & is_running. The rest is not used in the UI
export interface ActivationExtensionsResponse {
  sites: Array<string>
  is_running: boolean
  force_foreign_changes: boolean
  time_started: string
  changes: Array<object>
  status_per_site: Array<StatusPerSiteResponse>
}

// We only really care about the extensions. The rest is not used in the UI
export interface ActivationStatusResponse {
  links: Array<object>
  domainType: string
  id: string
  title: string
  members: object
  extensions: ActivationExtensionsResponse
}

// We only really care about the id. The rest is not used in the UI
export interface ActivatePendingChangesResponse {
  links: Array<object>
  domainType: string
  id: string
  title: string
  members: object
  extensions: object
}

// Site information as returned by the ajax call
// The lastActivationStatus is provided by the backend from persisted state
export interface Site {
  siteId: string
  siteName: string
  onlineStatus: string
  changes: number
  version: string
  loggedIn: boolean
  lastActivationStatus: StatusPerSiteResponse | undefined
}

export interface PendingChanges {
  changeId: string
  changeText: string
  user: string
  time: number
  whichSites: Array<string>
  timestring?: string
}

export interface SitesAndChanges {
  sites: Array<Site>
  pendingChanges: Array<PendingChanges>
}
