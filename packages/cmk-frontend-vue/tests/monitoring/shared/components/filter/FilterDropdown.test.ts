/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, h, nextTick, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'
import FilterDropdown from '@/monitoring/shared/components/filter/FilterDropdown.vue'
import type {
  AutocompleteChoiceFilter,
  CheckboxListFilter,
  ColumnFilterDefinition,
  ColumnFilterValue,
  SortDirection,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'

const definition: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: 'UP' },
    { value: 'DOWN', title: 'DOWN' }
  ]
}

const LABELS = ['cmk/os_family:linux', 'cmk/os_family:windows', 'cmk/site:heute']

const labelsDefinition: AutocompleteChoiceFilter<'labels'> = {
  type: 'autocomplete-choice',
  field: 'labels',
  op: 'all_of',
  suggest: (query: string) => Promise.resolve(LABELS.filter((label) => label.includes(query)))
}

const nameDefinition: StringInputFilter<'name'> = {
  type: 'string-input',
  field: 'name'
}

function upFilter(): ColumnFilterNode<'state'> {
  return { type: 'condition', field: 'state', op: 'one_of', value: ['UP'] }
}

// Wrapper holding the committed model so we can observe what the dropdown
// commits, and supplying the trigger slot the shell expects.
function renderDropdown(
  initial: ColumnFilterNode<FilterField> | undefined = undefined,
  sortable: boolean = false,
  extendsSortOf: string[] = [],
  filterDefinition: ColumnFilterDefinition = definition,
  label: string = 'State'
) {
  const model = ref<ColumnFilterNode<FilterField> | undefined>(initial)
  const sort = ref<SortDirection>(false)
  const extendedSort = ref<SortDirection>(false)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(
          FilterDropdown,
          {
            definition: filterDefinition,
            label: label,
            sortable: sortable,
            sort: sort.value,
            'onUpdate:sort': (value: SortDirection) => {
              sort.value = value
            },
            extendsSortOf: extendsSortOf,
            extendedSort: extendedSort.value,
            'onUpdate:extendedSort': (value: SortDirection) => {
              extendedSort.value = value
            },
            modelValue: model.value,
            'onUpdate:modelValue': (value: ColumnFilterValue<FilterField> | undefined) => {
              model.value = value as ColumnFilterNode<FilterField> | undefined
            }
          },
          {
            trigger: ({
              toggle,
              isOpen,
              panelId
            }: {
              toggle: () => void
              isOpen: boolean
              panelId: string
            }) =>
              h(
                'button',
                {
                  type: 'button',
                  onClick: toggle,
                  'aria-expanded': isOpen,
                  'aria-controls': panelId
                },
                'Open'
              )
          }
        )
    }
  })
  return { model, sort, extendedSort, ...render(wrapper) }
}

test('a sort direction is reported as it is picked, on its own', async () => {
  const user = userEvent.setup()
  const { model, sort } = renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('button', { name: 'Sort ascending' }))

  expect(sort.value).toBe('asc')
  expect(model.value).toBeUndefined()
})

test('picking a sort direction closes the panel', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('button', { name: 'Sort descending' }))

  expect(screen.queryByRole('group', { name: 'Filter State' })).not.toBeInTheDocument()
})

test('extending the active sort closes the panel', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, true, ['Host name'])

  await user.click(screen.getByRole('button', { name: 'Open' }))
  const extend = screen.getByRole('group', { name: 'Extend active sorting of "Host name" by' })
  await user.click(within(extend).getByRole('button', { name: 'Sort ascending' }))

  expect(screen.queryByRole('group', { name: 'Filter State' })).not.toBeInTheDocument()
})

test('picking a sort direction applies the staged selection with it', async () => {
  const user = userEvent.setup()
  const { model, sort } = renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.click(screen.getByRole('button', { name: 'Sort descending' }))

  expect(sort.value).toBe('desc')
  expect(model.value).toEqual(upFilter())
})

test('extending the active sort applies the staged selection with it', async () => {
  const user = userEvent.setup()
  const { model, extendedSort } = renderDropdown(undefined, true, ['Host name'])

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  const extend = screen.getByRole('group', { name: 'Extend active sorting of "Host name" by' })
  await user.click(within(extend).getByRole('button', { name: 'Sort ascending' }))

  expect(extendedSort.value).toBe('asc')
  expect(model.value).toEqual(upFilter())
})

