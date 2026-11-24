<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface WidgetVisualizationProps {
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
const showTitle = defineModel<boolean>('showTitle', { required: true })
const showTitleBackground = defineModel<boolean>('showTitleBackground', { required: true })
// Offered only where a wizard binds it; the default keeps Vue from casting it to false.
const showWidgetBackground = defineModel<boolean | undefined>('showWidgetBackground', {
  default: undefined
})
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription :help="titleHelpText">{{ _t('Title') }}</FieldDescription>
      <FieldComponent>
        <CmkCheckbox v-model="showTitle" :label="_t('Show title')" />
        <CmkIndent v-if="showTitle">
          <div class="field-component__item">
            <CmkInput
              :model-value="title"
              type="text"
              field-size="medium"
              @update:model-value="(value) => (title = value ?? title)"
            />
          </div>
          <div class="field-component__item">
            <CmkCheckbox v-model="showTitleBackground" :label="_t('Show title background')" />
          </div>
        </CmkIndent>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow v-if="showWidgetBackground !== undefined">
      <FieldDescription>{{ _t('Background') }}</FieldDescription>
      <FieldComponent>
        <CmkCheckbox v-model="showWidgetBackground" :label="_t('Show widget background')" />
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
