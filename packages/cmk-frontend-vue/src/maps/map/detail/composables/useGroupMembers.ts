/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import type { MapStateCount } from '@/maps/map/components/MapStateCounts.vue'
import { useMapsApis } from '@/maps/services/context'
import type { GroupMember, MapElement } from '@/maps/types/api'
import { groupMembersQuery } from '@/maps/utils/memberFilter'
import { isProblemState } from '@/maps/utils/problemState'
import { stateRank } from '@/maps/utils/stateColors'
import { hostStateCounts, serviceStateCounts } from '@/maps/utils/stateCounts'

interface GroupMembersOptions {
  object: () => MapElement | null
  connectionId: () => string | null | undefined
}

const MEMBER_TRUNCATE = 50

/**
 * Member list for the drawer's Members tab: fetches per-member state for a
 * host-/service-group or dyngroup so the operator can triage without leaving
 * the drawer, and derives the health counts, search/problem filter, sorted +
 * truncated view, and the summary chips.
 */
export function useGroupMembers(options: GroupMembersOptions) {
  const { object, connectionId } = options
  const { objects } = useMapsApis()
  const { _t } = usei18n()

  const groupMembers = ref<GroupMember[]>([])
  const loadingMembers = ref(false)
  const memberSearch = ref('')
  const onlyProblems = ref(false)

  watch(
    [
      () => object()?.type,
      () => object()?.group_name,
      () => object()?.object_filter,
      () => object()?.object_types,
      () => object()?.exclude_members,
      connectionId
    ],
    async ([objType, groupName, objFilter, objTypes, excluded, connId]) => {
      groupMembers.value = []
      memberSearch.value = ''
      onlyProblems.value = false
      if (!connId) {
        return
      }
      const isHostOrServiceGroup = objType === 'hostgroup' || objType === 'servicegroup'
      if (isHostOrServiceGroup && !groupName) {
        return
      }
      if (objType === 'dyngroup' && !objFilter) {
        return
      }
      if (!isHostOrServiceGroup && objType !== 'dyngroup') {
        return
      }
      loadingMembers.value = true
      try {
        let rows: GroupMember[]
        if (objType === 'dyngroup') {
          rows = await objects.fetchDyngroupMembers(objTypes ?? 'host', objFilter ?? '')
        } else if (objType === 'hostgroup' || objType === 'servicegroup') {
          const thinned = excluded ? groupMembersQuery(objType, groupName ?? '', excluded) : null
          rows = thinned
            ? await objects.fetchDyngroupMembers(thinned.objectTypes, thinned.objectFilter)
            : await objects.fetchGroupMembers(objType, groupName ?? '')
        } else {
          return
        }
        // Stale-response guard.
        if (
          object()?.type === objType &&
          object()?.group_name === groupName &&
          object()?.object_filter === objFilter &&
          object()?.exclude_members === excluded
        ) {
          groupMembers.value = rows
        }
      } catch {
        groupMembers.value = []
      } finally {
        loadingMembers.value = false
      }
    },
    { immediate: true }
  )

  const filteredMembers = computed(() => {
    const needle = memberSearch.value.trim().toLowerCase()
    return groupMembers.value
      .filter((m) => {
        if (onlyProblems.value && !isProblemState(m.state)) {
          return false
        }
        if (!needle) {
          return true
        }
        return (
          m.host.toLowerCase().includes(needle) ||
          m.service.toLowerCase().includes(needle) ||
          m.output.toLowerCase().includes(needle)
        )
      })
      .sort(
        (a, b) =>
          stateRank(b.state) - stateRank(a.state) ||
          a.host.localeCompare(b.host) ||
          a.service.localeCompare(b.service)
      )
  })

  const visibleMembers = computed(() => filteredMembers.value.slice(0, MEMBER_TRUNCATE))
  const truncatedMemberCount = computed(() =>
    Math.max(0, filteredMembers.value.length - MEMBER_TRUNCATE)
  )

  const isGroup = computed(() => {
    const t = object()?.type
    return t === 'hostgroup' || t === 'servicegroup' || t === 'dyngroup'
  })

  // A host group's members are hosts and are counted as such.
  const memberChips = computed<MapStateCount[]>(() => {
    const counts: Record<string, number> = {}
    for (const member of groupMembers.value) {
      counts[member.state] = (counts[member.state] ?? 0) + 1
    }
    return groupMembers.value.every((member) => !member.service)
      ? hostStateCounts(_t, counts)
      : serviceStateCounts(_t, counts)
  })

  function memberStateTone(state: string): string {
    if (state === 'CRITICAL' || state === 'DOWN') {
      return 'crit'
    }
    if (state === 'WARNING') {
      return 'warn'
    }
    if (state === 'UNKNOWN' || state === 'UNREACHABLE') {
      return 'unknown'
    }
    if (state === 'PENDING') {
      return 'pending'
    }
    return 'ok'
  }

  function memberStateBadge(state: string): string {
    switch (state) {
      case 'CRITICAL':
      case 'DOWN':
        return state === 'DOWN' ? 'D' : 'C'
      case 'WARNING':
        return 'W'
      case 'UNKNOWN':
        return '?'
      case 'UNREACHABLE':
        return 'U'
      case 'PENDING':
        return '·'
      case 'OK':
      case 'UP':
        return '✓'
      default:
        return '·'
    }
  }

  return {
    groupMembers,
    loadingMembers,
    memberSearch,
    onlyProblems,
    filteredMembers,
    visibleMembers,
    truncatedMemberCount,
    memberChips,
    memberStateTone,
    memberStateBadge,
    isGroup
  }
}
