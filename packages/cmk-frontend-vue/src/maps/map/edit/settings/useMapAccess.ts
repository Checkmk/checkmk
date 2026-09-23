/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { useAuth } from '@/maps/services/context'
import type { MapEnvelope, MapPublic, MapRead } from '@/maps/types/api'

/** Who a map is shared with, as the form offers it. */
export type PublicMode = 'private' | 'all' | 'groups' | 'sites'

export interface MapAccess {
  mode: Ref<PublicMode>
  groups: Ref<string[]>
  sites: Ref<string[]>
  hideInMonitorMenu: Ref<boolean>
  modeOptions: ComputedRef<Suggestions>
  groupChoices: ComputedRef<{ id: string; alias: string }[]>
  siteChoices: ComputedRef<{ id: string; alias: string }[]>
  /** True when this user may not share maps at all. */
  cannotShare: ComputedRef<boolean>
  setMode: (mode: PublicMode) => void
  setHideInMonitorMenu: (hide: boolean) => void
  toggleGroup: (id: string) => void
  toggleSite: (id: string) => void
  /** The envelope to save: the ``public`` value and the Monitor menu choice. */
  desired: () => MapEnvelope
  /** Stable text for dirty-tracking; see ``snapshot`` below. */
  snapshot: () => string
}

export function publicModeOf(value: MapRead['public']): PublicMode {
  if (value === true) {
    return 'all'
  }
  if (Array.isArray(value)) {
    return value[0] === 'sites' ? 'sites' : 'groups'
  }
  return 'private'
}

function listOf(value: MapRead['public'], kind: 'contact_groups' | 'sites'): string[] {
  return Array.isArray(value) && value[0] === kind ? [...value[1]] : []
}

/**
 * Who may see a map: only its owner, everyone, or the members of named contact
 * groups or sites; and whether the Monitor menu links it.
 *
 * This is the visuals visibility model — a map is a Checkmk visual, so it is
 * shared the way a dashboard is rather than through a permission grid of its
 * own. The offered options follow what this user may publish; the server
 * clamps the saved value again regardless.
 */
export function useMapAccess(map: () => MapRead): MapAccess {
  const { _t } = usei18n()
  const auth = useAuth()

  const capabilities = computed(() => auth.capabilities.value)

  const mode = ref<PublicMode>(publicModeOf(map().public))
  const groups = ref<string[]>(listOf(map().public, 'contact_groups'))
  const sites = ref<string[]>(listOf(map().public, 'sites'))
  const hideInMonitorMenu = ref<boolean>(map().hide_in_monitor_menu === true)

  // A map already scoped to sites keeps the option even for a user who could
  // not have chosen it, so an existing value stays visible and editable.
  const isSiteScoped = computed(() => publicModeOf(map().public) === 'sites')

  const modeOptions = computed<Suggestions>(() => {
    const offered = [{ name: 'private', title: _t('Only me') }]
    if (capabilities.value?.publish_all) {
      offered.push({ name: 'all', title: _t('All users') })
    }
    if (capabilities.value?.publish_to_groups) {
      offered.push({ name: 'groups', title: _t('Specific contact groups') })
    }
    if (capabilities.value?.publish_to_sites || isSiteScoped.value) {
      offered.push({ name: 'sites', title: _t('Specific sites') })
    }
    return { type: 'fixed', suggestions: offered }
  })

  // Both lists arrive already scoped by the server: own versus all groups, and
  // the sites this user is authorized for.
  const groupChoices = computed(() => capabilities.value?.all_contact_groups ?? [])
  const siteChoices = computed(() => capabilities.value?.all_sites ?? [])

  const cannotShare = computed(
    () =>
      !capabilities.value?.publish_all &&
      !capabilities.value?.publish_to_groups &&
      !capabilities.value?.publish_to_sites
  )

  function toggle(list: Ref<string[]>, id: string): void {
    const at = list.value.indexOf(id)
    if (at >= 0) {
      list.value.splice(at, 1)
    } else {
      list.value.push(id)
    }
  }

  function desiredPublic(): MapPublic {
    switch (mode.value) {
      case 'all':
        return true
      case 'groups':
        return ['contact_groups', [...groups.value]]
      case 'sites':
        return ['sites', [...sites.value]]
      default:
        return false
    }
  }

  function desired(): MapEnvelope {
    return { public: desiredPublic(), hide_in_monitor_menu: hideInMonitorMenu.value }
  }

  /**
   * Only the list the current mode uses counts, and its order does not: a
   * selection left behind in an inactive mode would otherwise keep the form
   * looking edited with nothing to show for it.
   */
  function snapshot(): string {
    return JSON.stringify({
      mode: mode.value,
      groups: mode.value === 'groups' ? [...groups.value].sort() : [],
      sites: mode.value === 'sites' ? [...sites.value].sort() : [],
      hideInMonitorMenu: hideInMonitorMenu.value
    })
  }

  return {
    mode,
    groups,
    sites,
    hideInMonitorMenu,
    modeOptions,
    setMode: (picked) => {
      mode.value = picked
    },
    setHideInMonitorMenu: (hide) => {
      hideInMonitorMenu.value = hide
    },
    groupChoices,
    siteChoices,
    cannotShare,
    toggleGroup: (id) => toggle(groups, id),
    toggleSite: (id) => toggle(sites, id),
    desired,
    snapshot
  }
}
