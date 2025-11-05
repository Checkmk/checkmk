/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'
import { type InjectionKey, inject } from 'vue'

import type { AiTemplateService } from '@/ai/lib/service/ai-template'

export const aiTemplateKey = Symbol() as InjectionKey<Ref<AiTemplateService | null>>

export function getInjectedAiTemplate(): Ref<AiTemplateService | null> {
  const aiTemplate = inject(aiTemplateKey)
  if (aiTemplate === undefined) {
    throw Error('can only be used inside menu context')
  }
  return aiTemplate
}
