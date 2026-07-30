/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'

import type { PageStatus } from '../types/page'
import { type NavPage, useNavigation } from './useNavigation'

const dismissedChipsStorageKey = 'ucl-dismissed-status-chips'
const statusChipLifetimeMs = 90 * 24 * 60 * 60 * 1000

function parseDismissedKeys(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry) => typeof entry === 'string') : []
}

function dismissalKey(page: NavPage): string {
  return `${page.path}|${page.status}|${page.statusSince ?? ''}`
}

function isDismissible(page: NavPage): boolean {
  return page.status === 'new' || page.status === 'updated'
}

function hasExpired(page: NavPage): boolean {
  return (
    page.statusSince !== undefined &&
    Date.now() - Date.parse(page.statusSince) > statusChipLifetimeMs
  )
}

export function createPageStatus(pages: NavPage[]) {
  const dismissedKeys = usePersistentRef<string[]>(
    dismissedChipsStorageKey,
    [],
    parseDismissedKeys,
    'local'
  )

  const producedKeys = new Set(pages.filter(isDismissible).map(dismissalKey))
  const currentDismissedKeys = dismissedKeys.value.filter((key) => producedKeys.has(key))
  if (currentDismissedKeys.length !== dismissedKeys.value.length) {
    dismissedKeys.value = currentDismissedKeys
  }

  function visibleStatus(page: NavPage): PageStatus | undefined {
    if (!page.status) {
      return undefined
    }
    if (page.status === 'deprecated') {
      return page.status
    }
    if (hasExpired(page)) {
      return undefined
    }
    return dismissedKeys.value.includes(dismissalKey(page)) ? undefined : page.status
  }

  function dismissStatusForPath(routePath: string): void {
    const page = pages.find((navPage) => navPage.path === routePath)
    if (!page || !isDismissible(page)) {
      return
    }
    const key = dismissalKey(page)
    if (!dismissedKeys.value.includes(key)) {
      dismissedKeys.value = [...dismissedKeys.value, key]
    }
  }

  return {
    visibleStatus,
    dismissStatusForPath
  }
}

let pageStatus: ReturnType<typeof createPageStatus> | undefined

export function usePageStatus() {
  pageStatus ??= createPageStatus(useNavigation().allPages)
  return pageStatus
}
