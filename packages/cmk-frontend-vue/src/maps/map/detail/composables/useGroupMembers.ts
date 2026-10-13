/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref, watch } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import type { GroupMember, MapElement } from '@/maps/types/api'

interface MemberChip {
  label: string
  count: number
  tone: 'crit' | 'warn' | 'unknown' | 'ok'
}

interface GroupMembersOptions {
  object: () => MapElement | null
  connectionId: () => string | null | undefined
}

// Severity rank for sort: worst first. Matches the radar view's intent so the
// member list and the donut counts agree.
const _MEMBER_SEVERITY: Record<string, number> = {
  DOWN: 5,
  CRITICAL: 5,
  UNREACHABLE: 4,
  WARNING: 3,
  UNKNOWN: 3,
  PENDING: 1,
  UP: 0,
  OK: 0
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
      connectionId
    ],
    async ([objType, groupName, objFilter, objTypes, connId]) => {
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
        const rows =
          objType === 'dyngroup'
            ? await objects.fetchDyngroupMembers(objTypes ?? 'host', objFilter ?? '')
            : await objects.fetchGroupMembers(
                objType as 'hostgroup' | 'servicegroup',
                groupName ?? ''
              )
        // Stale-response guard.
        if (
          object()?.type === objType &&
          object()?.group_name === groupName &&
          object()?.object_filter === objFilter
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

  const memberHealth = computed(() => {
    const counts = { ok: 0, warn: 0, crit: 0, unkn: 0, pending: 0 }
    for (const m of groupMembers.value) {
      if (m.state === 'OK' || m.state === 'UP') {
        counts.ok += 1
      } else if (m.state === 'WARNING') {
        counts.warn += 1
      } else if (m.state === 'CRITICAL' || m.state === 'DOWN') {
        counts.crit += 1
      } else if (m.state === 'UNKNOWN' || m.state === 'UNREACHABLE') {
        counts.unkn += 1
      } else {
        counts.pending += 1
      }
    }
    return counts
  })

  const filteredMembers = computed(() => {
    const needle = memberSearch.value.trim().toLowerCase()
    return groupMembers.value
      .filter((m) => {
        if (onlyProblems.value && (m.state === 'OK' || m.state === 'UP')) {
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
      .sort((a, b) => {
        const sa = _MEMBER_SEVERITY[a.state] ?? 0
        const sb = _MEMBER_SEVERITY[b.state] ?? 0
        if (sa !== sb) {
          return sb - sa
        }
        return a.host.localeCompare(b.host) || a.service.localeCompare(b.service)
      })
  })

  const visibleMembers = computed(() => filteredMembers.value.slice(0, MEMBER_TRUNCATE))
  const truncatedMemberCount = computed(() =>
    Math.max(0, filteredMembers.value.length - MEMBER_TRUNCATE)
  )

  const isGroup = computed(() => {
    const t = object()?.type
    return t === 'hostgroup' || t === 'servicegroup' || t === 'dyngroup'
  })

  const memberChips = computed<MemberChip[]>(() => {
    const h = memberHealth.value
    const chips: MemberChip[] = []
    if (h.crit > 0) {
      chips.push({ label: 'CRIT', count: h.crit, tone: 'crit' })
    }
    if (h.warn > 0) {
      chips.push({ label: 'WARN', count: h.warn, tone: 'warn' })
    }
    if (h.unkn > 0) {
      chips.push({ label: 'UNKN', count: h.unkn, tone: 'unknown' })
    }
    chips.push({ label: 'OK', count: h.ok, tone: 'ok' })
    return chips
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
