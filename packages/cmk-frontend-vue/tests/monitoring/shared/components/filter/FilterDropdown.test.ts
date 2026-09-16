/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h, nextTick, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'
import FilterDropdown from '@/monitoring/shared/components/filter/FilterDropdown.vue'
import type {
  CheckboxListFilter,
  ColumnFilterValue,
  SortDirection
} from '@/monitoring/shared/components/filter/types'

const definition: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: 'UP' },
    { value: 'DOWN', title: 'DOWN' }
  ]
}

function upFilter(): ColumnFilterNode<'state'> {
  return { type: 'condition', field: 'state', op: 'one_of', value: ['UP'] }
}

// Wrapper holding the committed model so we can observe what the dropdown
// commits, and supplying the trigger slot the shell expects.
function renderDropdown(
  initial: ColumnFilterNode<FilterField> | undefined = undefined,
  sortable: boolean = false
) {
  const model = ref<ColumnFilterNode<FilterField> | undefined>(initial)
  const sort = ref<SortDirection>(false)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(
          FilterDropdown,
          {
            definition: definition,
            label: 'State',
            sortable: sortable,
            sort: sort.value,
            'onUpdate:sort': (value: SortDirection) => {
              sort.value = value
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
  return { model, sort, ...render(wrapper) }
}

test('a sort direction is reported as it is picked, on its own', async () => {
  const user = userEvent.setup()
  const { model, sort } = renderDropdown(undefined, true)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await user.click(screen.getByRole('button', { name: 'Sort ascending' }))

  expect(sort.value).toBe('asc')
  expect(model.value).toBeUndefined()
})

test('a column offers no sort directions unless it sorts', async () => {
  const user = userEvent.setup()
  renderDropdown()

  await user.click(screen.getByRole('button', { name: 'Open' }))

  expect(screen.queryByRole('button', { name: 'Sort ascending' })).not.toBeInTheDocument()
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

function stubRect(element: Element, left: number, right: number): void {
  element.getBoundingClientRect = () =>
    ({
      left,
      right,
      top: 0,
      bottom: 20,
      width: right - left,
      height: 20,
      x: left,
      y: 0,
      toJSON: () => ({})
    }) as DOMRect
}

const nativeOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

function stubPanelWidth(width: number): void {
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    value: width
  })
}

afterEach(() => {
  if (nativeOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', nativeOffsetWidth)
  }
})

async function openAnchored(anchorRight: number, triggerRight: number): Promise<HTMLElement> {
  const user = userEvent.setup()
  renderAnchoredDropdown()
  stubRect(document.querySelector('.anchor')!, anchorRight - 200, anchorRight)
  stubRect(document.querySelector('.monitoring-filter-dropdown')!, triggerRight - 20, triggerRight)
  stubPanelWidth(300)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await nextTick()
  return screen.getByRole('group', { name: 'Filter State' })
}

test('the panel lines up with the left edge of its anchor', async () => {
  const panel = await openAnchored(300, 280)

  expect(panel.style.left).toBe('-160px')
  expect(panel.style.right).toBe('auto')
})

test('the panel lines up right when left would overflow', async () => {
  const panel = await openAnchored(1000, 980)

  expect(panel.style.left).toBe('auto')
  expect(panel.style.right).toBe('-20px')
})

async function openClipped(
  anchor: { left: number; right: number },
  clip: { left: number; right: number }
): Promise<HTMLElement> {
  const user = userEvent.setup()
  renderAnchoredDropdown(true)
  stubRect(document.querySelector('.clip')!, clip.left, clip.right)
  stubRect(document.querySelector('.anchor')!, anchor.left, anchor.right)
  stubRect(document.querySelector('.monitoring-filter-dropdown')!, anchor.right - 20, anchor.right)
  stubPanelWidth(300)

  await user.click(screen.getByRole('button', { name: 'Open' }))
  await nextTick()
  return screen.getByRole('group', { name: 'Filter State' })
}

test('a column scrolled past the left edge keeps the panel inside it', async () => {
  const panel = await openClipped({ left: 100, right: 300 }, { left: 200, right: 900 })

  expect(panel.style.left).toBe('-80px')
  expect(panel.style.right).toBe('auto')
})

test('a column scrolled past the right edge keeps the panel inside it', async () => {
  const panel = await openClipped({ left: 800, right: 1100 }, { left: 200, right: 1000 })

  expect(panel.style.left).toBe('auto')
  expect(panel.style.right).toBe('100px')
})
