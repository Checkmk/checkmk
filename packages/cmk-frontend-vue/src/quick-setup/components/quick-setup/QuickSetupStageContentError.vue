<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import {
  type DetailedError,
  type QuickSetupStageContent,
  isDetailedError
} from './quick_setup_types'

const { _t } = usei18n()

const details = ref<boolean>(false)
const props = defineProps<{ errors: QuickSetupStageContent['errors'] }>()

const isValidationError = (value: unknown): value is string => {
  return !isDetailedError(value) && (typeof value === 'string' || value instanceof String)
}

const validationErrors = computed<Array<string>>(() => props.errors.filter(isValidationError))
const detailedErrors = computed<Array<DetailedError>>(() => props.errors.filter(isDetailedError))
</script>

<template>
  <CmkAlertBoxDeprecated v-for="error in detailedErrors" :key="error.details" variant="error">
    <div class="qs-stage-content-error__message">
      <CmkHtml :html="error.message" />
    </div>
    <CmkButton v-if="details === false" @click="details = true">{{ _t('Show details') }}</CmkButton>
    <div v-else>
      <pre>{{ error.details }}</pre>
    </div>
  </CmkAlertBoxDeprecated>
  <CmkAlertBoxDeprecated v-if="validationErrors.length > 0" variant="error">
    <div v-for="error in validationErrors" :key="error">
      <div class="qs-stage-content-error__message">
        <CmkHtml :html="error" />
      </div>
    </div>
  </CmkAlertBoxDeprecated>
</template>

<style scoped>
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.qs-stage-content-error__message :deep(pre) {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
