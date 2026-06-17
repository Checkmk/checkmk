<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkSlideInDropdown, {
  type CmkSlideInDropdownChoice
} from '@/components/user-input/CmkSlideInDropdown'

defineProps<{ screenshotMode: boolean }>()

const choices: Array<CmkSlideInDropdownChoice> = [
  { name: 'entity_1', title: untranslated('First Demo Entity') },
  { name: 'entity_2', title: untranslated('Second Demo Entity') }
]

const selectedId1 = ref<string | null>('entity_1')
const selectedId2 = ref<string | null>(null)
const selectedIdReadonly = ref<string | null>('entity_2')
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
</template>
