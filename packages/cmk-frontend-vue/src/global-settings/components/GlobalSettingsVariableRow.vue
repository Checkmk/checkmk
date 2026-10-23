<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import FormReadonly from '@/form/FormReadonly.vue'

import { isModified } from '../lib/values'
import GlobalSettingsCollapsibleValue from './GlobalSettingsCollapsibleValue.vue'
import GlobalSettingsHighlightedText from './GlobalSettingsHighlightedText.vue'
import GlobalSettingsInlineToggle from './GlobalSettingsInlineToggle.vue'
import GlobalSettingsRow from './GlobalSettingsRow.vue'

const { _t } = usei18n()

const props = defineProps<{
  variable: GlobalSettingsVariable
  query: string
}>()

const emit = defineEmits<{ edit: [] }>()

const isBooleanChoice = computed(() => props.variable.spec.type === 'boolean_choice')
const modified = computed(() => isModified(props.variable))
const value = computed(() => props.variable.current.value)
</script>

<template>
  <div class="global-settings-variable-row" @click="emit('edit')">
    <CmkIconButton
      name="edit"
      size="small"
      :title="_t('Edit %{title}', { title: variable.spec.title })"
      class="global-settings-variable-row__edit"
      @click.stop="emit('edit')"
    />
    <GlobalSettingsRow
      :label="untranslated(variable.spec.title)"
      class="global-settings-variable-row__row"
    >
      <template #label>
        <GlobalSettingsHighlightedText :text="variable.spec.title" :query="query" />
      </template>
      <template v-if="modified" #label-end>
        <CmkChip as-div size="small" color="others" variant="outline">
          {{ _t('modified') }}
        </CmkChip>
      </template>
      <template #default>
        <GlobalSettingsInlineToggle v-if="isBooleanChoice" :variable="variable" />
        <GlobalSettingsCollapsibleValue v-else>
          <FormReadonly :spec="variable.spec" :data="value" :backend-validation="[]" />
        </GlobalSettingsCollapsibleValue>
      </template>
    </GlobalSettingsRow>
  </div>
</template>

<style scoped>
.global-settings-variable-row {
  --global-settings-row-label-width: 400px;
  --global-settings-collapsible-value-bg-color: var(--ux-theme-3);

  display: flex;
  min-width: min-content;
  align-items: baseline;
  gap: var(--dimension-4);
  padding: var(--dimension-3) var(--dimension-5);
  border-radius: var(--border-radius-half);
  color: var(--global-settings-variable-color);
  cursor: pointer;

  &:hover,
  &:has(:focus-visible) {
    --global-settings-collapsible-value-bg-color: var(--global-settings-row-hover-bg-color);

    background: var(--global-settings-row-hover-bg-color);
  }
}

.global-settings-variable-row__row {
  flex: 1 1 auto;
  min-width: min-content;
}

.global-settings-variable-row__edit {
  flex-shrink: 0;
  opacity: 0;

  .global-settings-variable-row:hover &,
  .global-settings-variable-row:has(:focus-visible) & {
    opacity: 1;
  }
}
</style>
