/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import ObjectPropertiesModal from '@/maps/map/edit/properties/ObjectPropertiesModal.vue'
import type { MapElement, ObjectType } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// Stand-in for the confirmation popup: the real MapsConfirmDialog renders through
// reka-ui's Dialog, whose a11y title warning would trip the fail-on-console rule.
// The stub preserves the only contract the modal depends on — it surfaces a
// confirm affordance while open and re-emits `confirm` — so the delete flow stays
// observable without pulling the dialog internals into scope.
const confirmDialogStub = defineComponent({
  props: { open: { type: Boolean, default: false } },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () =>
      props.open
        ? h('button', { type: 'button', onClick: () => emit('confirm') }, 'Confirm delete')
        : null
  }
})

// The suggestion-driven inputs (object pickers, colour picker, custom-icon
// picker) and the composite dropdown are not the subject of these tests; stub
// them so the assertions target the card's own structure, native fields, and
// footer actions.
const stubs = {
  MapsSuggestionField: true,
  ImagePicker: true,
  MapsColorInput: true,
  CmkDropdown: true,
  MapsConfirmDialog: confirmDialogStub
}

function obj(extra: Partial<MapElement> & { type: ObjectType }): MapElement {
  return anObject({ id: 'o', x: 40, y: 60, url_target: '_blank', ...extra })
}

function renderModal(object: MapElement, extraProps: Record<string, unknown> = {}) {
  return render(ObjectPropertiesModal, {
    props: {
      object,
      connectionId: 'test',
      checkmkUrl: 'https://cmk.example.com/site',
      ...extraProps
    },
    global: mapsGlobal(stubs)
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  // The auth store reads this at creation; a present token keeps requireToken()
  // from throwing when the mounted autocomplete/metric loads fire.
  sessionStorage.setItem('maps_access_token', 'test-token')
})

describe('ObjectPropertiesModal – conditional fields by object type', () => {
  it('shows the monitoring-object fields for a host (hostname + both host toggles)', () => {
    renderModal(obj({ type: 'host', host_name: 'web01' }))

    expect(screen.getByText('Monitoring object')).toBeInTheDocument()
    expect(screen.getByText('Hostname')).toBeInTheDocument()
    expect(screen.getByText('Only hard states')).toBeInTheDocument()
    expect(screen.getByText('Consider services')).toBeInTheDocument()
    // Host is not a service/textbox/graph, so those sections stay hidden.
    expect(screen.queryByText('Service')).not.toBeInTheDocument()
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
    expect(screen.queryByText('Metric source')).not.toBeInTheDocument()
  })

  it('adds the service field for a service and drops the host-only toggle', () => {
    renderModal(obj({ type: 'service', host_name: 'web01', service_description: 'PING' }))

    expect(screen.getByText('Hostname')).toBeInTheDocument()
    // Twice: the header's type badge and the field's own label.
    expect(screen.getAllByText('Service')).toHaveLength(2)
    expect(screen.getByText('Only hard states')).toBeInTheDocument()
    // "Consider services" is host-only.
    expect(screen.queryByText('Consider services')).not.toBeInTheDocument()
  })

  it('renders the content editor for a textbox and hides object/appearance sections', () => {
    renderModal(obj({ type: 'textbox' }))

    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Text content/)).toBeInTheDocument()
    expect(screen.queryByText('Monitoring object')).not.toBeInTheDocument()
    // Appearance ("View type") is not offered for a textbox.
    expect(screen.queryByText('View type')).not.toBeInTheDocument()
  })

  it('renders line-specific styling and drops the generic position/appearance sections', () => {
    renderModal(obj({ type: 'line', x2: 200, y2: 60 }))

    // Twice: the header's type badge and the section title.
    expect(screen.getAllByText('Line')).toHaveLength(2)
    expect(screen.getByText('Style')).toBeInTheDocument()
    expect(screen.getByText('Perfdata label')).toBeInTheDocument()
    expect(screen.getByText('Color by utilization (weathermap)')).toBeInTheDocument()
    // Lines carry their own coordinate + label fields, so the shared
    // Position and Appearance sections are suppressed.
    expect(screen.queryByText('Position')).not.toBeInTheDocument()
    expect(screen.queryByText('View type')).not.toBeInTheDocument()
  })

  it('names the object type in words, never as its wire name', () => {
    renderModal(obj({ type: 'dyngroup' }))

    expect(screen.getByText('Dynamic group')).toBeInTheDocument()
    expect(screen.queryByText('dyngroup')).not.toBeInTheDocument()
  })

  it('renders the dyngroup host/service choice + livestatus filter fields', () => {
    renderModal(obj({ type: 'dyngroup' }))

    expect(screen.getByText('Filter on')).toBeInTheDocument()
    expect(screen.getByText('Livestatus filter')).toBeInTheDocument()
  })

  // The exclude-members preview counts BI leaves, so the aggregation is the one
  // object type whose filter the card can actually show a result for.
  it('offers the member filter to a BI aggregation', () => {
    renderModal(obj({ type: 'aggregation', aggregation_id: 'Hosts', exclude_members: 'test-.*' }))

    expect(screen.getByText('Exclude members')).toBeInTheDocument()
    expect(screen.getByText('Exclude states')).toBeInTheDocument()
  })

  it('renders the metric-source and url-embed sections for a graph', () => {
    renderModal(obj({ type: 'graph', host_name: 'web01', service_description: 'CPU' }))

    expect(screen.getByText('Metric source')).toBeInTheDocument()
    expect(screen.getByText('URL embed')).toBeInTheDocument()
    // Graphs render their own embed; the icon/appearance section is hidden.
    expect(screen.queryByText('View type')).not.toBeInTheDocument()
  })
})