test('a column offers no sort directions unless it sorts', async () => {
  const user = userEvent.setup()
  renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.queryByRole('button', { name: 'Sort ascending' })).not.toBeInTheDocument()
})

test('opening the panel focuses the filter rather than the sort directions', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await nextTick()

  expect(screen.getByRole('checkbox', { name: 'Select all' })).toHaveFocus()
})

test('the sort is only offered for extension once another column sorts', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.queryByRole('group', { name: /Extend active sorting/ })).not.toBeInTheDocument()
})

test('extending the active sort is reported apart from sorting by the column', async () => {
  const user = userEvent.setup()
  const { sort, extendedSort } = renderDropdown(undefined, true, ['Host name'])

  await user.click(screen.getByRole('button', { name: 'Open' }))
  const extend = screen.getByRole('group', { name: 'Extend active sorting of "Host name" by' })
  await user.click(within(extend).getByRole('button', { name: 'Sort descending' }))

  expect(extendedSort.value).toBe('desc')
  expect(sort.value).toBe(false)
})

test('toggling an option does not commit to the model before Apply', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))

  expect(model.value).toBeUndefined()
})

test('Apply commits the staged selection and closes the dropdown', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(model.value).toEqual(upFilter())
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument()
})

test('Close discards the staged selection and leaves the model untouched', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(model.value).toBeUndefined()
  expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
})

test('a closed edit is gone when the dropdown is reopened', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown(upFilter())

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'DOWN' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.getByRole('checkbox', { name: 'UP' })).toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'DOWN' })).not.toBeChecked()
  expect(model.value).toEqual(upFilter())
})

test('a click that unmounts its own target does not close the funnel', async () => {
  const user = userEvent.setup()
  renderDropdown()
  await user.click(screen.getByRole('button', { name: 'Open' }))
  const panel = screen.getByRole('group', { name: 'Filter State' })

  // Stands in for floating content that unmounts as it is activated - a dropdown
  // option, say. It is still in the panel at pointerdown and detached by the time
  // the document-level click handler runs, so a containment check made then sees
  // a node that is inside nothing at all.
  const option = document.createElement('button')
  option.addEventListener('click', () => option.remove())
  panel.appendChild(option)

  option.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  option.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  await nextTick()

  expect(screen.queryByRole('group', { name: 'Filter State' })).not.toBeNull()
})

test('the trigger points at the panel it expands', async () => {
  const user = userEvent.setup()
  renderDropdown()

  const trigger = screen.getByRole('button', { name: 'Open' })
  expect(trigger).toHaveAttribute('aria-expanded', 'false')

  await user.click(trigger)

  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  const panel = screen.getByRole('group', { name: 'Filter State' })
  expect(trigger.getAttribute('aria-controls')).toBe(panel.id)
  expect(panel.id).not.toBe('')
})

test('Alt+ArrowDown on the trigger opens the panel and moves into it', async () => {
  const user = userEvent.setup()
  renderDropdown()

  const trigger = screen.getByRole('button', { name: 'Open' })
  trigger.focus()
  await user.keyboard('{ArrowDown}')
  expect(trigger).toHaveAttribute('aria-expanded', 'false')

  await user.keyboard('{Alt>}{ArrowDown}{/Alt}')

  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  const panel = screen.getByRole('group', { name: 'Filter State' })
  expect(panel).toContainElement(document.activeElement as HTMLElement)
})

function renderAnchoredDropdown(clipped = false) {
  const wrapper = defineComponent({
    setup() {
      const anchored = () =>
        h('div', { class: 'anchor' }, [
          h(
            FilterDropdown,
            {
              definition: definition,
              label: 'State',
              anchor: '.anchor',
              modelValue: undefined,
              'onUpdate:modelValue': () => {}
            },
            {
              trigger: ({
                toggle,
                isOpen,
                panelId
              }: {
                toggle: () => void
                isOpen: boolean
                panelId: string
              }) =>
                h(
                  'button',
                  {
                    type: 'button',
                    onClick: toggle,
                    'aria-expanded': isOpen,
                    'aria-controls': panelId
                  },
                  'Open'
                )
            }
          )
        ])
      return () =>
        clipped
          ? h('div', { class: 'clip', style: 'overflow-x: hidden' }, [anchored()])
          : anchored()
    }
  })
  return render(wrapper)
}

