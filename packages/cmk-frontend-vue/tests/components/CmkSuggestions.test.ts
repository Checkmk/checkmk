/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'

import CmkSuggestions, {
  NoSelection,
  Response,
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

async function typeFilter(value: string): Promise<void> {
  const input = screen.getByRole('textbox', { name: 'filter' })
  await fireEvent.update(input, value)
}

function assertSplit(option: HTMLElement, before: string, match: string, after: string): void {
  const children = Array.from(option.children) as HTMLElement[]
  expect(children.map((c) => c.tagName)).toEqual(['SPAN', 'MARK', 'SPAN'])
  expect(children[0]!.textContent).toBe(before)
  expect(children[1]!.textContent).toBe(match)
  expect(children[2]!.textContent).toBe(after)
}

test('filtered mode + matching query wraps title in <mark>', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'filtered',
        suggestions: [{ name: 'foobar', title: 'foobar' }]
      },
      role: 'option'
    }
  })

  await typeFilter('oob')

  const option = await screen.findByRole('option', { name: 'foobar' })
  await waitFor(() => expect(option.querySelector('mark')).not.toBeNull())
  assertSplit(option, 'f', 'oob', 'ar')
})

test('filtered mode + case-insensitive match preserves original casing inside <mark>', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'filtered',
        suggestions: [{ name: 'foobar', title: 'FooBar' }]
      },
      role: 'option'
    }
  })

  await typeFilter('foo')

  const option = await screen.findByRole('option', { name: 'FooBar' })
  await waitFor(() => expect(option.querySelector('mark')).not.toBeNull())
  assertSplit(option, '', 'Foo', 'Bar')
  expect(option.textContent).toBe('FooBar')
})

test('callback-filtered mode: query matched only on name surfaces highlighted name suffix', async () => {
  // Simulates a backend like _matches_id_or_title in cmk/gui/watolib/_autocompleters.py
  // returning a row because the query matched the internal name, while the title is unrelated.
  // "Checkmk Agent" does not contain the substring "cmk" — only the internal name does.
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'callback-filtered',
        querySuggestions: async (_query: string) =>
          new Response([{ name: 'cmk_agent', title: 'Checkmk Agent' }])
      },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'Checkmk Agent' })

  await typeFilter('cmk')

  const option = await screen.findByRole('option', { name: 'Checkmk Agent' })

  await waitFor(() => expect(option.querySelector('.cmk-suggestions__name-match')).not.toBeNull())

  const nameMatch = option.querySelector('.cmk-suggestions__name-match')!
  expect(nameMatch.textContent).toBe(' (cmk_agent)')
  const mark = nameMatch.querySelector('mark')!
  expect(mark.textContent).toBe('cmk')

  // Title itself stays plain — no <mark> outside the name-match suffix.
  expect(option.textContent).toBe('Checkmk Agent (cmk_agent)')
  const titleArea = option.cloneNode(true) as HTMLElement
  titleArea.querySelector('.cmk-suggestions__name-match')?.remove()
  expect(titleArea.querySelector('mark')).toBeNull()
})

test('title-match takes precedence over a coincident name-match', async () => {
  // A row whose name and title both contain the query must highlight in the title only;
  // we don't want to render the parenthesised name suffix on top of an already-highlighted title.
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'callback-filtered',
        querySuggestions: async (_query: string) =>
          new Response([{ name: 'cmk_agent', title: 'Checkmk Agent' }])
      },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'Checkmk Agent' })

  await typeFilter('agent')

  const option = await screen.findByRole('option', { name: 'Checkmk Agent' })

  await waitFor(() => expect(option.querySelector('mark')).not.toBeNull())
  expect(option.querySelector('.cmk-suggestions__name-match')).toBeNull()
  expect(option.querySelector('mark')!.textContent).toBe('Agent')
})

test('fixed mode never renders <mark>', async () => {
  const { container } = render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'fixed',
        suggestions: [
          { name: 'one', title: 'one' },
          { name: 'two', title: 'two' }
        ]
      },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'one' })
  await screen.findByRole('option', { name: 'two' })

  expect(container.querySelector('mark')).toBeNull()
  expect(container.querySelector('span.input')?.classList.contains('hidden')).toBe(true)
})
