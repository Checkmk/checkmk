/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type PropType, defineComponent, h } from 'vue'

import type { MapsCapabilities } from '@/maps/api/ticket'
import MapSettingsForm from '@/maps/map/edit/settings/MapSettingsForm.vue'
import type { MapConfig, MapRead } from '@/maps/types/api'

import { aMap, newMapView } from '../../../support/fixtures'
import { aTicket, fakeMapsServices, provideServices } from '../../../support/services'

// The map metadata FormSpec is a whole vendored renderer; this form only
// orchestrates it (wires v-model:data, gates Save on dirtiness, forwards the
// edited bag to the store on save). Replace it with a tiny stub that exposes a
// single "edit" affordance so the tests drive the modal's own logic, not the
// FormSpec dispatcher.
vi.mock('@/form/FormEdit.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      name: 'FormEditStub',
      props: {
        data: { type: Object as PropType<Record<string, unknown>>, required: true },
        spec: { type: Object as PropType<Record<string, unknown>>, required: true },
        backendValidation: { type: Array as PropType<unknown[]>, default: () => [] }
      },
      emits: ['update:data'],
      setup(props, { emit }) {
        return () =>
          h(
            'button',
            {
              type: 'button',
              onClick: () => emit('update:data', { ...props.data, alias: 'Edited alias' })
            },
            'stub-edit-alias'
          )
      }
    })
  }
})

// The modal saves and deletes through the map service; spying on it makes both
// observable without a network round-trip.
let services: ReturnType<typeof fakeMapsServices>
let saveMapMetadata: ReturnType<typeof vi.spyOn>
let deleteMap: ReturnType<typeof vi.spyOn>

const capabilities: MapsCapabilities = {
  may_edit: true,
  configure: true,
  see_all: true,
  folder_see_all: true,
  contact_groups: [],
  publish_all: true,
  publish_to_groups: true,
  publish_to_foreign_groups: false,
  publish_to_sites: false,
  all_contact_groups: [{ id: 'linux-admins', alias: 'Linux admins' }],
  all_sites: [],
  commands: []
}

const savedMap: MapConfig = aMap({
  name: 'net-overview',
  alias: 'Network Overview',
  icon_size: null,
  connection_id: 'local',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: newMapView('static'),
  objects: []
})

// Both confirmation popups render through reka-ui's Dialog, whose missing-title
// a11y warning trips the fail-on-console harness. Swap them for stubs that keep
// the only contract this modal relies on — surface a confirm affordance while
// open and re-emit — so the discard/delete flows stay observable.
//
// The stub renders inline (not through a portal), so the open slide-in's
// focus-trap marks it aria-hidden; the tests reach these buttons with
// ``{ hidden: true }``.
const unsavedChangesDialogStub = defineComponent({
  name: 'MapsUnsavedChangesDialog',
  props: { open: { type: Boolean, default: false } },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () =>
      props.open
        ? h('div', [
            h('button', { type: 'button', onClick: () => emit('confirm') }, 'Discard changes'),
            h('button', { type: 'button', onClick: () => emit('cancel') }, 'Stay on page')
          ])
        : h('div')
  }
})

const confirmDialogStub = defineComponent({
  name: 'MapsConfirmDialog',
  props: { open: { type: Boolean, default: false } },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () =>
      props.open
        ? h('div', [
            h('button', { type: 'button', onClick: () => emit('confirm') }, 'Confirm delete')
          ])
        : h('div')
  }
})

// The header carries its own close "X" (aria-label "Close") alongside the footer
// Close button, so role+name is ambiguous — reach the footer action by its text.
function footerButton(label: string): HTMLElement {
  const button = screen.getByText(label).closest('button')
  if (!button) {
    throw new Error(`No footer button labelled "${label}"`)
  }
  return button
}

function makeMap(overrides: Partial<MapRead> = {}): MapRead {
  return {
    name: 'net-overview',
    alias: 'Network Overview',
    icon_size: null,
    connection_id: 'local',
    view_type: 'static',
    view: newMapView('static'),
    object_count: 0,
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    can_delete: true,
    public: false,
    ...overrides
  }
}