describe('ObjectPropertiesModal – save payload', () => {
  it('emits a host payload with the host-only keys and no service field', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'host', host_name: 'web01' }))

    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(emitted().save).toHaveLength(1)
    const payload = (emitted().save as unknown[][])[0]![0] as Record<string, unknown>
    expect(payload).toMatchObject({
      host_name: 'web01',
      only_hard_states: false,
      recognize_services: false
    })
    // Position is persisted for a non-worldmap object.
    expect(payload).toMatchObject({ x: 40, y: 60 })
    // service_description belongs to service/graph objects, not a host.
    expect(payload).not.toHaveProperty('service_description')
  })

  it('emits a service payload carrying the service description', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(
      obj({ type: 'service', host_name: 'web01', service_description: 'PING' })
    )

    await user.click(screen.getByRole('button', { name: 'Save' }))

    const payload = (emitted().save as unknown[][])[0]![0] as Record<string, unknown>
    expect(payload).toMatchObject({ host_name: 'web01', service_description: 'PING' })
    // recognize_services is a host-only field.
    expect(payload).not.toHaveProperty('recognize_services')
  })

  it('carries edits to the textbox content into the label payload', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'textbox' }))

    await user.type(screen.getByPlaceholderText(/Text content/), 'Rack A – core switches')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    const payload = (emitted().save as unknown[][])[0]![0] as Record<string, unknown>
    const label = payload.label as Record<string, unknown>
    expect(label.text).toBe('Rack A – core switches')
  })

  it('blocks the save and shows an error when weather coloring has no metric', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(
      obj({ type: 'line', line_weather_color: true, weathermap_metric: '', x2: 200, y2: 60 })
    )

    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText(/weather coloring needs one/)).toBeInTheDocument()
    expect(emitted().save).toBeUndefined()
  })
})

describe('ObjectPropertiesModal – close / detach / delete', () => {
  it('emits close from the Cancel button, the close icon, and the Escape key', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'host', host_name: 'web01' }))

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Close' }))
    await user.keyboard('{Escape}')

    expect(emitted().close).toHaveLength(3)
  })

  it('emits detach for an attached line', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'line', start_ref: 'anchor-1', x2: 200, y2: 60 }))

    await user.click(screen.getByRole('button', { name: 'Detach from object' }))

    expect(emitted().detach).toHaveLength(1)
  })

  it('emits delete only after the confirmation dialog is confirmed', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'host', host_name: 'web01' }))

    // The footer Delete button just opens the confirm dialog — nothing is
    // emitted yet.
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(emitted().delete).toBeUndefined()

    await user.click(await screen.findByRole('button', { name: 'Confirm delete' }))

    await waitFor(() => expect(emitted().delete).toHaveLength(1))
  })
})

