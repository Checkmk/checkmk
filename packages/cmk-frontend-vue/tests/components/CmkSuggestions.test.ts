/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { h } from 'vue'

import CmkSuggestions, {
  NoSelection,
  Response,
  type Section,
  SelectionWithTitle,
  type Suggestion,
  type Suggestions
} from '@/components/CmkSuggestions'

const flatSuggestions: Suggestion[] = [
  { name: 'option1', title: 'Option One' },
  { name: 'option2', title: 'Option Two' },
  { name: 'option3', title: 'Option Three' }
]

const twoSections: Section[] = [
  {
    title: 'Section A',
    suggestions: [
      { name: 'a1', title: 'Alpha One' },
      { name: 'a2', title: 'Alpha Two' }
    ]
  },
  {
    title: 'Section B',
    suggestions: [
      { name: 'b1', title: 'Beta One' },
      { name: 'b2', title: 'Beta Two' }
    ]
  }
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

test.each([
  {
    name: 'flat empty list',
    suggestions: { type: 'fixed', suggestions: [] as Suggestion[] } as Suggestions,
    filter: undefined as string | undefined
  },
  {
    name: 'filtered sectioned list with no matches',
    suggestions: { type: 'filtered', suggestions: twoSections } as Suggestions,
    filter: 'zzz'
  }
])(
  'shows noResultsHint and no options or headings when empty: $name',
  async ({ suggestions, filter }) => {
    const user = userEvent.setup()
    render(CmkSuggestions, {
      props: {
        selectedSuggestion: new NoSelection(),
        suggestions,
        role: 'option',
        noResultsHint: 'No matches'
      }
    })

    if (filter !== undefined) {
      await user.type(screen.getByLabelText('filter'), filter)
    }

    // The hint is rendered as a plain <li> with no role or accessible name,
    // so visible text is the only signal available for this assertion.
    await screen.findByText('No matches')
    expect(screen.queryByRole('option')).toBeNull()
    expect(screen.queryByRole('heading')).toBeNull()
  }
)

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
  // The matched substring is wrapped in <mark> (the highlight has no ARIA representation, so the
  // semantic element is what we assert); the full title text stays intact around it.
  expect(option.querySelector('mark')?.textContent).toBe(match)
  expect(option.textContent).toBe(`${before}${match}${after}`)
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

test('renders sticky headers and items when more than one section is present', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: twoSections },
      role: 'option'
    }
  })

  const headerA = await screen.findByRole('heading', { name: 'Section A' })
  await screen.findByRole('heading', { name: 'Section B' })
  expect(headerA).toHaveClass('cmk-suggestions__section-header')

  expect(screen.getAllByRole('option')).toHaveLength(4)
  await screen.findByRole('option', { name: 'Alpha One' })
  await screen.findByRole('option', { name: 'Alpha Two' })
  await screen.findByRole('option', { name: 'Beta One' })
  await screen.findByRole('option', { name: 'Beta Two' })
})

test('renders an empty-title section header-less and flush-left before titled sections', async () => {
  const sections: Section[] = [
    { title: '', suggestions: [{ name: 'user-entry', title: 'user-entry' }] },
    ...twoSections
  ]
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: sections },
      role: 'option'
    }
  })

  const userEntry = await screen.findByRole('option', { name: 'user-entry' })
  // The empty-title section emits no header, while the titled sections keep theirs.
  const headerA = await screen.findByRole('heading', { name: 'Section A' })
  await screen.findByRole('heading', { name: 'Section B' })
  expect(screen.getAllByRole('heading')).toHaveLength(2)

  // The section-less item renders first, ahead of the section headers.
  expect(screen.getAllByRole('option')[0]).toBe(userEntry)
  expect(userEntry.compareDocumentPosition(headerA) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

  // No indentation
  expect(userEntry).toHaveClass('selectable')
  expect(userEntry).not.toHaveClass('cmk-suggestions__item--in-section')
  expect(screen.getByRole('option', { name: 'Alpha One' })).toHaveClass(
    'cmk-suggestions__item--in-section'
  )
})