function renderModal(map: MapRead = makeMap()) {
  const { global: provided } = provideServices(services)
  return render(MapSettingsForm, {
    props: { map },
    global: {
      ...provided,
      stubs: {
        MapsConfirmDialog: confirmDialogStub,
        MapsUnsavedChangesDialog: unsavedChangesDialogStub
      }
    }
  })
}

// The metadata FormSpec renders on mount (after the async schema resolves); wait
// for the stub so the modal has finished settling its initial (clean) snapshot.
async function renderReady(map?: MapRead) {
  const result = renderModal(map)
  await screen.findByRole('button', { name: 'stub-edit-alias' })
  return result
}

// Flip the modal dirty by having the FormEdit stub emit an edited data bag.
async function editForm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'stub-edit-alias' }))
}

beforeEach(async () => {
  vi.clearAllMocks()
  services = fakeMapsServices({}, aTicket({ capabilities }))
  saveMapMetadata = vi.spyOn(services.maps, 'saveMapMetadata').mockResolvedValue(savedMap)
  deleteMap = vi.spyOn(services.maps, 'deleteMap').mockResolvedValue(undefined)
  vi.mocked(services.apis.formSchemas.fetch).mockResolvedValue({
    schema: { type: 'dictionary', elements: [] },
    data: {}
  })
  // The server translates the form's values into stored ones; here that is the
  // identity, so the tests observe the bag the form produced.
  vi.mocked(services.apis.formSchemas.parse).mockImplementation((_spec, values) =>
    Promise.resolve({ data: values })
  )
  await services.auth.init()
})

afterEach(() => {})

describe('MapSettingsForm – rendering', () => {
  it('titles the dialog with the map alias and name', async () => {
    await renderReady()
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: /Map settings — Network Overview · net-overview/
      })
    ).toBeInTheDocument()
  })

  it('offers Close and Save, with Save disabled while there are no changes', async () => {
    await renderReady()
    expect(footerButton('Close')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  it('reveals a Reset button only once the form is dirty', async () => {
    const user = userEvent.setup()
    await renderReady()
    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
    await editForm(user)
    expect(await screen.findByRole('button', { name: 'Reset' })).toBeInTheDocument()
  })
})

describe('MapSettingsForm – delete affordance', () => {
  it('shows the Delete button when the map is deletable', async () => {
    await renderReady(makeMap({ can_delete: true }))
    expect(screen.getByRole('button', { name: 'Delete map…' })).toBeInTheDocument()
  })

  it('hides the Delete button when the map cannot be deleted', async () => {
    await renderReady(makeMap({ can_delete: false }))
    expect(screen.queryByRole('button', { name: 'Delete map…' })).toBeNull()
  })
})

describe('MapSettingsForm – close/cancel', () => {
  it('emits close immediately when there are no unsaved changes', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderReady()
    await user.click(footerButton('Close'))
    await waitFor(() => expect(emitted().close).toHaveLength(1))
  })

  it('opens a discard dialog instead of closing when there are unsaved changes', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderReady()
    await editForm(user)

    await user.click(footerButton('Close'))
    // The discard confirmation appears and no close has leaked out yet.
    const discard = await screen.findByRole('button', { name: 'Discard changes', hidden: true })
    expect(emitted().close).toBeUndefined()

    // The confirmation is inside the slide-in's focus-trap region (pointer-events
    // are disabled there), so dispatch the click directly rather than via userEvent.
    await fireEvent.click(discard)
    await waitFor(() => expect(emitted().close).toHaveLength(1))
  })
})

