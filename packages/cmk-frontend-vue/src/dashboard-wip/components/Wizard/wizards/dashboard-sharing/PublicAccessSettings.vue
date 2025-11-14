<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FieldComponent from '../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../components/TableForm/FieldDescription.vue'
import TableForm from '../../components/TableForm/TableForm.vue'
import TableFormRow from '../../components/TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface PublicAccessSettingsEmits {
  updateSettings: [() => void]
}

const emit = defineEmits<PublicAccessSettingsEmits>()

const validUntil = defineModel<Date>('validUntil', { required: true })
const comment = defineModel<string>('comment', { required: true })
const displaySuccessMessage = ref<boolean>(false)
const dateValidationError = ref<TranslatedString[]>([])

watch([comment, validUntil], () => {
  displaySuccessMessage.value = false
})

const expiryDate = computed({
  get: (): string => {
    return validUntil.value ? validUntil.value.toISOString().split('T')[0]! : ''
  },

  set: (dateStr: string | undefined): void => {
    const date = new Date(dateStr ? dateStr : '')
    date.setHours(23, 59, 59, 999)

    const targetDate = new Date()

    if (date < targetDate) {
      dateValidationError.value = [_t('Expiration date cannot be in the past.')]
      return
    }

    targetDate.setFullYear(targetDate.getFullYear() + 2)
    if (date > targetDate) {
      dateValidationError.value = [_t('Expiration date cannot be more than 2 years in the future.')]
      return
    }

    dateValidationError.value = []
    validUntil.value = date
  }
})
</script>

<template>
  <CmkHeading type="h3">{{ _t('Link settings') }}</CmkHeading>
  <CmkLabel>{{
    _t('Choose how the dashboard appears, set an expiration date or add a comment')
  }}</CmkLabel>

  <ContentSpacer />

  <CmkAlertBox v-if="displaySuccessMessage" variant="success">{{
    _t('Link settings saved.')
  }}</CmkAlertBox>

  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Validity') }}</FieldDescription>
      <FieldComponent>
        <CmkCheckbox :model-value="true" :label="_t('Set expiration date')" />
        <div v-if="true" class="db-public-access-settings__validity">
          <div>
            <CmkLabel>{{ _t('Public link expiration date') }}</CmkLabel>
          </div>
          <div>
            <CmkInput
              v-model="expiryDate as string"
              type="date"
              :external-errors="dateValidationError"
            />
          </div>
        </div>
      </FieldComponent>
    </TableFormRow>
    <TableFormRow>
      <FieldDescription>{{ _t('Comment') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          v-model="comment as string"
          :placeholder="_t('Internal comment, not visible to viewers')"
          field-size="MEDIUM"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>

  <ContentSpacer />

  <ActionBar align-items="right">
    <ActionButton
      :label="_t('Save changes')"
      :action="
        () =>
          emit('updateSettings', () => {
            displaySuccessMessage = true
          })
      "
      variant="optional"
    />
  </ActionBar>
</template>

<style scoped>
.db-public-access-settings__validity {
  padding-top: var(--dimension-4);
  padding-bottom: var(--dimension-4);
}
</style>
