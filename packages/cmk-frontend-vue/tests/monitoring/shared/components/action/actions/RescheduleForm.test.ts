/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { computed } from 'vue'

import RescheduleForm, {
  type RescheduleValues
} from '@/monitoring/shared/components/action/actions/RescheduleForm.vue'
import { ACTION_TARGET_COUNT } from '@/monitoring/shared/components/action/types'

function mountForm(overrides: Partial<RescheduleValues> = {}, targetCount = 1) {
  const modelValue: RescheduleValues = { spreadMinutes: 5, ...overrides }
  return render(RescheduleForm, {
    props: { modelValue },
    global: { provide: { [ACTION_TARGET_COUNT as symbol]: computed(() => targetCount) } }
  })
}

test('reports valid for a non-negative spread', () => {
  const { emitted } = mountForm()

  expect(emitted('update:valid')?.at(-1)).toEqual([true])
})

test('reports invalid when no spread is entered', () => {
  const { emitted } = mountForm({ spreadMinutes: undefined })

  expect(emitted('update:valid')?.at(-1)).toEqual([false])
})

test('renders the spread-over input', () => {
  mountForm()

  expect(screen.getByText('Spread over')).toBeInTheDocument()
})

test('warns about the load only when more than one check is rescheduled', () => {
  const { unmount } = mountForm({}, 1)
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  unmount()

  mountForm({}, 7)
  expect(screen.getByRole('alert')).toHaveTextContent('Rescheduling 7 checks at once')
})
