<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkSlideInDropdownCodeExample.vue?raw'

export const a11yData = [
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

export type OmittedProps = 'modelValue' | 'choices' | 'newTitle' | 'editTitle'
export const panelConfig = {
  label: { type: 'string' as const, title: 'Label', initialState: 'Select an entity' },
  validation: { type: 'string-array' as const, title: 'Validation Errors', initialState: [] },
  inputHint: {
    type: 'string' as const,
    title: 'Input Hint',
    initialState: 'Select an element...'
  },
  allowEditingExistingElements: {
    type: 'boolean' as const,
    title: 'Allow Editing Existing',
    initialState: true
  }
} satisfies PanelConfigFor<typeof CmkSlideInDropdown, OmittedProps>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkSlideInDropdown, {
  type CmkSlideInDropdownChoice
} from '@/components/user-input/CmkSlideInDropdown'

import UclCmkSlideInDropdownDev from './UclCmkSlideInDropdownDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSlideInDropdown, OmittedProps>().createRef(
  panelConfig
)

const selectedId = ref<string | null>(null)

const choices = ref<Array<CmkSlideInDropdownChoice>>([
  { name: 'entity_1', title: untranslated('First Demo Entity') },
  { name: 'entity_2', title: untranslated('Second Demo Entity') }
])

const draftTitle = ref('')
let createdCount = 0

function entityTitle(objectId: string | null): string {
  return choices.value.find((entry) => entry.name === objectId)?.title ?? ''
}

function saveEntity(objectId: string | null, close: () => void) {
  if (objectId === null) {
    createdCount += 1
    const name = `created_entity_${createdCount}`
    choices.value.push({
      name,
      title: untranslated(draftTitle.value.trim() || `New Demo Entity ${createdCount}`)
    })
    selectedId.value = name
  } else {
    const choice = choices.value.find((entry) => entry.name === objectId)
    if (choice && draftTitle.value.trim()) {
      choice.title = untranslated(draftTitle.value.trim())
    }
  }
  draftTitle.value = ''
  close()
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSlideInDropdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkSlideInDropdown
        v-model="selectedId"
        :choices="choices"
        :label="propState.label"
        :input-hint="propState.inputHint"
        :allow-editing-existing-elements="Boolean(propState.allowEditingExistingElements)"
        :validation="propState.validation"
        :new-title="untranslated('New demo entity')"
        :edit-title="untranslated('Edit demo entity')"
      >
        <template #slide-in="{ objectId, close }">
          <div class="ucl-cmk-slide-in-dropdown__demo">
            <CmkParagraph>
              This slide-in is just a generic container: the <code>slide-in</code> slot can render
              any content (a form, a wizard, a preview, …). The simple title form below is only a
              demo.
            </CmkParagraph>
            <div class="ucl-cmk-slide-in-dropdown__demo-field">
              <CmkLabel for="ucl-demo-entity-title">Title</CmkLabel>
              <CmkInput
                id="ucl-demo-entity-title"
                v-model="draftTitle"
                :placeholder="objectId === null ? 'New entity' : entityTitle(objectId)"
                :field-size="'medium'"
                inline
              />
            </div>
            <div class="ucl-cmk-slide-in-dropdown__demo-actions">
              <CmkButtonSubmit @click="() => saveEntity(objectId, close)">Save</CmkButtonSubmit>
              <CmkButtonCancel @click="close">Cancel</CmkButtonCancel>
            </div>
          </div>
        </template>
      </CmkSlideInDropdown>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkSlideInDropdownDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-slide-in-dropdown__demo {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.ucl-cmk-slide-in-dropdown__demo-field {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.ucl-cmk-slide-in-dropdown__demo-actions {
  display: flex;
  gap: var(--spacing);
}
</style>