describe('MapSettingsForm – save', () => {
  it('enables Save on edit and persists the edited data, then emits updated', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderReady()

    await editForm(user)
    const save = screen.getByRole('button', { name: 'Save' })
    await waitFor(() => expect(save).toBeEnabled())

    await user.click(save)

    await waitFor(() => expect(saveMapMetadata).toHaveBeenCalledTimes(1))
    expect(saveMapMetadata).toHaveBeenCalledWith(
      'net-overview',
      expect.objectContaining({ alias: 'Edited alias' }),
      // The envelope: a private map, linked from the Monitor menu.
      { public: false, hide_in_monitor_menu: false }
    )
    expect(emitted().updated).toHaveLength(1)
  })

  it('persists the values the form spec translated the form bag into', async () => {
    // A single-choice field carries an opaque id in the form and its stored
    // name only after the form spec translated it, so the dialog has to save
    // what came back rather than what it holds.
    vi.mocked(services.apis.formSchemas.parse).mockResolvedValue({
      data: { alias: 'Edited alias', render_mode: 'nagvis_classic' }
    })
    const user = userEvent.setup()
    await renderReady()

    await editForm(user)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(saveMapMetadata).toHaveBeenCalledTimes(1))
    expect(saveMapMetadata).toHaveBeenCalledWith(
      'net-overview',
      expect.objectContaining({ render_mode: 'nagvis_classic' }),
      { public: false, hide_in_monitor_menu: false }
    )
  })

  it('reports a refused value on its own field instead of saving', async () => {
    vi.mocked(services.apis.formSchemas.parse).mockResolvedValue({
      validation: [
        { location: ['render_mode'], message: 'Invalid choice', replacement_value: null }
      ]
    })
    const user = userEvent.setup()
    await renderReady()

    await editForm(user)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(screen.getByText(/Please correct the highlighted fields/)).toBeInTheDocument()
    )
    expect(saveMapMetadata).not.toHaveBeenCalled()
  })

  it('saves the problems filter the settings show', async () => {
    const radar = { type: 'radar', filter: 'all_services', filter_value: '' } as const
    const user = userEvent.setup()
    await renderReady(makeMap({ view_type: 'radar', view: { ...radar, problems_only: true } }))

    const problemsOnly = screen.getByRole('switch')
    expect(problemsOnly).toHaveAttribute('aria-checked', 'true')
    await user.click(problemsOnly)
    await waitFor(() => expect(footerButton('Save')).toBeEnabled())
    await user.click(footerButton('Save'))

    await waitFor(() => expect(saveMapMetadata).toHaveBeenCalledTimes(1))
    expect(saveMapMetadata).toHaveBeenCalledWith(
      'net-overview',
      expect.objectContaining({ view: { ...radar, problems_only: false } }),
      { public: false, hide_in_monitor_menu: false }
    )
  })
})

describe('MapSettingsForm – delete flow', () => {
  it('deletes the map on confirmation and emits updated + close', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderReady()

    await user.click(screen.getByRole('button', { name: 'Delete map…' }))
    // Confirmation lives in the focus-trap region; dispatch the click directly.
    await fireEvent.click(
      await screen.findByRole('button', { name: 'Confirm delete', hidden: true })
    )

    await waitFor(() => expect(deleteMap).toHaveBeenCalledWith('net-overview'))
    await waitFor(() => expect(emitted().updated).toHaveLength(1))
    expect(emitted().close).toHaveLength(1)
  })
})

describe('MapSettingsForm – tabs', () => {
  it('switches to the Access tab to reveal the visibility controls', async () => {
    const user = userEvent.setup()
    await renderReady()

    expect(screen.queryByText(/Control who can see this map/)).toBeNull()

    await user.click(screen.getByRole('tab', { name: 'Access' }))

    expect(await screen.findByText(/Control who can see this map/)).toBeInTheDocument()
    expect(screen.getByText('Visibility')).toBeInTheDocument()
  })

  it('saves the Monitor menu choice made on the Access tab', async () => {
    const user = userEvent.setup()
    await renderReady(makeMap({ hide_in_monitor_menu: true }))

    await user.click(screen.getByRole('tab', { name: 'Access' }))
    const hide = await screen.findByRole('checkbox', { name: 'Hide this map in the Monitor menu' })
    expect(hide).toBeChecked()
    await user.click(hide)
    await waitFor(() => expect(footerButton('Save')).toBeEnabled())
    await user.click(footerButton('Save'))

    await waitFor(() => expect(saveMapMetadata).toHaveBeenCalledTimes(1))
    expect(saveMapMetadata).toHaveBeenCalledWith('net-overview', expect.anything(), {
      public: false,
      hide_in_monitor_menu: false
    })
  })
})
