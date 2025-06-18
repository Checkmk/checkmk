<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import usei18n from '@/lib/i18n'
import {
  type QuickSetupStageContent,
  type DetailedError,
  isDetailedError
} from './quick_setup_types'
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkHtml from '@/components/CmkHtml.vue'

const { t } = usei18n('quick-setup-stage-content-error')

const details = ref<boolean>(false)
const props = defineProps<{ errors: QuickSetupStageContent['errors'] }>()

const isValidationError = (value: unknown): value is string => {
  return !isDetailedError(value) && (typeof value === 'string' || value instanceof String)
}

const validationErrors = computed<Array<string>>(() => props.errors.filter(isValidationError))
const detailedErrors = computed<Array<DetailedError>>(() => props.errors.filter(isDetailedError))
</script>

<template>
  <CmkAlertBox v-for="error in detailedErrors" :key="error.details" variant="error">
    <CmkHtml :html="error.message" />
    <CmkButton v-if="details === false" @click="details = true">{{
      t('show-details', 'Show details')
    }}</CmkButton>
    <div v-else>
      <pre>{{ error.details }}</pre>
    </div>
  </CmkAlertBox>
  <CmkAlertBox v-if="validationErrors.length > 0" variant="error">
    <div v-for="error in validationErrors" :key="error">
      <CmkHtml :html="error" />
    </div>
  </CmkAlertBox>
</template>
