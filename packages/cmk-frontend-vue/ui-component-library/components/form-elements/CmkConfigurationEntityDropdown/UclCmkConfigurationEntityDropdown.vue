<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type PanelConfig,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { String as FormSpecString } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { setupWorker } from 'msw/browser'
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'

import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import UclCmkConfigurationEntityDropdownDev from './UclCmkConfigurationEntityDropdownDev.vue'

initializeComponentRegistry()

defineProps<{ screenshotMode: boolean }>()

// Dummy entity type used only in this UCL demo — not a real backend type.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DEMO_ENTITY_TYPE = 'ucl_demo_entity' as any as ConfigEntityType

const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the dropdown.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the dropdown from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Opens the dropdown or selects the focused option.'
  },
  {
    keys: ['ArrowDown'],
    description: 'Opens the dropdown or moves focus to the next option.'
  },
  {
    keys: ['ArrowUp'],
    description: 'Moves focus to the previous option.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the dropdown without changing the selection.'
  }
]

const panelConfig = {
  allowEditing: { type: 'boolean', title: 'Allow Editing Existing', initialState: true }
} satisfies PanelConfig

const propState = ref(createPanelState(panelConfig))

const selectedId = ref<string | null>(null)

// ----- Mock data -----

const mockEntities = [
  { id: 'entity_1', title: 'First Demo Entity' },
  { id: 'entity_2', title: 'Second Demo Entity' }
]

const minimalSchema: FormSpecString = {
  type: 'string',
  title: 'Name',
  help: '',
  validators: [],
  label: null,
  input_hint: null,
  autocompleter: null,
  field_size: 'MEDIUM'
}

// ----- MSW setup -----

let worker: ReturnType<typeof setupWorker> | null = null
const mockLoaded = ref(false)

onBeforeMount(async () => {
  worker = setupWorker(
    // Get schema: /domain-types/form_spec/collections/{entityType}
    http.get(new RegExp('/domain-types/form_spec/collections/'), () => {
      return HttpResponse.json({
        extensions: { schema: minimalSchema, default_values: '' }
      })
    }),
    // List entities: /domain-types/{entityType}/collections/{specifier}
    http.get(new RegExp('/domain-types/(?!form_spec)[^/]+/collections/'), () => {
      return HttpResponse.json({
        value: mockEntities.map((e) => ({ id: e.id, title: e.title }))
      })
    }),
    // Get entity data for editing: /objects/{entityType}/{entityId}
    http.get(new RegExp('/objects/[^/]+/[^/]+$'), ({ request }) => {
      const url = new URL(request.url)
      const entityId = url.pathname.split('/').at(-1)
      const entity = mockEntities.find((e) => e.id === entityId)
      return HttpResponse.json({ extensions: entity?.title ?? '' })
    }),
    // Create entity
    http.post(
      new RegExp('/domain-types/configuration_entity/collections/all'),
      async ({ request }) => {
        const body = (await request.json()) as { data: unknown }
        const newId = `entity_${Date.now()}`
        const title = typeof body?.data === 'string' ? body.data : `New entity ${newId}`
        mockEntities.push({ id: newId, title })
        return HttpResponse.json({ id: newId, title })
      }
    ),
    // Update entity
    http.put(
      new RegExp('/domain-types/configuration_entity/actions/edit-single-entity/invoke'),
      async ({ request }) => {
        const body = (await request.json()) as { entity_id: string; data: unknown }
        const entity = mockEntities.find((e) => e.id === body?.entity_id)
        const newTitle =
          typeof body?.data === 'string' ? body.data : (entity?.title ?? body?.entity_id)
        if (entity) {
          entity.title = newTitle
        }
        return HttpResponse.json({ id: body?.entity_id, title: newTitle })
      }
    )
  )
  await worker.start({ onUnhandledRequest: 'bypass' })
  mockLoaded.value = true
})

onBeforeUnmount(() => {
  worker?.stop()
})

const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown'

const selectedId = ref<string | null>(null)
<${'/'} script>

<template>
  <CmkConfigurationEntityDropdown
    v-model="selectedId"
    config-entity-type="notification_parameter"
    config-entity-type-specifier="slack"
    label="Notification parameter"
    :allow-editing-existing-elements="true"
  />
</template>`
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkConfigurationEntityDropdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div v-if="mockLoaded">
        <CmkConfigurationEntityDropdown
          v-model="selectedId"
          :config-entity-type="DEMO_ENTITY_TYPE"
          config-entity-type-specifier="all"
          label="Demo entity"
          :allow-editing-existing-elements="Boolean(propState.allowEditing)"
        />
      </div>
      <div v-else>Initializing...</div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkConfigurationEntityDropdownDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
