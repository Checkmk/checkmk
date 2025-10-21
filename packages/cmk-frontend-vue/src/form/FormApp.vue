<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'
import CmkHelpText from '@/components/CmkHelpText.vue'

import FormReadonly from '@/form/components/FormReadonly.vue'
import type { ValidationMessages } from '@/form/components/utils/validation'

import FormEdit from './components/FormEdit.vue'

const props = defineProps<{
  id: string
  spec: FormSpec
  data: unknown
  validation: ValidationMessages
  display_mode: 'edit' | 'readonly' | 'both'
}>()

const dataRef = ref()
immediateWatch(
  () => props.data,
  (newValue) => {
    dataRef.value = newValue
  }
)

immediateWatch(
  () => props.display_mode,
  (newValue) => {
    activeMode.value = newValue
  }
)

const valueAsJSON = computed(() => {
  return JSON.stringify(dataRef.value)
})

const activeMode = ref<string>('readonly')

// Debug utiltilies
const showToggleMode = false
function toggleActiveMode() {
  if (activeMode.value === 'edit') {
    activeMode.value = 'readonly'
  } else if (activeMode.value === 'readonly') {
    activeMode.value = 'both'
  } else if (activeMode.value === 'both') {
    activeMode.value = 'edit'
  }
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <div :id="`form-app--${id}`">
    <CmkErrorBoundary>
      <input
        v-if="showToggleMode"
        type="button"
        value="TOGGLE MODE"
        @click="toggleActiveMode"
      /><label v-if="showToggleMode">{{ activeMode }}</label>
      <div v-if="activeMode === 'readonly' || activeMode === 'both'">
        <FormReadonly :data="dataRef" :backend-validation="validation" :spec="spec"></FormReadonly>
      </div>

      <CmkHelpText :help="untranslated(spec.help)" />
      <div v-if="activeMode === 'edit' || activeMode === 'both'" class="form-app__root">
        <FormEdit
          v-if="display_mode === 'edit' || display_mode === 'both'"
          v-model:data="dataRef"
          :backend-validation="validation"
          :spec="spec"
        />
        <!-- This input field contains the computed json value which is sent when the form is submitted -->
        <input v-model="valueAsJSON" :name="id" type="hidden" />
      </div>
    </CmkErrorBoundary>
  </div>
</template>

<style scoped>
.form-app__root {
  margin: 2px;
}
</style>
