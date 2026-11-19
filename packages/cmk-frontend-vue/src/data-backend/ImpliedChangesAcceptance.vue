<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DataBackendImpliedChangesAcceptance } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const acceptance = defineModel<DataBackendImpliedChangesAcceptance>('acceptance', {
  required: true
})

defineProps<{ validation: string[] }>()

const { _t } = usei18n()

function setAccepted(accepted: boolean): void {
  acceptance.value = { ...acceptance.value, accepted }
}
</script>

<template>
  <div class="data-backend-implied-changes-acceptance">
    <CmkAlert
      variant="warning"
      :text="_t('This also makes these implied changes:')"
      class="data-backend-implied-changes-acceptance__alert"
    />
    <ul class="data-backend-implied-changes-acceptance__changes">
      <li v-for="change in acceptance.implied_changes" :key="change.identity">
        <CmkTag
          v-if="change.new"
          :content="_t('New')"
          color="warning"
          variant="fill"
          size="small"
        />
        {{ change.text }}
      </li>
    </ul>
    <div class="data-backend-implied-changes-acceptance__footer">
      <CmkCheckbox
        :model-value="acceptance.accepted"
        :label="_t('Make these changes')"
        :external-errors="validation"
        @update:model-value="setAccepted"
      />
    </div>
  </div>
</template>

<style scoped>
.data-backend-implied-changes-acceptance {
  display: flex;
  flex-direction: column;
  margin-bottom: var(--spacing);
  border: var(--border-width-1) solid var(--status-border-color-warning);
  border-radius: var(--border-radius);
  overflow: hidden;

  /* Nested to outweigh the alert's own margin and corners. */
  .data-backend-implied-changes-acceptance__alert {
    margin: 0;
    border-radius: 0;
  }
}

.data-backend-implied-changes-acceptance__changes {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin: 0;
  padding: var(--dimension-5) var(--dimension-5) var(--dimension-5) var(--dimension-8);
}

.data-backend-implied-changes-acceptance__footer {
  padding: var(--dimension-5);
  border-top: var(--border-width-1) solid var(--status-border-color-warning);
}
</style>
