/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { InjectionKey } from 'vue'

import type { NetworkFlowDonutContent, VisualContext } from '@/dashboard/types/widget'

/** Opens the network flow host detail slide-in for the given IP address. */
export type OpenHostSlideIn = (ip: string) => void
export const hostSlideInKey: InjectionKey<OpenHostSlideIn> = Symbol('networkFlowHostSlideIn')

/** Opens the network flow autonomous system detail slide-in for the given ASN. */
export type OpenAutonomousSystemSlideIn = (asn: number) => void
export const autonomousSystemSlideInKey: InjectionKey<OpenAutonomousSystemSlideIn> = Symbol(
  'networkFlowAutonomousSystemSlideIn'
)

/**
 * What the donut's aggregated "Other" slice was drawn from: the widget's own
 * configuration and filters, since the limit decides which categories are behind
 * the slice and the filters decide what its total is, plus the window the ring's
 * numbers came from so the breakdown covers the same traffic.
 */
export interface DonutOtherBreakdownTarget {
  content: NetworkFlowDonutContent
  context: VisualContext
  window: { start: number; end: number }
}

/** Opens the breakdown of a donut widget's aggregated "Other" slice. */
export type OpenDonutOtherBreakdownSlideIn = (target: DonutOtherBreakdownTarget) => void
export const donutOtherBreakdownSlideInKey: InjectionKey<OpenDonutOtherBreakdownSlideIn> = Symbol(
  'networkFlowDonutOtherBreakdownSlideIn'
)
