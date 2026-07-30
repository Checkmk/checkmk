/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { InjectionKey } from 'vue'

/** Opens the network flow host detail slide-in for the given IP address. */
export type OpenHostSlideIn = (ip: string) => void
export const hostSlideInKey: InjectionKey<OpenHostSlideIn> = Symbol('networkFlowHostSlideIn')

/** Opens the network flow autonomous system detail slide-in for the given ASN. */
export type OpenAutonomousSystemSlideIn = (asn: number) => void
export const autonomousSystemSlideInKey: InjectionKey<OpenAutonomousSystemSlideIn> = Symbol(
  'networkFlowAutonomousSystemSlideIn'
)
