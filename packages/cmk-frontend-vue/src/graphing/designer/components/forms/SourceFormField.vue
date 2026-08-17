<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

import SourceFormStack from './SourceFormStack.vue'
import SourceFormText from './SourceFormText.vue'

const { label, labelVariant, errors, required } = defineProps<{
  label: TranslatedString
  labelVariant: 'name' | 'description'
  errors: TranslatedString[]
  required: boolean
}>()

const controlId = useId()
const validationId = useId()

const invalid = computed(() => errors.length > 0)
</script>

<template>
  <SourceFormStack spacing="label">
    <CmkLabel :for="controlId">
      <SourceFormText :variant="labelVariant">{{ label }}</SourceFormText
      ><CmkLabelRequired :show="required" space="before" />
    </CmkLabel>
    <CmkInlineValidation v-if="invalid" :id="validationId" :validation="errors" />
    <slot
      :control-id="controlId"
      :described-by="invalid ? validationId : undefined"
      :invalid="invalid"
    />
  </SourceFormStack>
</template>
