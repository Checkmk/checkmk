<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { DashboardFeatures } from '@/dashboard/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FieldComponent from '../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../components/TableForm/FieldDescription.vue'
import TableForm from '../../components/TableForm/TableForm.vue'
import TableFormRow from '../../components/TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface PublicAccessSettingsEmits {
  updateSettings: []
}

interface PublicAccessSettingsProps {
  validationError: TranslatedString[] | null
  availableFeatures: DashboardFeatures
  validate: () => boolean
}

const props = defineProps<PublicAccessSettingsProps>()
const emit = defineEmits<PublicAccessSettingsEmits>()

const hasValidity = defineModel<boolean>('hasValidity', { required: true })
const validUntil = defineModel<Date | null>('validUntil', { required: true, default: null })
const comment = defineModel<string>('comment', { required: true })

const displaySuccessMessage = ref<boolean>(false)

const expiryDate = computed({
  get: (): string => {
    return validUntil.value ? validUntil.value.toISOString().split('T')[0]! : ''
  },

  set: (dateStr: string | undefined): void => {
    if (dateStr) {
      const date = new Date(dateStr)
      validUntil.value = date
    } else {
      validUntil.value = null
    }
  }
})

const handleSave = () => {
  displaySuccessMessage.value = false
  if (props.validate()) {
    emit('updateSettings')
    displaySuccessMessage.value = true
  }
}
</script>

<template>
  <CmkHeading type="h4">{{ _t('Link settings') }}</CmkHeading>
  <ContentSpacer :dimension="4" />
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
        <CmkCheckbox
          :model-value="hasValidity"
          :disabled="props.availableFeatures === DashboardFeatures.RESTRICTED"
          :label="_t('Set expiration date')"
          padding="top"
          @update:model-value="
            (value: boolean) => {
              hasValidity = value
              displaySuccessMessage = false
            }
          "
        />
        <div v-if="hasValidity" class="db-public-access-settings__validity">
          <CmkLabel>{{ _t('Public link expiration date') }}</CmkLabel>
          <ContentSpacer :dimension="4" />
          <CmkInput
            v-model="expiryDate as string"
            type="date"
            :external-errors="validationError || []"
            @update:model-value="displaySuccessMessage = false"
          />
        </div>
      </FieldComponent>
    </TableFormRow>
    <TableFormRow>
      <FieldDescription>{{ _t('Comment') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          v-model="comment as string"
          :placeholder="_t('Internal comment, not visible to viewers')"
          field-size="FILL"
          @update:model-value="displaySuccessMessage = false"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>

  <ContentSpacer />

  <ActionBar align-items="right">
    <ActionButton :label="_t('Save changes')" :action="handleSave" variant="optional" />
  </ActionBar>
</template>

<style scoped>
.db-public-access-settings__validity {
  padding-top: var(--dimension-6);

  /* Subtract the row gap from the TableForm */
  padding-bottom: calc(var(--dimension-6) - var(--spacing-half));
}
</style>
