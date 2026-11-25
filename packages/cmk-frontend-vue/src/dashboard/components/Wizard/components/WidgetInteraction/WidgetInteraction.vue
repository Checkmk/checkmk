<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="C extends LinkedContent">
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import ContextualLinkConfig from '../ContextualLink/ContextualLinkConfig.vue'
import type { LinkedContent } from '../ContextualLink/contextualLink'
import type { UseContextualLink } from '../ContextualLink/useContextualLink.ts'
import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'

const { _t } = usei18n()
// Binding to the following models will enable the corresponding settings
// Controls
const clickToPlacePin = defineModel<boolean | undefined>('clickToPlacePin', { default: undefined })
const showBurgerMenu = defineModel<boolean | undefined>('showBurgerMenu', { default: undefined })

// Title
const titleUrlEnabled = defineModel<boolean | undefined>('titleUrlEnabled', { default: undefined })
const titleUrl = defineModel<string | undefined>('titleUrl', { default: undefined })
const titleUrlValidationErrors = defineModel<string[]>('titleUrlValidationErrors', {
  default: []
})

// Read only title
const readOnlyTitle = defineModel<boolean | undefined>('readOnlyTitle', { default: undefined })

// Contextual links
const contextualLink = defineModel<UseContextualLink<C> | undefined>('contextualLink', {
  default: undefined
})

const { contextualLinkDefaultTarget, contextualLinkUnavailable } = defineProps<{
  contextualLinkDefaultTarget?: TranslatedString
  contextualLinkUnavailable?: TranslatedString | undefined
}>()
</script>

<template>
  <TableForm>
    <TableFormRow v-if="clickToPlacePin !== undefined && showBurgerMenu !== undefined">
      <FieldDescription>{{ _t('Controls') }}</FieldDescription>
      <FieldComponent>
        <div>
          <CmkCheckbox
            v-model:model-value="clickToPlacePin"
            :label="_t('Click on graph to place pin')"
          />
        </div>
        <div>
          <CmkCheckbox
            v-model:model-value="showBurgerMenu"
            :label="_t('Show burger menu for graph options')"
          />
        </div>
      </FieldComponent>
    </TableFormRow>
    <TableFormRow v-if="titleUrlEnabled !== undefined && titleUrl !== undefined">
      <FieldDescription>{{ _t('Title') }}</FieldDescription>
      <FieldComponent>
        <div class="field-component__item">
          <CmkCheckbox v-model="titleUrlEnabled" :label="_t('Link title to')" />
          <CmkIndent v-if="titleUrlEnabled">
            <CmkInput
              :model-value="titleUrl"
              type="text"
              field-size="medium"
              :external-errors="titleUrlValidationErrors"
              @update:model-value="(value) => (titleUrl = value ?? titleUrl)"
            />
          </CmkIndent>
        </div>
        <div v-if="readOnlyTitle !== undefined" class="field-component__item">
          <CmkCheckbox
            v-model="readOnlyTitle"
            :label="_t('Read only')"
            :help="
              _t(
                'A click on a host or service name, a related hosts count or a perfometer opens no details, and the rows offer no actions. The graph links next to the names still open the graphs.'
              )
            "
          />
        </div>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow v-if="contextualLink !== undefined">
      <FieldDescription>{{ _t('Links to views and dashboards') }}</FieldDescription>
      <FieldComponent>
        <ContextualLinkConfig
          v-model:handler="contextualLink"
          :default-target="contextualLinkDefaultTarget"
          :unavailable="contextualLinkUnavailable"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
