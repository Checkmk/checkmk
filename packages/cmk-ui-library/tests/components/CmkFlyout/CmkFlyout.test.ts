/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFlyout from 'cmk-ui-library/components/CmkFlyout'
import { provideFloatingBoundary } from 'cmk-ui-library/lib/useFloatingTarget'
import { afterEach, beforeEach, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

// CmkFlyout is fully controlled: it never opens or closes itself. The host owns `open`, toggles it
// from the trigger, and closes on the `cancel` event (Escape / outside press / focus leaving).
const renderFlyout = (props: Record<string, unknown> = {}) =>
  render(
    defineComponent({
      components: { CmkFlyout },
      data: () => ({
        open: false,
        cancelCount: 0,
        boundProps: props
      }),
      methods: {
        onCancel(this: { open: boolean; cancelCount: number }) {
          this.cancelCount += 1
          this.open = false
        },
        restoreFocus(this: { $refs: Record<string, unknown> }) {
          const toggle = this.$refs.toggle
          if (toggle instanceof HTMLElement) {
            toggle.focus()
          }
        }
      },
      template: `
        <CmkFlyout :open="open" :restore-focus="restoreFocus" v-bind="boundProps" @cancel="onCancel">
          <template #trigger="{ aria }">
            <button ref="toggle" type="button" v-bind="aria" @click="open = !open">Toggle</button>
          </template>
          <div>Flyout body</div>
          <button type="button">Inside</button>
        </CmkFlyout>
        <button type="button" @click="open = !open">Outside toggle</button>
        <span data-testid="open">{{ open }}</span>
        <span data-testid="cancel">{{ cancelCount }}</span>
      `
    })
  )

const openState = () => screen.getByTestId('open').textContent
const cancelCount = () => screen.getByTestId('cancel').textContent

test('CmkFlyout renders the trigger slot and keeps the popup closed initially', () => {
  renderFlyout()

  expect(screen.getByRole('button', { name: 'Toggle' })).toBeInTheDocument()
  expect(screen.queryByText('Flyout body')).not.toBeInTheDocument()
  expect(openState()).toBe('false')
})

test('CmkFlyout reveals its body when the owner opens it', async () => {
  renderFlyout()

  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

  expect(screen.getByText('Flyout body')).toBeInTheDocument()
  expect(openState()).toBe('true')
})

test('CmkFlyout closes and emits cancel on Escape', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

  await fireEvent.keyDown(screen.getByText('Flyout body'), { key: 'Escape' })

  expect(screen.queryByText('Flyout body')).not.toBeInTheDocument()
  expect(openState()).toBe('false')
  expect(cancelCount()).toBe('1')
})

test('CmkFlyout dismisses on an outside press', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))
  expect(openState()).toBe('true')

  await fireEvent.pointerDown(screen.getByRole('button', { name: 'Outside toggle' }))

  expect(screen.queryByText('Flyout body')).not.toBeInTheDocument()
  expect(openState()).toBe('false')
  expect(cancelCount()).toBe('1')
})

test('CmkFlyout does not emit cancel for an owner-driven close (re-clicking the trigger)', async () => {
  renderFlyout()
  const trigger = screen.getByRole('button', { name: 'Toggle' })

  await fireEvent.click(trigger)
  expect(openState()).toBe('true')

  // Closing via the trigger is the owner writing `open` — not a flyout-detected dismissal, so no
  // `cancel` is emitted (the owner already knows it closed it).
  await fireEvent.click(trigger)
  expect(openState()).toBe('false')
  expect(cancelCount()).toBe('0')
})

test('CmkFlyout exposes dialog semantics and wires the trigger aria', async () => {
  renderFlyout({ label: 'Demo flyout' })
  const trigger = screen.getByRole('button', { name: 'Toggle' })
  expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
  expect(trigger).toHaveAttribute('aria-expanded', 'false')

  await fireEvent.click(trigger)

  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  const dialog = screen.getByRole('dialog')
  expect(dialog).toHaveAttribute('aria-label', 'Demo flyout')
  expect(trigger).toHaveAttribute('aria-controls', dialog.id)
})

test('CmkFlyout closes and cancels when focus leaves while open', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))
  expect(openState()).toBe('true')

  await fireEvent.focusOut(screen.getByText('Flyout body'), {
    relatedTarget: screen.getByRole('button', { name: 'Outside toggle' })
  })

  expect(openState()).toBe('false')
  expect(cancelCount()).toBe('1')
})

