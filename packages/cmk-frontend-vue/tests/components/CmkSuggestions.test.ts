/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import CmkSuggestions, {
  NoSelection,
  SelectionWithTitle,
  type Suggestion
} from '@/components/CmkSuggestions'

const flatSuggestions: Suggestion[] = [
  { name: 'option1', title: 'Option One' },
  { name: 'option2', title: 'Option Two' },
  { name: 'option3', title: 'Option Three' }
]

test('renders a flat fixed suggestion list', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option'
    }
  })

  expect(await screen.findAllByRole('option')).toHaveLength(3)
  await screen.findByRole('option', { name: 'Option One' })
  await screen.findByRole('option', { name: 'Option Two' })
  await screen.findByRole('option', { name: 'Option Three' })
})

test('clicking a suggestion emits select-suggestion with that item', async () => {
  const user = userEvent.setup()
  const { emitted } = render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option'
    }
  })

  await user.click(await screen.findByRole('option', { name: 'Option Two' }))

  expect(emitted('select-suggestion')).toBeTruthy()
  expect(emitted('select-suggestion')![0]).toEqual([{ name: 'option2', title: 'Option Two' }])
})

test('shows noResultsHint when the suggestion list is empty', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: [] as Suggestion[] },
      role: 'option',
      noResultsHint: 'No matches'
    }
  })

  // The hint is rendered as a plain <li> with no role or accessible name,
  // so visible text is the only signal available for this assertion.
  await screen.findByText('No matches')
  expect(screen.queryByRole('option')).toBeNull()
})

test('filtered mode narrows visible options when typing into the filter', async () => {
  const user = userEvent.setup()
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'filtered', suggestions: flatSuggestions },
      role: 'option'
    }
  })

  expect(await screen.findAllByRole('option')).toHaveLength(3)

  await user.type(screen.getByLabelText('filter'), 'Two')

  expect(await screen.findAllByRole('option')).toHaveLength(1)
  await screen.findByRole('option', { name: 'Option Two' })
  expect(screen.queryByRole('option', { name: 'Option One' })).toBeNull()
  expect(screen.queryByRole('option', { name: 'Option Three' })).toBeNull()
})

test('marks the matching item as selected when selectedSuggestion is provided', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new SelectionWithTitle('option2', 'Option Two'),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option'
    }
  })

  expect(await screen.findByRole('option', { name: 'Option Two' })).toHaveClass('selected')
  expect(screen.getByRole('option', { name: 'Option One' })).not.toHaveClass('selected')
  expect(screen.getByRole('option', { name: 'Option Three' })).not.toHaveClass('selected')
})
