<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import FormReadonly from '@/form/FormReadonly.vue'

const { _t } = usei18n()

defineProps<{ variable: GlobalSettingsVariable }>()

const emit = defineEmits<{ edit: [] }>()
</script>

<template>
  <div class="global-settings-variable-row" @click="emit('edit')">
    <div class="global-settings-variable-row__label">
      <span class="global-settings-variable-row__title" :title="variable.spec.title">
        {{ variable.spec.title }}
      </span>
    </div>
    <div class="global-settings-variable-row__value">
      <FormReadonly :spec="variable.spec" :data="variable.value" :backend-validation="[]" />
      <span v-if="variable.modified" class="global-settings-variable-row__modified">
        {{ _t('(modified)') }}
      </span>
    </div>
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
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 2px;
  cursor: pointer;

  &:hover,
  &:focus-within {
    background: var(--ux-theme-6);
  }
}

.global-settings-variable-row__label {
  display: flex;
  flex: 0 1 400px;
  align-items: baseline;
  gap: 4px;
  min-width: 0;

  &::after {
    content: '';
    flex: 1 1 auto;
    min-width: 8px;
    border-bottom: 1px dotted var(--font-color-dimmed);
  }
}

.global-settings-variable-row__title {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.global-settings-variable-row__value {
  display: flex;
  flex: 1 1 auto;
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
