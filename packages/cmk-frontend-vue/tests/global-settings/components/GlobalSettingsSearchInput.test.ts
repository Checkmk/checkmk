/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'
import { h, ref } from 'vue'

import GlobalSettingsSearchInput from '@/global-settings/components/GlobalSettingsSearchInput.vue'

// A parent that actually feeds the model back, as v-model does.
function setup() {
  const query = ref('')
  const user = userEvent.setup()
  render({
    setup: () => () =>
      h(GlobalSettingsSearchInput, {
        placeholder: 'Search settings…',
        modelValue: query.value,
        'onUpdate:modelValue': (value: string) => (query.value = value)
      })
  })
  return { user, query }
}

test('the model follows every keystroke', async () => {
  const { user, query } = setup()

  await user.type(screen.getByRole('searchbox'), 'idle')

  expect(query.value).toBe('idle')
})

test('the magnifier gives way to the clear button once there is a query', async () => {
  const { user } = setup()
  expect(screen.queryByRole('button', { name: 'Clear search' })).not.toBeInTheDocument()

  await user.type(screen.getByRole('searchbox'), 'idle')

  expect(screen.getByRole('button', { name: 'Clear search' })).toBeInTheDocument()
})

test('clearing empties the query', async () => {
  const { user, query } = setup()
  await user.type(screen.getByRole('searchbox'), 'idle')

  await user.click(screen.getByRole('button', { name: 'Clear search' }))

  expect(query.value).toBe('')
  expect(screen.queryByRole('button', { name: 'Clear search' })).not.toBeInTheDocument()
})
