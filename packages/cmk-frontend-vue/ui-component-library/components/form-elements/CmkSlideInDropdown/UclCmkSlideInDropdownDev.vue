<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideInDropdown, {
  type CmkSlideInDropdownChoice
} from 'cmk-ui-library/components/user-input/CmkSlideInDropdown'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

const props = defineProps<{ screenshotMode: boolean }>()

const choices: Array<CmkSlideInDropdownChoice> = [
  { name: 'entity_1', title: untranslated('First Demo Entity') },
  { name: 'entity_2', title: untranslated('Second Demo Entity') }
]

const selectedId1 = ref<string | null>('entity_1')
const selectedId2 = ref<string | null>(null)
const selectedIdReadonly = ref<string | null>('entity_2')
const selectedIdAsync = ref<string | null>(null)

const asyncChoices = ref<Array<CmkSlideInDropdownChoice>>([])
const asyncLoading = ref<boolean>(true)

function fetchAsyncChoices() {
  asyncChoices.value = []
  asyncLoading.value = true
  setTimeout(() => {
    asyncChoices.value = [...choices]
    asyncLoading.value = false
  }, 2000)
}

// In screenshot mode the fetch never resolves, keeping the loading state stable.
if (!props.screenshotMode) {
  fetchAsyncChoices()
}
</script>

<template>
  <h2>Pre-selected entity</h2>
  <CmkSlideInDropdown
    v-model="selectedId1"
    :choices="choices"
    label="Demo entity"
    :allow-editing-existing-elements="true"
    :new-title="untranslated('New demo entity')"
    :edit-title="untranslated('Edit demo entity')"
  >
    <template #slide-in="{ objectId, close }">
      <div>
        <p>Slide-in body for {{ objectId ?? 'a new element' }}.</p>
        <button @click="close">Close</button>
      </div>
    </template>
  </CmkSlideInDropdown>
  <div style="margin-top: 0.5em">Selected: {{ selectedId1 ?? '(none)' }}</div>

  <h2>Empty selection</h2>
  <CmkSlideInDropdown
    v-model="selectedId2"
    :choices="choices"
    label="Demo entity"
    :allow-editing-existing-elements="true"
    :new-title="untranslated('New demo entity')"
    :edit-title="untranslated('Edit demo entity')"
  >
    <template #slide-in="{ objectId, close }">
      <div>
        <p>Slide-in body for {{ objectId ?? 'a new element' }}.</p>
        <button @click="close">Close</button>
      </div>
    </template>
  </CmkSlideInDropdown>
  <div style="margin-top: 0.5em">Selected: {{ selectedId2 ?? '(none)' }}</div>

  <h2>Editing disabled</h2>
  <CmkSlideInDropdown
    v-model="selectedIdReadonly"
    :choices="choices"
    label="Demo entity"
    :allow-editing-existing-elements="false"
    :new-title="untranslated('New demo entity')"
    :edit-title="untranslated('Edit demo entity')"
  >
    <template #slide-in="{ objectId, close }">
      <div>
        <p>Slide-in body for {{ objectId ?? 'a new element' }}.</p>
        <button @click="close">Close</button>
      </div>
    </template>
  </CmkSlideInDropdown>
  <div style="margin-top: 0.5em">Selected: {{ selectedIdReadonly ?? '(none)' }}</div>

  <h2>Async choices (loading)</h2>
  <CmkSlideInDropdown
    v-model="selectedIdAsync"
    :choices="asyncChoices"
    :loading="asyncLoading"
    label="Demo entity"
    :allow-editing-existing-elements="true"
    :new-title="untranslated('New demo entity')"
    :edit-title="untranslated('Edit demo entity')"
  >
    <template #slide-in="{ objectId, close }">
      <div>
        <p>Slide-in body for {{ objectId ?? 'a new element' }}.</p>
        <button @click="close">Close</button>
      </div>
    </template>
  </CmkSlideInDropdown>
  <div style="margin-top: 0.5em">
    Selected: {{ selectedIdAsync ?? '(none)' }}
    <button style="margin-left: 0.5em" @click="fetchAsyncChoices">Refetch (2 s)</button>
  </div>
</template>
