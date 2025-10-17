/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from '@/lib/api-client'

export interface EALink {
  domainType: string
  rel: string
  href: string
  method: string
  type: string
}

export interface EffectiveAttributes {
  links: EALink[]
  id: string
  domainType: string
  value: []
}
export class CseOnboardingApiClient extends Api {
  public getAgentSecret(): Promise<{ secret: string }> {
    return this.get('objects/onboarding/agent') as Promise<{ secret: string }> // TODO BKP: test if this works
  }
}
