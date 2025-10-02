/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import type { Site } from '@/main-menu/changes/ChangesInterfaces'

export function useSiteStatus(sites: Ref<Site[]>) {
  function siteHasChanges(site: Site): boolean {
    return site.changes > 0
  }

  function siteHasErrors(site: Site): boolean {
    return (
      (site.lastActivationStatus &&
        ['error', 'warning'].includes(site.lastActivationStatus.state)) ||
      site.onlineStatus !== 'online'
    )
  }

  const sitesWithChanges = computed(() => sites.value.filter(siteHasChanges))

  const sitesWithErrors = computed(() => sites.value.filter(siteHasErrors))

  const hasSitesWithChanges = computed(() => sitesWithChanges.value.length > 0)

  const hasSitesWithErrors = computed(() => sitesWithErrors.value.length > 0)

  const hasSitesWithChangesOrErrors = computed(
    () => hasSitesWithChanges.value || hasSitesWithErrors.value
  )

  return {
    siteHasChanges,
    siteHasErrors,

    sitesWithChanges,
    sitesWithErrors,

    hasSitesWithChanges,
    hasSitesWithErrors,
    hasSitesWithChangesOrErrors
  }
}
