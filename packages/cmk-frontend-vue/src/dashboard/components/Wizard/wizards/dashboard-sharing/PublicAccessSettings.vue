<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getLocalTimeZone, parseDate } from '@internationalized/date'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { renderDate } from 'cmk-ui-library/lib/renderTime'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import FieldComponent from '../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../components/TableForm/FieldDescription.vue'
import TableForm from '../../components/TableForm/TableForm.vue'
import TableFormRow from '../../components/TableForm/TableFormRow.vue'

const { _t } = usei18n()

const expiryDateId = useId()

interface PublicAccessSettingsEmits {
  updateSettings: []
}

interface PublicAccessSettingsProps {
  validationError: TranslatedString[] | null
  dashboardFeatures: DashboardFeatures
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
    return validUntil.value ? renderDate(validUntil.value) : ''
  },

  set: (dateStr: string | undefined): void => {
    if (dateStr) {
      validUntil.value = parseDate(dateStr).toDate(getLocalTimeZone())
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

  <CmkAlert
    v-if="displaySuccessMessage"
    :dismissible="true"
    variant="success"
    :text="_t('Link settings saved.')"
  />

  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Validity') }}</FieldDescription>
      <FieldComponent>
        <CmkCheckbox
          :model-value="hasValidity"
          :disabled="props.dashboardFeatures === DashboardFeatures.RESTRICTED"
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
          <CmkLabel :for="expiryDateId">{{ _t('Public link expiration date') }}</CmkLabel>
          <ContentSpacer :dimension="4" />
          <CmkInput
            :id="expiryDateId"
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
          field-size="fill"
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