test('CmkFlyout stays open when focus drops to nowhere (no relatedTarget)', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))
  const inside = screen.getByRole('button', { name: 'Inside' })
  inside.focus()

  // The window keeps focus (the real case); jsdom's hasFocus() is false by default.
  const hasFocus = vi.spyOn(document, 'hasFocus').mockReturnValue(true)

  // A focusout with no relatedTarget — focus dropping to <body>, or a re-render unmounting the
  // focused node — is never a deliberate exit, so the flyout must stay open.
  await fireEvent.focusOut(inside, { relatedTarget: null })
  await nextTick()

  expect(openState()).toBe('true')
  expect(cancelCount()).toBe('0')
  hasFocus.mockRestore()
})

test('CmkFlyout does not cancel when focus leaves while closed', async () => {
  renderFlyout()

  // A keyboard tab-away off the closed trigger is the owner's concern (e.g. reverting a draft),
  // not the flyout's — the flyout only dismisses (and cancels) while open.
  await fireEvent.focusOut(screen.getByRole('button', { name: 'Toggle' }), {
    relatedTarget: screen.getByRole('button', { name: 'Outside toggle' })
  })

  expect(cancelCount()).toBe('0')
})

test('CmkFlyout calls restoreFocus when it closes with focus inside the popup', async () => {
  renderFlyout()
  const toggle = screen.getByRole('button', { name: 'Toggle' })
  await fireEvent.click(toggle)

  // The user tabbed/clicked into the popup, so focus is inside it when it closes.
  const inside = screen.getByRole('button', { name: 'Inside' })
  inside.focus()
  expect(document.activeElement).toBe(inside)

  await fireEvent.keyDown(inside, { key: 'Escape' })

  // restoreFocus ran (focusing the trigger button) before the popup unmounted, so focus did not
  // fall back to <body> when the focused popup element was removed.
  expect(openState()).toBe('false')
  expect(document.activeElement).toBe(toggle)
})

test('CmkFlyout does not move focus on close when focus is not inside the popup', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

  // Focus rests on an outside control, not inside the popup: closing must not steal it back.
  const outside = screen.getByRole('button', { name: 'Outside toggle' })
  outside.focus()

  await fireEvent.keyDown(screen.getByText('Flyout body'), { key: 'Escape' })

  expect(openState()).toBe('false')
  expect(document.activeElement).toBe(outside)
})

test('CmkFlyout emits a single cancel when an outside press dismisses it', async () => {
  renderFlyout()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))
  expect(openState()).toBe('true')

  // An outside press dismisses (cancel #1) and the owner closes; the trailing focusout (the browser
  // moving focus to the pressed control) must not emit a second cancel.
  const outside = screen.getByRole('button', { name: 'Outside toggle' })
  await fireEvent.pointerDown(outside)
  await fireEvent.focusOut(screen.getByRole('button', { name: 'Toggle' }), {
    relatedTarget: outside
  })

  expect(openState()).toBe('false')
  expect(cancelCount()).toBe('1')
})

// A child flyout nested in a parent flyout's body coordinates through useFlyoutNesting, so the
// parent does not dismiss itself while the child is open.
const renderNestedFlyouts = () =>
  render(
    defineComponent({
      components: { CmkFlyout },
      data: () => ({
        parentOpen: false,
        childOpen: false,
        parentCancel: 0,
        childCancel: 0
      }),
      methods: {
        onParentCancel(this: { parentOpen: boolean; parentCancel: number }) {
          this.parentCancel += 1
          this.parentOpen = false
        },
        onChildCancel(this: { childOpen: boolean; childCancel: number }) {
          this.childCancel += 1
          this.childOpen = false
        }
      },
      template: `
        <CmkFlyout :open="parentOpen" :restore-focus="() => {}" @cancel="onParentCancel">
          <template #trigger>
            <button type="button" @click="parentOpen = !parentOpen">Parent</button>
          </template>
          <div>Parent body</div>
          <CmkFlyout :open="childOpen" :restore-focus="() => {}" @cancel="onChildCancel">
            <template #trigger>
              <button type="button" @click="childOpen = !childOpen">Child</button>
            </template>
            <div>Child body</div>
          </CmkFlyout>
        </CmkFlyout>
        <button type="button" @click="parentOpen = false">Outside</button>
        <span data-testid="parentOpen">{{ parentOpen }}</span>
        <span data-testid="childOpen">{{ childOpen }}</span>
        <span data-testid="parentCancel">{{ parentCancel }}</span>
        <span data-testid="childCancel">{{ childCancel }}</span>
      `
    })
  )

