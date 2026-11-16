/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import WidgetActionAlert from '@/dashboard/components/WidgetActionAlert.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { useActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'

const WAITING = untranslated('Waiting for the check of heute to finish')

function renderAlert() {
  const stack = useActionFeedbackStack()
  const rendered = render(WidgetActionAlert, { props: { stack } })
  return { ...rendered, stack }
}

function renderOutcome(outcome: ActionOutcome) {
  const rendered = renderAlert()
  rendered.stack.show(outcome)
  return rendered
}

/** An action that runs until the end of the test. */
const runningAction = () => new Promise<ActionOutcome>(() => {})

describe('WidgetActionAlert', () => {
  it('tells how an action in a widget went', async () => {
    renderOutcome({ variant: 'success', message: untranslated('The rescheduled check has run') })

    expect(await screen.findByRole('status')).toHaveTextContent('The rescheduled check has run')
  })

  it('closes a warning on request, leaving no empty space behind', async () => {
    const { container } = renderOutcome({
      variant: 'warning',
      message: untranslated('The check did not finish within 10 seconds.')
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Close' }))

    expect(container).toBeEmptyDOMElement()
  })

  it('tells of a failed action as an alert', async () => {
    renderOutcome({
      variant: 'error',
      heading: untranslated('Could not reschedule the checks for the selected hosts'),
      message: untranslated('Retry the command.')
    })

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reschedule the checks for the selected hosts'
    )
  })

  it('tells that an action in a widget still runs', async () => {
    const { stack } = renderAlert()

    void stack.track({ pending: WAITING, perform: runningAction })

    expect(await screen.findByRole('status')).toHaveTextContent(WAITING)
  })

  it('tells of each action still running in an alert of its own', async () => {
    const { stack } = renderAlert()

    void stack.track({ pending: WAITING, perform: runningAction })
    void stack.track({ pending: WAITING, perform: runningAction })

    expect(await screen.findAllByRole('status')).toHaveLength(2)
  })
})
