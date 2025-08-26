/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

export interface WizardContext {
  mode: () => 'overview' | 'guided'
  isSelected: (index: number) => boolean
  navigation: WizardNavigation
}

export interface WizardNavigation {
  next: () => void
  prev: () => void
  goto: (index: number) => void
}

export const wizardContextProvider = Symbol() as InjectionKey<WizardContext>

export function provideWizardContext(context: WizardContext): void {
  provide(wizardContextProvider, context)
}

export function getWizardContext(): WizardContext {
  const context = inject(wizardContextProvider)
  if (context === undefined) {
    throw Error('can only be used inside a CmkWizard')
  }
  return context
}
