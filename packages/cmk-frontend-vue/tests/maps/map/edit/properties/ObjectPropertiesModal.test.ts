/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import ObjectPropertiesModal from '@/maps/map/edit/properties/ObjectPropertiesModal.vue'
import type { MapElement, ObjectType } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// Stand-in for the confirmation popup: the real MapsConfirmDialog renders through
// reka-ui's Dialog, whose a11y title warning would trip the fail-on-console rule.
// The stub preserves the only contract the modal depends on — it surfaces a
// confirm affordance named after its action while open and re-emits `confirm` —
// so the delete and discard flows stay observable without pulling the dialog
// internals into scope.
const confirmDialogStub = defineComponent({
  props: { open: { type: Boolean, default: false }, confirmLabel: { type: String, default: '' } },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () =>
      props.open
        ? h(
            'button',
            { type: 'button', onClick: () => emit('confirm') },
            `Confirm ${props.confirmLabel.toLowerCase()}`
          )
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
  // The auth store reads this at creation; a present token keeps requireToken()
  // from throwing when the mounted autocomplete/metric loads fire.
  sessionStorage.setItem('maps_access_token', 'test-token')
})

describe('ObjectPropertiesModal – conditional fields by object type', () => {
  it('shows the monitoring-object fields for a host (hostname + both host toggles)', () => {
    renderModal(obj({ type: 'host', host_name: 'web01' }))

    expect(screen.getByText('Monitoring object')).toBeInTheDocument()
    expect(screen.getByText('Host name')).toBeInTheDocument()
    expect(screen.getByText('Only hard states')).toBeInTheDocument()
    expect(screen.getByText('Consider services')).toBeInTheDocument()
    // Host is not a service/textbox/graph, so those sections stay hidden.
    expect(screen.queryByText('Service')).not.toBeInTheDocument()
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
    expect(screen.queryByText('Metric source')).not.toBeInTheDocument()
  })

  it('adds the service field for a service and drops the host-only toggle', () => {
    renderModal(obj({ type: 'service', host_name: 'web01', service_description: 'PING' }))

    expect(screen.getByText('Host name')).toBeInTheDocument()
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

  it('asks a line for the object it shows the state of', () => {
    renderModal(obj({ type: 'line', line_object_type: 'hostgroup', group_name: 'web' }))

    expect(screen.getByText('Shows the state of')).toBeInTheDocument()
    expect(screen.getByText('Group name')).toBeInTheDocument()
  })

  it('offers no perfdata on a line that shows no service', () => {
    renderModal(obj({ type: 'line', line_object_type: 'hostgroup', group_name: 'web' }))

    expect(screen.queryByText('Perfdata label')).not.toBeInTheDocument()
  })

  it('renders line-specific styling and drops the generic position/appearance sections', () => {
    renderModal(
      obj({
        type: 'line',
        host_name: 'sw01',
        service_description: 'Interface 1',
        x2: 200,
        y2: 60
      })
    )

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
    expect(screen.getByText('Consider services')).toBeInTheDocument()
  })

  it('offers the services toggle only to a dynamic group of hosts', () => {
    renderModal(obj({ type: 'dyngroup', object_types: 'service' }))

    expect(screen.getByText('Only hard states')).toBeInTheDocument()
    expect(screen.queryByText('Consider services')).not.toBeInTheDocument()
  })

  it('offers the member filter to a host group, also as a line', () => {
    renderModal(
      obj({ type: 'line', line_object_type: 'hostgroup', group_name: 'web', exclude_members: 'x' })
    )

    expect(screen.getByText('Exclude members')).toBeInTheDocument()
    expect(screen.getByText('Exclude members from state')).toBeInTheDocument()
  })

  it('offers no member filter where the daemon applies none', () => {
    renderModal(obj({ type: 'aggregation', aggregation_id: 'Hosts', exclude_members: 'x' }))

    expect(screen.queryByText('Exclude members')).not.toBeInTheDocument()
  })

  it('renders the metric-source and url-embed sections for a graph', () => {
    renderModal(obj({ type: 'graph', host_name: 'web01', service_description: 'CPU' }))

    expect(screen.getByText('Metric source')).toBeInTheDocument()
    expect(screen.getByText('URL embed')).toBeInTheDocument()
    // Graphs render their own embed; the icon/appearance section is hidden.
    expect(screen.queryByText('View type')).not.toBeInTheDocument()
  })

  it('offers an image only the template placeholders it can fill', () => {
    renderModal(obj({ type: 'image', hover_template: '{{name}}' }))

    expect(screen.getByText('Available: {{name}}')).toBeInTheDocument()
  })
})

describe('ObjectPropertiesModal – field names', () => {
  it('names each field by its row', () => {
    renderModal(
      obj({
        type: 'host',
        host_name: 'web01',
        label: { show: true, x: 0, y: 0, size: 11, color: '#fff', background: 'transparent' }
      })
    )

    expect(within(screen.getByRole('group', { name: 'Position' })).getByLabelText('X')).toHaveValue(
      40
    )
    expect(within(screen.getByRole('group', { name: 'Offset' })).getByLabelText('X')).toHaveValue(0)
    expect(screen.getByLabelText('Text')).toBeInTheDocument()
    expect(screen.getByLabelText('Font size')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Show label' })).toBeInTheDocument()
  })

  it('shows the label settings only while the label is shown', async () => {
    renderModal(obj({ type: 'host', host_name: 'web01' }))
    expect(screen.queryByLabelText('Font size')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('checkbox', { name: 'Show label' }))

    expect(screen.getByLabelText('Font size')).toBeInTheDocument()
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
      obj({
        type: 'line',
        host_name: 'sw01',
        service_description: 'Interface 1',
        line_weather_color: true,
        weathermap_metric: '',
        x2: 200,
        y2: 60
      })
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

  it('closes on Escape while a layer elsewhere on the page stays open', async () => {
    const user = userEvent.setup()
    const { emitted } = renderModal(obj({ type: 'host', host_name: 'web01' }))
    const elsewhere = document.body.appendChild(document.createElement('div'))
    elsewhere.setAttribute('data-dismissable-layer', '')

    await user.keyboard('{Escape}')
    elsewhere.remove()

    expect(emitted().close).toHaveLength(1)
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

describe('ObjectPropertiesModal – a click on the map', () => {
  function clickMap(container: Element): Promise<void> {
    return userEvent.click(
      container.querySelector<HTMLElement>('.maps-object-properties-modal__backdrop')!
    )
  }

  function renderClosable(object: MapElement): { container: Element; closes: () => number } {
    let closes = 0
    const { container } = renderModal(object, {
      onClose: () => {
        closes += 1
      }
    })
    return { container, closes: () => closes }
  }

  it('closes an untouched card', async () => {
    const { container, closes } = renderClosable(obj({ type: 'textbox' }))

    await clickMap(container)

    expect(closes()).toBe(1)
    expect(screen.queryByRole('button', { name: 'Discard changes' })).toBeNull()
  })

  it('asks before it throws away an edit, and closes once that is confirmed', async () => {
    const user = userEvent.setup()
    const { container, closes } = renderClosable(obj({ type: 'textbox' }))
    await user.type(screen.getByPlaceholderText(/Text content/), 'Rack A')

    await clickMap(container)
    expect(closes()).toBe(0)

    await user.click(await screen.findByRole('button', { name: 'Discard changes' }))
    expect(closes()).toBe(1)
  })

  it('takes a field typed into and cleared again as untouched', async () => {
    const user = userEvent.setup()
    const { container, closes } = renderClosable(obj({ type: 'line' }))
    const width = screen.getByLabelText('Line width')
    await user.type(width, '4')
    await user.clear(width)

    await clickMap(container)

    expect(closes()).toBe(1)
    expect(screen.queryByRole('button', { name: 'Discard changes' })).toBeNull()
  })

  it('asks the same before Escape, the close button or Cancel discard an edit', async () => {
    const user = userEvent.setup()
    const { closes } = renderClosable(obj({ type: 'textbox' }))
    await user.type(screen.getByPlaceholderText(/Text content/), 'Rack A')

    for (const leave of [
      () => user.keyboard('{Escape}'),
      () => user.click(screen.getByRole('button', { name: 'Close' })),
      () => user.click(screen.getByRole('button', { name: 'Cancel' }))
    ]) {
      await leave()
      await user.click(await screen.findByRole('button', { name: 'Keep editing' }))
      await waitFor(() => expect(screen.queryByRole('button', { name: 'Keep editing' })).toBeNull())
    }

    expect(closes()).toBe(0)
    expect(screen.getByPlaceholderText(/Text content/)).toHaveValue('Rack A')
  })

  it('keeps editing when the question is dismissed with Escape', async () => {
    const user = userEvent.setup()
    const { container, closes } = renderClosable(obj({ type: 'textbox' }))
    await user.type(screen.getByPlaceholderText(/Text content/), 'Rack A')
    await clickMap(container)
    await screen.findByRole('button', { name: 'Discard changes' })

    await user.keyboard('{Escape}')

    expect(closes()).toBe(0)
    expect(screen.getByPlaceholderText(/Text content/)).toHaveValue('Rack A')
  })
})

describe('ObjectPropertiesModal – placement', () => {
  function cardBeside(left: number): HTMLElement {
    const { container } = renderModal(obj({ type: 'host', host_name: 'web01' }), {
      avoid: { left, top: 40, right: left + 32, bottom: 72 }
    })
    return container.querySelector<HTMLElement>('.maps-object-properties-modal__card')!
  }

  it('opens on the right of an object in the left half of the window', () => {
    vi.stubGlobal('innerWidth', 1200)

    expect(cardBeside(100)).toHaveClass('maps-object-properties-modal__card--right')
  })

  it('opens on the left of an object in the right half of the window', () => {
    vi.stubGlobal('innerWidth', 1200)

    expect(cardBeside(900)).toHaveClass('maps-object-properties-modal__card--left')
  })
})

/** A 1200×800 map with the 504-px card's 40-px header at the top center. */
function renderDraggable() {
  const { container } = renderModal(obj({ type: 'host', host_name: 'web01' }))
  const frame = container.querySelector<HTMLElement>('.maps-object-properties-modal')!
  const card = frame.querySelector<HTMLElement>('.maps-object-properties-modal__card')!
  const header = card.querySelector<HTMLElement>('.maps-object-properties-modal__header')!
  const backdrop = frame.querySelector<HTMLElement>('.maps-object-properties-modal__backdrop')!
  vi.spyOn(frame, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 0, 1200, 800))
  vi.spyOn(header, 'getBoundingClientRect').mockReturnValue(new DOMRect(348, 16, 504, 40))
  return { card, header, backdrop }
}

describe('ObjectPropertiesModal – dragging', () => {
  it('moves with its header from where it opened', async () => {
    const user = userEvent.setup()
    const { card, header } = renderDraggable()

    await user.pointer([
      { target: header, coords: { clientX: 500, clientY: 300 }, keys: '[MouseLeft>]' },
      { target: header, coords: { clientX: 700, clientY: 400 } },
      { target: header, keys: '[/MouseLeft]' }
    ])

    expect(card.style.transform).toBe('translate(calc(-50% + 200px), 100px)')
  })

  it('keeps its header on the map, so it can always be pulled back', async () => {
    const user = userEvent.setup()
    const { card, header } = renderDraggable()

    await user.pointer([
      { target: header, coords: { clientX: 500, clientY: 30 }, keys: '[MouseLeft>]' },
      { target: header, coords: { clientX: 2000, clientY: -500 } },
      { target: header, keys: '[/MouseLeft]' }
    ])

    expect(card.style.transform).toBe('translate(calc(-50% + 348px), -16px)')
  })

  it('stays put under a pointer that was released off the header', async () => {
    const user = userEvent.setup()
    const { card, header, backdrop } = renderDraggable()

    await user.pointer([
      { target: header, coords: { clientX: 500, clientY: 300 }, keys: '[MouseLeft>]' },
      { target: backdrop, coords: { clientX: 700, clientY: 400 } },
      { target: backdrop, keys: '[/MouseLeft]' },
      { target: header, coords: { clientX: 600, clientY: 350 } }
    ])

    expect(card.style.transform).toBe('translate(calc(-50% + 0px), 0px)')
  })
})
