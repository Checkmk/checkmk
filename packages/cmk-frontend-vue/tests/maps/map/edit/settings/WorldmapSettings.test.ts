/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import WorldmapSettings from '@/maps/map/edit/settings/components/WorldmapSettings.vue'
import { type SettingsForm, formFromMap } from '@/maps/map/edit/settings/settingsForm'

import { aListedMap, newMapView } from '../../../support/fixtures'
import { fakeMapsServices, provideServices } from '../../../support/services'

describe('WorldmapSettings', () => {
  // The world map's empty hint opens the settings on this option.
  it('puts the cursor on the automatic placement when opened for it', async () => {
    const map = aListedMap({ view_type: 'worldmap', view: newMapView('worldmap') })
    const form = formFromMap(map, null)
    // Shown after the first render, as the dialog does: render() moves what it
    // mounts, which would drop a focus taken on mount.
    const shown = ref(false)
    const host = defineComponent({
      setup: () => () =>
        shown.value
          ? h(WorldmapSettings, { form, saveAttempted: false, initialFocus: 'automap_source' })
          : null
    })
    render(host, provideServices(fakeMapsServices()))
    shown.value = true

    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Automatic object placement' })).toHaveFocus()
    )
  })

  it('marks the group as missing once a save was tried without one', () => {
    const map = aListedMap({ view_type: 'worldmap', view: newMapView('worldmap') })
    const form = { ...formFromMap(map, null), worldmap_auto_source: 'hostgroup' as const }
    render(WorldmapSettings, {
      props: { form, saveAttempted: true },
      ...provideServices(fakeMapsServices())
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Pick a group to discover hosts from.')
    expect(screen.getByRole('combobox', { name: 'Group name' })).toHaveAttribute(
      'aria-invalid',
      'true'
    )
  })

  describe('the group picked for automatic placement', () => {
    function renderWithGroup() {
      const map = aListedMap({ view_type: 'worldmap', view: newMapView('worldmap') })
      const form = ref<SettingsForm>({
        ...formFromMap(map, null),
        worldmap_auto_source: 'hostgroup',
        worldmap_auto_filter_value: 'berlin'
      })
      render(WorldmapSettings, {
        props: {
          form: form.value,
          'onUpdate:form': (next: SettingsForm) => (form.value = next),
          saveAttempted: false
        },
        ...provideServices(fakeMapsServices())
      })
      return form
    }

    it('survives a detour over a choice without a group', async () => {
      const form = renderWithGroup()
      form.value.worldmap_auto_source = 'all_hosts'
      await nextTick()
      form.value.worldmap_auto_source = 'hostgroup'
      await nextTick()

      expect(form.value.worldmap_auto_filter_value).toBe('berlin')
    })

    it('is dropped for the other kind of group', async () => {
      const form = renderWithGroup()
      form.value.worldmap_auto_source = 'all_hosts'
      await nextTick()
      form.value.worldmap_auto_source = 'servicegroup'
      await nextTick()

      expect(form.value.worldmap_auto_filter_value).toBe('')
    })
  })
})