test('omits headers when only one section is present', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'fixed',
        suggestions: [{ title: 'Only', suggestions: twoSections[0]!.suggestions }]
      },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'Alpha One' })
  expect(screen.queryByRole('heading', { name: 'Only' })).toBeNull()
  expect(screen.queryByRole('heading')).toBeNull()
})

test('drops sections whose items are all filtered out, including their header', async () => {
  const user = userEvent.setup()
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'filtered', suggestions: twoSections },
      role: 'option'
    }
  })

  await screen.findByRole('heading', { name: 'Section A' })

  await user.type(screen.getByLabelText('filter'), 'Beta')

  await screen.findByRole('option', { name: 'Beta One' })
  // Only Section B survives; with a single surviving section, headers are
  // omitted entirely.
  expect(screen.queryByRole('heading')).toBeNull()
  expect(screen.queryByRole('option', { name: 'Alpha One' })).toBeNull()
  expect(screen.queryByRole('option', { name: 'Alpha Two' })).toBeNull()
})

test('callback-filtered renders sectioned response with headers when more than one section', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'callback-filtered',
        querySuggestions: async () => new Response(twoSections)
      },
      role: 'option'
    }
  })

  await screen.findByRole('heading', { name: 'Section A' })
  await screen.findByRole('heading', { name: 'Section B' })
  expect(screen.getAllByRole('option')).toHaveLength(4)
  await screen.findByRole('option', { name: 'Alpha One' })
  await screen.findByRole('option', { name: 'Beta Two' })
})

test('callback-filtered omits header when sectioned response has a single section', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: {
        type: 'callback-filtered',
        querySuggestions: async () =>
          new Response([{ title: 'Only', suggestions: twoSections[0]!.suggestions }])
      },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'Alpha One' })
  expect(screen.queryByRole('heading', { name: 'Only' })).toBeNull()
  expect(screen.queryByRole('heading')).toBeNull()
})

test('keyboard navigation skips headers and clicking a header does not select', async () => {
  const user = userEvent.setup()
  const { emitted } = render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: twoSections },
      role: 'option'
    }
  })

  await screen.findByRole('option', { name: 'Alpha One' })

  await user.click(screen.getByRole('heading', { name: 'Section A' }))
  expect(emitted('select-suggestion')).toBeUndefined()

  await user.click(screen.getByRole('option', { name: 'Beta One' }))
  expect(emitted('select-suggestion')).toBeTruthy()
  expect(emitted('select-suggestion')![0]).toEqual([{ name: 'b1', title: 'Beta One' }])
})

test('markSelected renders a checkmark only on the selected option', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new SelectionWithTitle('option2', 'Option Two'),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option',
      markSelected: true
    }
  })

  const selectedRow = await screen.findByRole('option', { name: 'Option Two' })
  expect(selectedRow.querySelector('.cmk-suggestions__selected-mark')).not.toBeNull()
  expect(selectedRow).toHaveAttribute('aria-selected', 'true')

  const otherRow = screen.getByRole('option', { name: 'Option One' })
  expect(otherRow.querySelector('.cmk-suggestions__selected-mark')).toBeNull()
  expect(otherRow).toHaveAttribute('aria-selected', 'false')
})

test('markSelected defaults to off so no checkmark is rendered', async () => {
  const { container } = render(CmkSuggestions, {
    props: {
      selectedSuggestion: new SelectionWithTitle('option2', 'Option Two'),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option'
    }
  })

  const selectedRow = await screen.findByRole('option', { name: 'Option Two' })
  expect(container.querySelectorAll('.cmk-suggestions__selected-mark')).toHaveLength(0)
  expect(selectedRow).not.toHaveAttribute('aria-selected')
})

test('option slot customizes the rendered option content', async () => {
  render(CmkSuggestions, {
    props: {
      selectedSuggestion: new NoSelection(),
      suggestions: { type: 'fixed', suggestions: flatSuggestions },
      role: 'option'
    },
    slots: {
      option: (props: { suggestion: Suggestion }) =>
        h('span', { class: 'custom-option' }, `[[${props.suggestion.title}]]`)
    }
  })

  const row = await screen.findByRole('option', { name: 'Option One' })
  expect(row.querySelector('.custom-option')?.textContent).toBe('[[Option One]]')
})
