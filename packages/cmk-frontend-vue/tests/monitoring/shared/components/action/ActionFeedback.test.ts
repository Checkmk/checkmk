/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { expect, test } from 'vitest'

import ActionFeedback from '@/monitoring/shared/components/action/ActionFeedback.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'

function renderFeedback(variant: ActionOutcome['variant']): ReturnType<typeof render> {
  const feedback: ActionOutcome = { variant, message: 'Acknowledged web-1' as TranslatedString }
  return render(ActionFeedback, { props: { feedback, open: true } })
}

test('a success can be dismissed', async () => {
  const { emitted } = renderFeedback('success')

  await userEvent.click(screen.getByRole('button', { name: 'Close' }))

  expect(emitted('update:open')).toEqual([[false]])
})

// It stays until the user acts on it.
test('a failure offers no close button', () => {
  renderFeedback('error')

  expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
})