const openNested = async () => {
  await fireEvent.click(screen.getByRole('button', { name: 'Parent' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Child' }))
  expect(screen.getByTestId('parentOpen').textContent).toBe('true')
  expect(screen.getByTestId('childOpen').textContent).toBe('true')
}

test('CmkFlyout Escape closes only the innermost open flyout', async () => {
  renderNestedFlyouts()
  await openNested()

  await fireEvent.keyDown(screen.getByText('Child body'), { key: 'Escape' })

  expect(screen.getByTestId('childOpen').textContent).toBe('false')
  expect(screen.getByTestId('parentOpen').textContent).toBe('true')
  expect(screen.getByTestId('childCancel').textContent).toBe('1')
  expect(screen.getByTestId('parentCancel').textContent).toBe('0')
})

test('CmkFlyout outside press dismisses only the child while one is open', async () => {
  renderNestedFlyouts()
  await openNested()

  await fireEvent.pointerDown(screen.getByRole('button', { name: 'Outside' }))

  expect(screen.getByTestId('childOpen').textContent).toBe('false')
  expect(screen.getByTestId('parentOpen').textContent).toBe('true')
  expect(screen.getByTestId('childCancel').textContent).toBe('1')
  expect(screen.getByTestId('parentCancel').textContent).toBe('0')
})

// Floating changes where the popup is placed, nothing about how it is dismissed or focused.
describe('CmkFlyout floating', () => {
  test('emits a single cancel when an outside press dismisses it', async () => {
    renderFlyout({ floating: true })
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

    await fireEvent.pointerDown(screen.getByRole('button', { name: 'Outside toggle' }))

    expect(openState()).toBe('false')
    expect(cancelCount()).toBe('1')
  })

  test('tabbing out past the popup dismisses it', async () => {
    const user = userEvent.setup()
    renderFlyout({ floating: true })
    await user.click(screen.getByRole('button', { name: 'Toggle' }))
    screen.getByRole('button', { name: 'Inside' }).focus()

    await user.tab()

    expect(openState()).toBe('false')
    expect(cancelCount()).toBe('1')
  })

  test('is placed by the time its owner focuses into it', async () => {
    // Focusing a popup still inside a scroll container would scroll the container.
    let positionAtFocus: string | undefined
    render(
      defineComponent({
        components: { CmkFlyout },
        data: () => ({ open: false }),
        methods: {
          async openAndFocus() {
            this.open = true
            await nextTick()
            positionAtFocus = document.querySelector<HTMLElement>('[role="dialog"]')?.style.position
          }
        },
        template: `
          <CmkFlyout :open="open" :restore-focus="() => {}" floating @cancel="open = false">
            <template #trigger="{ aria }">
              <button type="button" v-bind="aria" @click="openAndFocus">Toggle</button>
            </template>
            <div>Flyout body</div>
          </CmkFlyout>
        `
      })
    )

    await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

    expect(positionAtFocus).toBe('fixed')
  })
})

describe('CmkFlyout floating placement', () => {
  // jsdom lays nothing out: give the window, the trigger and the popup their boxes.
  const VIEWPORT = { width: 1000, height: 800 }
  const POPUP = { width: 300, height: 400 }

  function box(top: number, height: number, width: number, left = 100): DOMRect {
    return new DOMRect(left, top, width, height)
  }

  const isPopup = (el: HTMLElement): boolean => el.classList.contains('cmk-flyout__popup')

  beforeEach(() => {
    vi.spyOn(document.documentElement, 'clientWidth', 'get').mockReturnValue(VIEWPORT.width)
    vi.spyOn(document.documentElement, 'clientHeight', 'get').mockReturnValue(VIEWPORT.height)
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockImplementation(function (
      this: HTMLElement
    ) {
      return isPopup(this) ? POPUP.width : 0
    })
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockImplementation(function (
      this: HTMLElement
    ) {
      return isPopup(this) ? POPUP.height : 0
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // Hosts the flyout in an area that confines its popup, laid out at `boundary`.
  const boundaryHost = defineComponent({
    props: { boundary: { type: Object as () => DOMRect | null, default: null } },
    setup(props, { slots }) {
      provideFloatingBoundary(() =>
        props.boundary
          ? (document.querySelector('[data-testid="boundary"]') ?? undefined)
          : undefined
      )
      return () => h('div', { 'data-testid': 'boundary' }, slots.default?.())
    }
  })

  async function openPlaced(
    triggerTop: number,
    boundary: DOMRect | null = null,
    triggerLeft = 100,
    origin = { top: 0, left: 0 }
  ): Promise<HTMLElement> {
    render(
      defineComponent({
        components: { CmkFlyout, BoundaryHost: boundaryHost },
        data: () => ({ open: false, floating: true, boundary }),
        template: `
          <BoundaryHost :boundary="boundary">
            <CmkFlyout :open="open" :restore-focus="() => {}" :floating="floating" @cancel="open = false">
              <template #trigger="{ aria }">
                <button type="button" v-bind="aria" @click="open = !open">Toggle</button>
              </template>
              <div>Flyout body</div>
            </CmkFlyout>
          </BoundaryHost>
          <button type="button" @click="floating = false">Stop floating</button>
        `
      })
    )
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: HTMLElement
    ) {
      // The popup measures itself at the origin, to find its containing block's.
      return isPopup(this)
        ? new DOMRect(origin.left, origin.top, POPUP.width, POPUP.height)
        : new DOMRect(0, 0, 0, 0)
    })
    document.querySelector<HTMLElement>('.cmk-flyout')!.getBoundingClientRect = () =>
      box(triggerTop, 20, 200, triggerLeft)
    if (boundary) {
      const host = screen.getByTestId('boundary')
      host.getBoundingClientRect = () => boundary
      Object.defineProperties(host, {
        clientWidth: { configurable: true, value: boundary.width },
        clientHeight: { configurable: true, value: boundary.height }
      })
    }

    await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))
    await vi.waitFor(() => expect(screen.getByRole('dialog').style.position).toBe('fixed'))
    return screen.getByRole('dialog')
  }

  test('opens below a trigger with room below, uncapped', async () => {
    const popup = await openPlaced(100)

    // Trigger bottom 120 plus the 4px gap.
    expect(popup.style.top).toBe('124px')
    expect(popup.style.maxHeight).toBe('')
    expect(popup.style.overflowY).toBe('')
  })

  test('opens above a trigger with room only above', async () => {
    const popup = await openPlaced(600)

    // Trigger top 600 less the 4px gap and the popup's 400.
    expect(popup.style.top).toBe('196px')
  })

  test('moves over a trigger with room on neither side', async () => {
    const popup = await openPlaced(390)

    // As low as the window leaves room for: 800 - 8 - 400.
    expect(popup.style.top).toBe('392px')
  })

  test('stays within the boundary when the trigger lies outside it', async () => {
    const popup = await openPlaced(100, new DOMRect(0, 200, 1000, 600))

    expect(popup.style.top).toBe('208px')
  })

  test('scrolls where even the boundary is too short', async () => {
    const popup = await openPlaced(150, new DOMRect(0, 100, 1000, 300))

    expect(popup.style.top).toBe('108px')
    expect(popup.style.maxHeight).toBe('284px')
    expect(popup.style.overflowY).toBe('auto')
  })

  test('moves sideways from a trigger too close to the edge of the window', async () => {
    const popup = await openPlaced(100, null, 900)

    // As far right as the window leaves room for: 1000 - 8 - 300.
    expect(popup.style.left).toBe('692px')
  })

  test('offsets its position by a shifted containing block', async () => {
    // A transformed ancestor moves the containing block's origin off the viewport's.
    const popup = await openPlaced(100, null, 100, { top: 30, left: 50 })

    expect(popup.style.top).toBe('94px')
    expect(popup.style.left).toBe('50px')
  })

  function moveTrigger(top: number): void {
    document.querySelector<HTMLElement>('.cmk-flyout')!.getBoundingClientRect = () =>
      box(top, 20, 200)
  }

  test('follows its trigger when a container scrolls', async () => {
    const popup = await openPlaced(100)
    moveTrigger(50)

    await fireEvent.scroll(screen.getByTestId('boundary'))

    expect(popup.style.top).toBe('74px')
  })

  test('stays in place when scrolling inside the popup', async () => {
    const popup = await openPlaced(100)
    moveTrigger(50)

    await fireEvent.scroll(popup)

    expect(popup.style.top).toBe('124px')
  })

  test('goes back below its trigger when it stops floating', async () => {
    const popup = await openPlaced(600)

    await fireEvent.click(screen.getByRole('button', { name: 'Stop floating' }))

    expect(popup.style.position).toBe('')
    expect(popup.style.top).toBe('')
  })
})