describe('ObjectPropertiesModal – popover placement', () => {
  // Embedded in the Checkmk page, the card's fixed overlay is contained by the
  // content area rather than the viewport, so its left/top are read in that
  // box's coordinates. jsdom lays nothing out, so stand in for the browser's
  // measurements — the clamping on top of them is what is under test.
  const FRAME = { left: 74, top: 0, width: 1292, height: 768 }
  const CARD = { width: 402, height: 578 }

  function measureAs(frame: typeof FRAME, card: typeof CARD): void {
    const parent = document.createElement('div')
    parent.getBoundingClientRect = () =>
      ({ ...frame, right: frame.left + frame.width, bottom: frame.top + frame.height }) as DOMRect
    vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockReturnValue(parent)
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(card.width)
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(card.height)
  }

  async function renderPlaced(
    frame: typeof FRAME,
    anchorRect: { left: number; top: number; right: number; bottom: number } | null
  ): Promise<CSSStyleDeclaration> {
    measureAs(frame, CARD)
    const { container } = renderModal(obj({ type: 'host', host_name: 'web01' }), { anchorRect })
    // The card can only be measured once it is in the DOM, so the placement
    // lands a tick after the first render.
    await nextTick()
    return container.querySelector<HTMLElement>('.maps-object-properties-modal__card')!.style
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens beside the object, in the frame coordinates rather than the viewport ones', async () => {
    const style = await renderPlaced(FRAME, { left: 174, top: 100, right: 274, bottom: 160 })

    // 274 (anchor right, viewport) - 74 (frame left) + 12 (margin).
    expect(style.left).toBe('212px')
    expect(style.top).toBe('100px')
  })

  it('flips the card to the left of an object near the frame right edge', async () => {
    const style = await renderPlaced(FRAME, { left: 1230, top: 100, right: 1330, bottom: 160 })

    // 1230 (anchor left) - 74 (frame left) - 12 (margin) - 402 (card width).
    expect(style.left).toBe('742px')
  })

  it('pins a card too wide for either side inside the frame', async () => {
    const style = await renderPlaced(
      { left: 74, top: 0, width: 500, height: 768 },
      { left: 300, top: 100, right: 400, bottom: 160 }
    )

    expect(style.left).toBe('12px')
  })

  it('lifts the card so its bottom stays inside the frame', async () => {
    const style = await renderPlaced(FRAME, { left: 174, top: 700, right: 274, bottom: 760 })

    // 768 (frame height) - 578 (card height) - 12 (margin).
    expect(style.top).toBe('178px')
  })

  it('centers as an unplaced modal when the object gave no anchor', async () => {
    const style = await renderPlaced(FRAME, null)

    expect(style.left).toBe('')
    expect(style.top).toBe('')
  })

  it('leaves a card the operator dragged aside where they put it', async () => {
    const user = userEvent.setup()
    measureAs(FRAME, CARD)
    const { container } = renderModal(obj({ type: 'host', host_name: 'web01' }), {
      anchorRect: { left: 174, top: 100, right: 274, bottom: 160 }
    })
    await nextTick()
    const card = container.querySelector<HTMLElement>('.maps-object-properties-modal__card')!
    const header = card.querySelector<HTMLElement>('.maps-object-properties-modal__header')!

    await user.pointer([
      { target: header, coords: { clientX: 500, clientY: 300 }, keys: '[MouseLeft>]' },
      { target: header, coords: { clientX: 700, clientY: 400 } },
      { target: header, keys: '[/MouseLeft]' }
    ])
    const draggedTo = { left: card.style.left, top: card.style.top }

    // A section folds open and makes the card taller. Re-placing would now
    // compute a different top (the clamp has less room), which is exactly the
    // snatch-back the drag must survive.
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(740)
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect({ left: card.style.left, top: card.style.top }).toEqual(draggedTo)
    expect(card.style.transform).toBe('translate(200px, 100px)')
  })

  it('re-places an undragged card when it grows past the frame', async () => {
    measureAs(FRAME, CARD)
    const { container } = renderModal(obj({ type: 'host', host_name: 'web01' }), {
      anchorRect: { left: 174, top: 100, right: 274, bottom: 160 }
    })
    await nextTick()
    const card = container.querySelector<HTMLElement>('.maps-object-properties-modal__card')!
    expect(card.style.top).toBe('100px')

    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(740)
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    // 768 (frame height) - 740 (card height) - 12 (margin).
    expect(card.style.top).toBe('16px')
  })
})
