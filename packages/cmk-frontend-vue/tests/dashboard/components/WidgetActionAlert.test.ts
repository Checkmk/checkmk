/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import WidgetActionAlert from '@/dashboard/components/WidgetActionAlert.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'

function renderAlert(outcome: ActionOutcome) {
  return render(
    defineComponent({
      setup() {
        const open = ref(true)
        return () =>
          h(WidgetActionAlert, {
            outcome,
            open: open.value,
            'onUpdate:open': (value: boolean) => (open.value = value)
          })
      }
    })
  )
}

describe('WidgetActionAlert', () => {
  it('tells how an action in a widget went', () => {
    renderAlert({ variant: 'success', message: untranslated('The rescheduled check has run') })

    expect(screen.getByRole('status')).toHaveTextContent('The rescheduled check has run')
  })

  it('closes a warning on request, leaving no empty space behind', async () => {
    const { container } = renderAlert({
      variant: 'warning',
      message: untranslated('The check did not run within 10 seconds.')
    })

    await userEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(container).toBeEmptyDOMElement()
  })

  it('tells of a failed action as an alert', () => {
    renderAlert({
      variant: 'error',
      heading: untranslated('Could not reschedule the checks for the selected hosts'),
      message: untranslated('Retry the command.')
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Could not reschedule the checks for the selected hosts'
    )
  })
})
