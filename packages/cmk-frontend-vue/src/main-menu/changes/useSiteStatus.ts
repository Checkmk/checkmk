/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import type { PendingChanges, Site } from '@/main-menu/changes/ChangesInterfaces'

export function useSiteStatus(
  sites: Ref<Site[]>,
  pendingChanges: Ref<PendingChanges[]>,
  userCanActivateForeign: Ref<boolean>
) {
  function siteHasChanges(site: Site): boolean {
    return site.changes > 0
  }

  function siteHasStatusProblems(site: Site): boolean {
    return !['online', 'disabled'].includes(site.onlineStatus)
  }

  function siteHasActivationIssues(site: Site): boolean {
    return (
      !!site.lastActivationStatus && ['error', 'warning'].includes(site.lastActivationStatus.state)
    )
  }

  function siteHasErrors(site: Site): boolean {
    return siteHasActivationIssues(site) || siteHasStatusProblems(site)
  }

  function siteIsLoggedOut(site: Site): boolean {
    return site.loggedIn === false
  }

  function siteHasForeignChanges(site: Site): boolean {
    return pendingChanges.value.some(
      (change) =>
        (change.whichSites.includes(site.siteId) || change.whichSites.includes('All sites')) &&
        change.foreignChange
    )
  }

  function siteHasForeignChangesWithoutPermission(site: Site): boolean {
    return siteHasForeignChanges(site) && !userCanActivateForeign.value
  }

  function siteSelectionIsDisabled(site: Site): boolean {
    return (
      siteHasStatusProblems(site) ||
      siteIsLoggedOut(site) ||
      siteHasForeignChangesWithoutPermission(site)
    )
  }

  const allSitesWithChangesAreNotSelectable = computed((): boolean => {
    const sitesWithChanges = sites.value.filter((site) => site.changes > 0)
    if (sitesWithChanges.length === 0) {
      return false
    }
    return sitesWithChanges.every((site) => siteSelectionIsDisabled(site))
  })
  const sitesWithChanges = computed(() => sites.value.filter(siteHasChanges))

  const sitesWithErrors = computed(() => sites.value.filter(siteHasErrors))

  const loggedOutSites = computed(() => sites.value.filter(siteIsLoggedOut))

  const hasSitesWithChanges = computed(() => sitesWithChanges.value.length > 0)

  const hasSitesWithErrors = computed(() => sitesWithErrors.value.length > 0)

  const hasLoggedOutSites = computed(() => loggedOutSites.value.length > 0)

  const hasSitesWithChangesOrErrors = computed(
    () => hasSitesWithChanges.value || hasSitesWithErrors.value
  )

  return {
    siteHasChanges,
    siteHasStatusProblems,
    siteHasActivationIssues,
    siteHasErrors,
    siteIsLoggedOut,
    siteHasForeignChangesWithoutPermission,
    siteSelectionIsDisabled,
    allSitesWithChangesAreNotSelectable,

    sitesWithChanges,
    sitesWithErrors,
    loggedOutSites,

    hasSitesWithChanges,
    hasSitesWithErrors,
    hasSitesWithChangesOrErrors,
    hasLoggedOutSites
  }
}