interface Box {
  top: number
  bottom: number
  left: number
  right: number
}

/** Lay `element` out at `box`, as both its border box and its client box. */
function stubBox(element: Element, { top, bottom, left, right }: Box): void {
  element.getBoundingClientRect = () =>
    ({
      top,
      bottom,
      left,
      right,
      width: right - left,
      height: bottom - top,
      x: left,
      y: top,
      toJSON: () => ({})
    }) as DOMRect
  Object.defineProperties(element, {
    clientWidth: { configurable: true, value: right - left },
    clientHeight: { configurable: true, value: bottom - top }
  })
}

/** A box spanning `left` to `right` in the table header row. */
function inHeader(left: number, right: number): Box {
  return { top: 0, bottom: 20, left, right }
}

/** A box spanning `top` to `bottom` in a column running from 100 to 300. */
function inColumn(top: number, bottom: number): Box {
  return { top, bottom, left: 100, right: 300 }
}

const nativeOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
const nativeOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')

/** Give the panel a size; like a browser, its height gives way to the max-height it is capped at. */
function stubPanelSize(width: number, naturalHeight: number): void {
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    value: width
  })
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    get(this: HTMLElement) {
      const cap = parseFloat(this.style.maxHeight)
      return Number.isNaN(cap) ? naturalHeight : Math.min(naturalHeight, cap)
    }
  })
}

afterEach(() => {
  if (nativeOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', nativeOffsetWidth)
  }
  if (nativeOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', nativeOffsetHeight)
  }
})

interface Layout {
  /** The scroll container around the column. Unset, nothing but the window clips the panel. */
  clip?: Box
  anchor: Box
  trigger: Box
}

function layOut({ clip, anchor, trigger }: Layout): void {
  if (clip) {
    stubBox(document.querySelector('.clip')!, clip)
  }
  stubBox(document.querySelector('.anchor')!, anchor)
  stubBox(document.querySelector('.monitoring-filter-dropdown')!, trigger)
}

async function openPanel(): Promise<HTMLElement> {
  await userEvent.setup().click(screen.getByRole('button', { name: 'Open' }))
  await nextTick()
  await nextTick()
  return screen.getByRole('group', { name: 'Filter State' })
}

async function openLaidOut(layout: Layout, panelHeight = 0): Promise<HTMLElement> {
  renderAnchoredDropdown(layout.clip !== undefined)
  layOut(layout)
  stubPanelSize(300, panelHeight)
  return openPanel()
}

test('the panel lines up with the left edge of its anchor', async () => {
  const panel = await openLaidOut({ anchor: inHeader(100, 300), trigger: inHeader(260, 280) })

  expect(panel.style.left).toBe('-160px')
  expect(panel.style.right).toBe('auto')
})

test('the panel lines up right when left would overflow', async () => {
  const panel = await openLaidOut({ anchor: inHeader(800, 1000), trigger: inHeader(960, 980) })

  expect(panel.style.left).toBe('auto')
  expect(panel.style.right).toBe('-20px')
})

test('a column scrolled past the left edge keeps the panel inside it', async () => {
  const panel = await openLaidOut({
    clip: inHeader(200, 900),
    anchor: inHeader(100, 300),
    trigger: inHeader(280, 300)
  })

  expect(panel.style.left).toBe('-80px')
  expect(panel.style.right).toBe('auto')
})

test('a column scrolled past the right edge keeps the panel inside it', async () => {
  const panel = await openLaidOut({
    clip: inHeader(200, 1000),
    anchor: inHeader(800, 1100),
    trigger: inHeader(1080, 1100)
  })

  expect(panel.style.left).toBe('auto')
  expect(panel.style.right).toBe('100px')
})

function headerAt(top: number, bottom: number, clip: Box): Layout {
  return { clip, anchor: inColumn(top, bottom), trigger: inColumn(top, bottom) }
}

test('a panel taller than the room below its trigger is capped to that room', async () => {
  const panel = await openLaidOut(headerAt(80, 100, inColumn(50, 400)), 600)

  expect(panel).not.toHaveClass('monitoring-filter-dropdown__panel--up')
  expect(panel.style.maxHeight).toBe('292px')
})

