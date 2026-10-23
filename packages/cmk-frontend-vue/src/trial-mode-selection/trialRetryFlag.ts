/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/*
 * The site checks whether it can reach the verification domain only while it renders the
 * page, so Retry reloads it. This flag makes the reloaded page open on the trial's first
 * step instead of the choice.
 */

/*
 * The flag is only consumed when the dialog renders. A reload that ends up elsewhere -
 * the site was decided meanwhile, or the session expired - leaves it behind, and it must
 * not take over a visit long after.
 */
const MAX_AGE_MS = 60_000

/*
 * Checkmk sites on the same host share one origin, and with it the storage. The page
 * path tells them apart.
 */
function storageKey(): string {
  return `trialModeSelectionRetry:${window.location.pathname}`
}

export function storeTrialRetryFlag(): void {
  try {
    sessionStorage.setItem(storageKey(), String(Date.now()))
  } catch {
    // Privacy settings can block the storage. The reload then shows the choice.
  }
}

/* Whether the page was reloaded by Retry. */
export function consumeTrialRetryFlag(): boolean {
  try {
    const key = storageKey()
    // A missing flag reads as 0, which results as expired.
    const retriedAt = Number(sessionStorage.getItem(key))
    sessionStorage.removeItem(key)
    return Date.now() - retriedAt < MAX_AGE_MS
  } catch {
    return false
  }
}
