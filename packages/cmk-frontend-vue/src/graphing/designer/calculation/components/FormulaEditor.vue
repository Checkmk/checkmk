<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useWidgetKeys } from 'cmk-ui-library/lib/keyboardHelp'
import useId from 'cmk-ui-library/lib/useId'
import { ref } from 'vue'

const { _t } = usei18n()
useWidgetKeys(_t('Formula editor'), [{ combo: ['Enter'], description: _t('Submit formula') }])

const { errors } = defineProps<{ errors: string[] }>()

const text = defineModel<string>({ required: true })

const emit = defineEmits<{ submit: [] }>()

const labelId = useId()

// CmkInput is a generic SFC, so `InstanceType<typeof CmkInput>` is not usable; we only need focus().
const inputRef = ref<{ focus: () => void } | null>(null)

function focus(): void {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="graphing-formula-editor">
    <CmkHeading :id="labelId" type="h4">
      {{ _t('Formula input') }}
    </CmkHeading>
    <CmkInput
      ref="inputRef"
      v-model="text"
      :aria-labelledby="labelId"
      field-size="fill"
      :external-errors="errors"
      :placeholder="_t('Type a formula or select metrics and operators')"
      @keyup.enter="emit('submit')"
    />
  </div>
</template>

<style scoped>
.graphing-formula-editor {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--dimension-3);
}

/* CmkInput has no height prop; match the adjacent action-button height. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-formula-editor :deep(.cmk-input) {
  box-sizing: border-box;
  height: var(--dimension-10);
}
</style>
