<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import { ref } from 'vue'

import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown'

defineProps<{ screenshotMode: boolean }>()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DEMO_ENTITY_TYPE = 'ucl_demo_entity' as any as ConfigEntityType

const selectedId1 = ref<string | null>('entity_1')
const selectedId2 = ref<string | null>(null)
const selectedIdReadonly = ref<string | null>('entity_2')
</script>

<template>
  <h2>Pre-selected entity</h2>
  <CmkConfigurationEntityDropdown
    v-model="selectedId1"
    :config-entity-type="DEMO_ENTITY_TYPE"
    config-entity-type-specifier="all"
    label="Demo entity"
    :allow-editing-existing-elements="true"
  />
  <div style="margin-top: 0.5em">Selected: {{ selectedId1 ?? '(none)' }}</div>

  <h2>Empty selection</h2>
  <CmkConfigurationEntityDropdown
    v-model="selectedId2"
    :config-entity-type="DEMO_ENTITY_TYPE"
    config-entity-type-specifier="all"
    label="Demo entity"
    :allow-editing-existing-elements="true"
  />
  <div style="margin-top: 0.5em">Selected: {{ selectedId2 ?? '(none)' }}</div>

  <h2>Editing disabled</h2>
  <CmkConfigurationEntityDropdown
    v-model="selectedIdReadonly"
    :config-entity-type="DEMO_ENTITY_TYPE"
    config-entity-type-specifier="all"
    label="Demo entity"
    :allow-editing-existing-elements="false"
  />
  <div style="margin-top: 0.5em">Selected: {{ selectedIdReadonly ?? '(none)' }}</div>
</template>
