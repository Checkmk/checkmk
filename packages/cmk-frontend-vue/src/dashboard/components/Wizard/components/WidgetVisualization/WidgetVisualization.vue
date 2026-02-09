<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkIndent from '@/components/CmkIndent.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'
import LinkContent from './LinkContent.vue'

const { _t } = usei18n()

interface WidgetVisualizationProps {
  linkValidation?: TranslatedString[]
  linkOptions?: Suggestion[]
  targetOptions?: Suggestion[]
  titleMacros?: string[] | null
}

const props = withDefaults(defineProps<WidgetVisualizationProps>(), {
  titleMacros: null
})

const titleHelpText = computed(() => {
  if (!props.titleMacros || props.titleMacros.length === 0) {
    return null
  }
  const macrosList = props.titleMacros.map((macro) => `<li><tt>${macro}</tt></li>`).join('')
  return untranslated(
    `<b>${_t('The widget title can be static or dynamic.')}</b><br><br>` +
      `${_t('To create a dynamic title, use the following macros to automatically insert contextual information:')}` +
      `<ul>${macrosList}</ul>` +
      `${_t('These macros can be combined with custom text, e.g. "some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".')}`
  )
})

const title = defineModel<string>('title', { required: true })
const titleUrlEnabled = defineModel<boolean>('titleUrlEnabled', { required: true })
const titleUrl = defineModel<string>('titleUrl', { required: true })
const titleUrlValidationErrors = defineModel<string[]>('titleUrlValidationErrors', {
  required: true
})
const showTitle = defineModel<boolean>('showTitle', { required: true })
const showTitleBackground = defineModel<boolean>('showTitleBackground', { required: true })
const showWidgetBackground = defineModel<boolean>('showWidgetBackground', { required: true })

const linkType = defineModel<string | null>('linkType', { required: false, default: undefined })
const linkTarget = defineModel<string | null>('linkTarget', { required: false, default: undefined })

const displayLinkContent = computed(
  () => linkType.value !== undefined || linkTarget.value !== undefined
)
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription :help="titleHelpText">{{ _t('Title') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          :model-value="title"
          type="text"
          field-size="MEDIUM"
          @update:model-value="(value) => (title = value ?? title)"
        />
      </FieldComponent>
    </TableFormRow>
    <TableFormRow>
      <FieldDescription>{{ _t('Interaction') }}</FieldDescription>
      <FieldComponent>
        <div class="field-component__item">
          <CmkCheckbox v-model="titleUrlEnabled" :label="_t('Link title to')" />
          <CmkIndent v-if="titleUrlEnabled">
            <CmkInput
              :model-value="titleUrl"
              type="text"
              field-size="MEDIUM"
              :external-errors="titleUrlValidationErrors"
              @update:model-value="(value) => (titleUrl = value ?? titleUrl)"
            />
          </CmkIndent>
        </div>
        <div v-if="displayLinkContent" class="field-component__item">
          <LinkContent
            v-model:link-type="linkType"
            v-model:link-target="linkTarget"
            :link-validation="linkValidation || []"
            :link-options="linkOptions || []"
            :target-options="targetOptions || []"
          />
        </div>
      </FieldComponent>
    </TableFormRow>
    <TableFormRow>
      <FieldDescription>{{ _t('Appearance') }}</FieldDescription>
      <FieldComponent>
        <div class="field-component__item">
          <CmkCheckbox v-model="showTitle" :label="_t('Show title')" />
        </div>
        <div class="field-component__item">
          <CmkCheckbox v-model="showTitleBackground" :label="_t('Show title background')" />
        </div>
        <div class="field-component__item">
          <CmkCheckbox v-model="showWidgetBackground" :label="_t('Show widget background')" />
        </div>
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
