<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useTemplateRef } from 'vue'

import CmkDropdown from './CmkDropdown.vue'
import type { ButtonVariants } from './CmkDropdownButton.vue'

const { componentId = null } = defineProps<{
  options: Suggestions
  label: TranslatedString
  componentId?: string | null
  width?: ButtonVariants['width']
  floating?: boolean
}>()

const emit = defineEmits<{
  (event: 'select', value: string): void
}>()

function onSelect(value: string | null): void {
  if (value !== null) {
    emit('select', value)
  }
}

const dropdown = useTemplateRef<InstanceType<typeof CmkDropdown>>('dropdown')

defineExpose({
  /** Move keyboard focus to the button that opens the dropdown. */
  focus: (): void => {
    dropdown.value?.focus()
  }
})
</script>

<template>
  <CmkDropdown
    ref="dropdown"
    :model-value="null"
    :component-id="componentId"
    :options="options"
    :label="label"
    :input-hint="label"
    :width="width"
    :floating="floating"
    @update:model-value="onSelect"
  >
    <template #button-prefix>
      <CmkIcon name="plus" variant="inline" size="small" />
    </template>
  </CmkDropdown>
</template>
