/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, nextTick, provide, ref } from 'vue'

import {
  type OpenAutonomousSystemSlideIn,
  type OpenHostSlideIn,
  autonomousSystemSlideInKey,
  hostSlideInKey
} from './injectionKeys'

export interface NetworkFlowSlideIns {
  hostIp: Ref<string | null>
  hostOpen: ComputedRef<boolean>
  closeHost: () => void
  autonomousSystemAsn: Ref<number | null>
  autonomousSystemOpen: ComputedRef<boolean>
  closeAutonomousSystem: () => void
}

/**
 * Owns the network flow detail slide-ins and provides the openers, so anything
 * nested below - a dashboard widget or a table cell - can open one without
 * knowing where the panel is rendered.
 *
 * Switching target while a panel is open closes and reopens it on the next tick:
 * the panel loads its data once on mount, so it has to remount to reload.
 */
export function useNetworkFlowSlideIns(): NetworkFlowSlideIns {
  const hostIp = ref<string | null>(null)
  const autonomousSystemAsn = ref<number | null>(null)

  const openHost: OpenHostSlideIn = (ip) => {
    if (hostIp.value !== null && hostIp.value !== ip) {
      hostIp.value = null
      void nextTick(() => {
        hostIp.value = ip
      })
    } else {
      hostIp.value = ip
    }
  }

  const openAutonomousSystem: OpenAutonomousSystemSlideIn = (asn) => {
    if (autonomousSystemAsn.value !== null && autonomousSystemAsn.value !== asn) {
      autonomousSystemAsn.value = null
      void nextTick(() => {
        autonomousSystemAsn.value = asn
      })
    } else {
      autonomousSystemAsn.value = asn
    }
  }

  provide(hostSlideInKey, openHost)
  provide(autonomousSystemSlideInKey, openAutonomousSystem)

  return {
    hostIp,
    hostOpen: computed(() => hostIp.value !== null),
    closeHost: () => {
      hostIp.value = null
    },
    autonomousSystemAsn,
    autonomousSystemOpen: computed(() => autonomousSystemAsn.value !== null),
    closeAutonomousSystem: () => {
      autonomousSystemAsn.value = null
    }
  }
}