test('a panel flipped up is capped to the room above its trigger', async () => {
  const panel = await openLaidOut(headerAt(500, 520, inColumn(0, 700)), 600)

  expect(panel).toHaveClass('monitoring-filter-dropdown__panel--up')
  expect(panel.style.maxHeight).toBe('492px')
})

test('a container reaching past the window caps the panel at the window', async () => {
  // jsdom's window is 768px high.
  const panel = await openLaidOut(headerAt(80, 100, inColumn(0, 2000)), 1000)

  expect(panel.style.maxHeight).toBe('660px')
})

test('reopening the panel fits it from its natural height again', async () => {
  await openLaidOut(headerAt(80, 100, inColumn(50, 400)), 600)
  await userEvent.setup().click(screen.getByRole('button', { name: 'Cancel' }))

  // With 400px above and 300px below, the 600px panel flips up. Measured at the 292px cap of
  // the first opening, it would seem to fit below.
  layOut(headerAt(408, 428, inColumn(0, 736)))
  const panel = await openPanel()

  expect(panel).toHaveClass('monitoring-filter-dropdown__panel--up')
  expect(panel.style.maxHeight).toBe('400px')
})

test('resizing the window fits the open panel to its new room', async () => {
  const panel = await openLaidOut(headerAt(80, 100, inColumn(50, 400)), 600)

  layOut(headerAt(80, 100, inColumn(50, 600)))
  window.dispatchEvent(new Event('resize'))
  await nextTick()
  await nextTick()

  expect(panel.style.maxHeight).toBe('492px')
})

/** Give the panel's scroll area `height` of room, as its cap leaves it, and fit the panel again. */
async function leaveScrollRoom(height: number): Promise<HTMLElement> {
  const scrollArea = document.querySelector<HTMLElement>('.monitoring-filter-dropdown__scroll')!
  Object.defineProperty(scrollArea, 'clientHeight', { configurable: true, value: height })
  window.dispatchEvent(new Event('resize'))
  await nextTick()
  await nextTick()
  return scrollArea
}

test('filter content taller than the capped panel scrolls', async () => {
  await openLaidOut(headerAt(80, 100, inColumn(50, 400)), 600)

  const scrollArea = await leaveScrollRoom(250)

  expect(scrollArea).toHaveClass('monitoring-filter-dropdown__scroll--overflowing')
})

test('filter content that fits the panel does not scroll', async () => {
  await openLaidOut(headerAt(80, 100, inColumn(50, 400)), 200)

  const scrollArea = await leaveScrollRoom(250)

  expect(scrollArea).not.toHaveClass('monitoring-filter-dropdown__scroll--overflowing')
})

test('the arrow keys walk the suggestions one at a time', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, false, [], labelsDefinition, 'Labels')

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('searchbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))

  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toHaveFocus()

  // The shell walks the panel's rows on the same keys, so without the suggestion list
  // keeping them this second press would land on the third suggestion.
  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('button', { name: 'cmk/os_family:windows' })).toHaveFocus()

  await user.keyboard('{ArrowUp}')
  expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toHaveFocus()
})

test('Clear leaves the focus in the emptied filter field', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, false, [], nameDefinition, 'Host')

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('textbox', { name: 'Value' }), 'web')
  await user.click(screen.getByRole('button', { name: 'Clear' }))
  await nextTick()

  const field = screen.getByRole('textbox', { name: 'Value' })
  expect(field).toHaveValue('')
  expect(field).toHaveFocus()
})

test('Enter in a typed-in filter field commits it and closes the dropdown', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown(undefined, false, [], nameDefinition, 'Host')

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('textbox', { name: 'Value' }), 'web{Enter}')

  expect(model.value).toEqual({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument()
})

test('Enter in a suggestion search keeps the dropdown open', async () => {
  const user = userEvent.setup()
  renderDropdown(undefined, false, [], labelsDefinition, 'Labels')

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.type(screen.getByRole('searchbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  await user.keyboard('{Enter}')

  expect(screen.getByRole('searchbox')).toHaveValue('os_family')
  expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument()
})

test('Enter in the option search of a checkbox list keeps the dropdown open', async () => {
  const user = userEvent.setup()
  const { model } = renderDropdown(undefined, false, [], { ...definition, searchThreshold: 0 })

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('checkbox', { name: 'UP' }))
  await user.type(screen.getByRole('searchbox'), 'DO{Enter}')

  expect(model.value).toBeUndefined()
  expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument()
})
