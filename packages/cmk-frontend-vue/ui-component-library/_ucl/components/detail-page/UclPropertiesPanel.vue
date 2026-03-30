<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ListPropDef, PanelConfig, PanelState } from '@ucl/_ucl/types/prop-panel.ts'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import useId from '@/lib/useId'

import CmkCopy from '@/components/CmkCopy.vue'
import CmkDropdown from '@/components/CmkDropdown'
import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkSwitch from '@/components/CmkSwitch.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

const { config, title = 'Properties' } = defineProps<{ config: PanelConfig; title?: string }>()

const state = defineModel<PanelState>({ required: true })

const uid = useId()

const router = useRouter()
const route = useRoute()

const stringArrayInputs = ref<Record<string, string>>(
  Object.fromEntries(
    Object.entries(config)
      .filter(([, def]) => def.type === 'string-array')
      .map(([key, def]) => [key, formatStringArray(def.initialState as string[])])
  )
)

function formatStringArray(arr: string[]): string {
  return arr.join('\n')
}

function parseStringArray(raw: string): string[] {
  return raw
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

function handleStringArrayInput(key: string, raw: string) {
  stringArrayInputs.value[key] = raw
  state.value[key] = parseStringArray(raw)
}

const url = computed(() => {
  const urlQuery: Record<string, string | string[]> = {}
  for (const [configKey, configValue] of Object.entries(config)) {
    const stateValue = state.value[configKey]
    if (configValue.initialState !== stateValue && stateValue !== undefined) {
      if (typeof stateValue === 'boolean') {
        urlQuery[configKey] = stateValue ? '1' : '0'
      } else if (typeof stateValue === 'number') {
        urlQuery[configKey] = stateValue.toString()
      } else if (Array.isArray(stateValue)) {
        urlQuery[configKey] = stateValue as string[]
      } else {
        urlQuery[configKey] = stateValue
      }
    }
  }

  const permaLink = router.resolve({
    ...route,
    query: urlQuery
  }).href
  return `${window.location.origin}${permaLink}`
})

onMounted(() => {
  for (const [configKey, configValue] of Object.entries(config)) {
    const urlValue = route.query[configKey]
    if (urlValue !== undefined && urlValue !== null) {
      if (configValue.type === 'boolean') {
        state.value[configKey] = urlValue === '1' ? true : false
      } else if (configValue.type === 'number') {
        state.value[configKey] = parseFloat(urlValue as string)
      } else if (configValue.type === 'string-array') {
        const values = (Array.isArray(urlValue) ? urlValue : [urlValue]).filter(
          (v): v is string => v !== null
        )
        state.value[configKey] = values
        stringArrayInputs.value[configKey] = formatStringArray(values)
      } else {
        state.value[configKey] = (Array.isArray(urlValue) ? urlValue[0] : urlValue) ?? ''
      }
    }
  }
})
</script>

<template>
  <div class="ucl-properties-panel__properties-panel">
    <CmkHeading type="h4">{{ title }}</CmkHeading>

    <div class="ucl-properties-panel__copy">
      <CmkCopy :text="url">
        <CmkIconButton name="copied" size="medium" title="Copy permalink" />
      </CmkCopy>
    </div>

    <CmkSpace size="small" />

    <div
      v-for="[key, def] in Object.entries(config)"
      :key="key"
      class="ucl-properties-panel__prop-control"
    >
      <div class="ucl-properties-panel__label-container">
        <CmkLabel :for="`${uid}-${key}`">{{ def.title }}</CmkLabel>
        <CmkSpace v-if="def.help" size="small" />
        <CmkHelpText v-if="def.help" :help="def.help" />
      </div>
      <CmkSwitch
        v-if="def.type === 'boolean'"
        :id="`${uid}-${key}`"
        :data="state[key] as boolean"
        @update:data="state[key] = $event"
      />
      <CmkInput
        v-else-if="def.type === 'string'"
        :id="`${uid}-${key}`"
        :model-value="state[key] as string"
        @update:model-value="state[key] = $event ?? ''"
      />
      <CmkInput
        v-else-if="def.type === 'number'"
        :id="`${uid}-${key}`"
        type="number"
        :model-value="state[key] as number"
        @update:model-value="state[key] = $event ?? 0"
      />
      <textarea
        v-else-if="def.type === 'multiline-string'"
        :id="`${uid}-${key}`"
        rows="3"
        class="ucl-properties-panel__textarea"
        :value="state[key] as string"
        @input="state[key] = ($event.target as HTMLTextAreaElement).value"
      ></textarea>
      <CmkDropdown
        v-else-if="def.type === 'list'"
        :component-id="`${uid}-${key}`"
        :label="def.title"
        :options="{ type: 'fixed', suggestions: (def as ListPropDef).options }"
        :selected-option="state[key] as string"
        @update:selected-option="$event !== null && (state[key] = $event)"
      />
      <textarea
        v-else-if="def.type === 'string-array'"
        :id="`${uid}-${key}`"
        rows="3"
        class="ucl-properties-panel__textarea"
        :value="stringArrayInputs[key] ?? ''"
        @input="handleStringArrayInput(key, ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </div>
  </div>
</template>

<style scoped>
.ucl-properties-panel__properties-panel {
  border: 1px solid var(--ucl-elements-border-color);
  border-radius: 4px;
  padding: 16px;
  position: relative;
}

.ucl-properties-panel__copy {
  position: absolute;
  right: 16px;
  top: 14px;
}

.ucl-properties-panel__prop-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
}

.ucl-properties-panel__textarea {
  flex: 1;
}
</style>
