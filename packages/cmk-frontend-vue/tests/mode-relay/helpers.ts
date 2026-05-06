/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { vi } from 'vitest'
import type { Component } from 'vue'

import { type WizardContext, wizardContextProvider } from '@/components/CmkWizard/utils.ts'

/**
 * Mount a step component with a synthetic wizard context.
 *
 * By default the step is active (isSelected returns true) and navigation
 * functions are vi.fn() stubs. Pass contextOverrides to change any value.
 *
 * Returns the testing-library render result plus the live navigation stubs
 * so tests can assert on calls:
 *
 *   const { navigation } = mountWithWizardContext(NameRelay, props)
 *   await fireEvent.click(screen.getByRole('button', { name: /next step/i }))
 *   expect(navigation.next).toHaveBeenCalled()
 */
export function mountWithWizardContext<P extends object>(
  component: Component,
  props: P,
  contextOverrides: Partial<WizardContext> = {}
) {
  const navigation = {
    next: vi.fn<() => void>(),
    prev: vi.fn<() => void>(),
    goto: vi.fn<(index: number) => void>()
  }
  const context: WizardContext = {
    mode: () => 'guided',
    isSelected: () => true,
    navigation,
    ...contextOverrides
  }
  const result = render(component, {
    props,
    global: {
      provide: { [wizardContextProvider as symbol]: context }
    }
  })
  return { ...result, navigation, context }
}
