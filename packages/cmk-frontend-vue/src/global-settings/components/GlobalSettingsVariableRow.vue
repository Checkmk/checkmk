<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import FormReadonly from '@/form/FormReadonly.vue'

import GlobalSettingsInlineToggle from './GlobalSettingsInlineToggle.vue'
import GlobalSettingsRow from './GlobalSettingsRow.vue'

const { _t } = usei18n()

const props = defineProps<{ variable: GlobalSettingsVariable }>()

const emit = defineEmits<{ edit: [] }>()

const isBooleanChoice = computed(() => props.variable.spec.type === 'boolean_choice')
</script>

<template>
  <div class="global-settings-variable-row" @click="emit('edit')">
    <GlobalSettingsRow
      :label="untranslated(variable.spec.title)"
      class="global-settings-variable-row__row"
    >
      <div class="global-settings-variable-row__value">
        <GlobalSettingsInlineToggle v-if="isBooleanChoice" :variable="variable" />
        <FormReadonly
          v-else
          :spec="variable.spec"
          :data="variable.value"
          :backend-validation="[]"
        />
        <span v-if="variable.modified" class="global-settings-variable-row__modified">
          {{ _t('(modified)') }}
        </span>
      </div>
    </GlobalSettingsRow>
    <CmkIconButton
      name="edit"
      size="small"
      :title="_t('Edit %{title}', { title: variable.spec.title })"
      class="global-settings-variable-row__edit"
      @click.stop="emit('edit')"
    />
  </div>
</template>

<style scoped>
.global-settings-variable-row {
  --global-settings-row-label-width: 400px;

  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 4px 12px;
  border-radius: 2px;
  cursor: pointer;

  &:hover,
  &:focus-within {
    background: var(--global-settings-row-hover-bg-color);
  }
}

.global-settings-variable-row__row {
  flex: 1 1 auto;
  min-width: 0;
}

.global-settings-variable-row__value {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.global-settings-variable-row__modified {
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.global-settings-variable-row__edit {
  flex-shrink: 0;
  align-self: center;
  opacity: 0;

  .global-settings-variable-row:hover &,
  .global-settings-variable-row:focus-within & {
    opacity: 1;
  }
}
</style>
