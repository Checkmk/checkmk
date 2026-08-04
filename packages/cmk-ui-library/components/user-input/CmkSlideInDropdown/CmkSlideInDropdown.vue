<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkInlineButton from 'cmk-ui-library/components/user-input/CmkInlineButton.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

export interface CmkSlideInDropdownChoice {
  name: string
  title: TranslatedString
  /** Hide the edit button while this choice is selected. */
  hideEdit?: boolean
}

const { _t } = usei18n()

const props = defineProps<{
  choices: Array<CmkSlideInDropdownChoice>
  label: string
  inputHint?: string
  validation?: Array<string>
  allowEditingExistingElements?: boolean
  loading?: boolean
  /** Title of the slide-in when creating a new element. */
  newTitle: TranslatedString
  /** Title of the slide-in when editing an existing element. */
  editTitle: TranslatedString
}>()

type OptionId = string

const selectedObjectId = defineModel<OptionId | null>({ required: true })

const slideInObjectId = ref<OptionId | null>(null)
const slideInOpen = ref<boolean>(false)

const resolvedI18n = computed(() => ({
  noSelection: props.inputHint ?? _t('Please select an element'),
  noObjects: _t('No options available'),
  loading: _t('Loading…'),
  edit: _t('Edit'),
  create: _t('Create new')
}))

const editHidden = computed(
  () => props.choices.find((choice) => choice.name === selectedObjectId.value)?.hideEdit === true
)

function closeSlideIn() {
  slideInOpen.value = false
}

function openSlideIn(objectId: OptionId | null) {
  slideInObjectId.value = objectId
  slideInOpen.value = true
  error.value = null
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary, error } = useCmkErrorBoundary()
</script>

<template>
  <div>
    <div class="cmk-slide-in-dropdown__controls">
      <CmkDropdown
        v-model="selectedObjectId"
        :options="{
          type: choices.length > 5 ? 'filtered' : 'fixed',
          suggestions: choices
        }"
        :input-hint="untranslated(resolvedI18n.noSelection)"
        :no-elements-text="untranslated(loading ? resolvedI18n.loading : resolvedI18n.noObjects)"
        :no-results-hint="untranslated(loading ? resolvedI18n.loading : '')"
        :label="untranslated(label)"
        required
      />
      <CmkInlineButton
        v-if="allowEditingExistingElements && !editHidden"
        v-show="selectedObjectId !== null"
        icon="edit"
        @click="openSlideIn(selectedObjectId)"
      >
        {{ resolvedI18n.edit }}
      </CmkInlineButton>
      <CmkInlineButton @click="openSlideIn(null)">
        {{ resolvedI18n.create }}
      </CmkInlineButton>
    </div>

    <CmkSlideInDialog
      :open="slideInOpen"
      :header="{
        title: slideInObjectId === null ? newTitle : editTitle,
        closeButton: true
      }"
      @close="closeSlideIn"
    >
      <CmkErrorBoundary>
        <slot name="slide-in" :object-id="slideInObjectId" :close="closeSlideIn" />
      </CmkErrorBoundary>
    </CmkSlideInDialog>

    <CmkInlineValidation :validation="props.validation" />
  </div>
</template>

<style scoped>
.cmk-slide-in-dropdown__controls {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}
</style>
