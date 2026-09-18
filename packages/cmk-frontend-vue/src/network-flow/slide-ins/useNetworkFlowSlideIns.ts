/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, nextTick, provide, ref } from 'vue'

import {
  type DonutOtherBreakdownTarget,
  type OpenAutonomousSystemSlideIn,
  type OpenDonutOtherBreakdownSlideIn,
  type OpenHostSlideIn,
  autonomousSystemSlideInKey,
  donutOtherBreakdownSlideInKey,
  hostSlideInKey
} from './injectionKeys'

type PanelName = 'host' | 'autonomousSystem' | 'donutOther'

export interface NetworkFlowSlideIns {
  hostIp: Ref<string | null>
  hostOpen: ComputedRef<boolean>
  closeHost: () => void
  autonomousSystemAsn: Ref<number | null>
  autonomousSystemOpen: ComputedRef<boolean>
  closeAutonomousSystem: () => void
  donutOtherTarget: Ref<DonutOtherBreakdownTarget | null>
  donutOtherOpen: ComputedRef<boolean>
  closeDonutOther: () => void
}

/**
 * Owns the network flow detail slide-ins and provides the openers, so anything
 * nested below - a dashboard widget or a table cell - can open one without
 * knowing where the panel is rendered.
 *
 * Switching target while a panel is open closes and reopens it on the next tick:
 * the panel loads its data once on mount, so it has to remount to reload.
 *
 * Closing puts the keyboard back where it came from: the panel prevents the
 * dialog library's own restoration and is unmounted on the way out, so focus
 * would otherwise land on the document body.
 */
export function useNetworkFlowSlideIns(): NetworkFlowSlideIns {
  const hostIp = ref<string | null>(null)
  const autonomousSystemAsn = ref<number | null>(null)
  const donutOtherTarget = ref<DonutOtherBreakdownTarget | null>(null)

  // One per panel: nothing traps focus, so a reader can open a second panel from
  // behind the first, and then closing them shares no single "the" trigger.
  // An SVG element counts as one - the donut's arcs are focusable groups.
  const triggers: Record<PanelName, HTMLElement | SVGElement | null> = {
    host: null,
    autonomousSystem: null,
    donutOther: null
  }

  function captureTrigger(panel: PanelName): void {
    const active = document.activeElement
    triggers[panel] =
      (active instanceof HTMLElement || active instanceof SVGElement) &&
      active !== document.body &&
      active !== document.documentElement
        ? active
        : null
  }

  function restoreTrigger(panel: PanelName): void {
    const element = triggers[panel]
    // Cleared first, so a second close cannot reach for a stale element.
    triggers[panel] = null
    if (element !== null && element.isConnected) {
      void nextTick(() => element.focus({ preventScroll: true }))
    }
  }

  const openHost: OpenHostSlideIn = (ip) => {
    captureTrigger('host')
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
    captureTrigger('autonomousSystem')
    if (autonomousSystemAsn.value !== null && autonomousSystemAsn.value !== asn) {
      autonomousSystemAsn.value = null
      void nextTick(() => {
        autonomousSystemAsn.value = asn
      })
    } else {
      autonomousSystemAsn.value = asn
    }
  }

  // The target is an object, so reopening always remounts rather than comparing.
  const openDonutOther: OpenDonutOtherBreakdownSlideIn = (target) => {
    captureTrigger('donutOther')
    if (donutOtherTarget.value !== null) {
      donutOtherTarget.value = null
      void nextTick(() => {
        donutOtherTarget.value = target
      })
    } else {
      donutOtherTarget.value = target
    }
  }

  provide(hostSlideInKey, openHost)
  provide(autonomousSystemSlideInKey, openAutonomousSystem)
  provide(donutOtherBreakdownSlideInKey, openDonutOther)

  return {
    hostIp,
    hostOpen: computed(() => hostIp.value !== null),
    closeHost: () => {
      hostIp.value = null
      restoreTrigger('host')
    },
    autonomousSystemAsn,
    autonomousSystemOpen: computed(() => autonomousSystemAsn.value !== null),
    closeAutonomousSystem: () => {
      autonomousSystemAsn.value = null
      restoreTrigger('autonomousSystem')
    },
    donutOtherTarget,
    donutOtherOpen: computed(() => donutOtherTarget.value !== null),
    closeDonutOther: () => {
      donutOtherTarget.value = null
      restoreTrigger('donutOther')
    }
  }
}
