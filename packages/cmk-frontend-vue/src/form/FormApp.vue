<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import FormEdit from './components/FormEdit.vue'
import FormReadonly from '@/form/components/FormReadonly.vue'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'
import { immediateWatch } from '@/lib/watch'
import HelpText from '@/components/HelpText.vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'

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
const { ErrorBoundary } = useErrorBoundary()
</script>

<template>
  <div :id="`form-app--${id}`">
    <ErrorBoundary>
      <input
        v-if="showToggleMode"
        type="button"
        value="TOGGLE MODE"
        @click="toggleActiveMode"
      /><label v-if="showToggleMode">{{ activeMode }}</label>
      <div v-if="activeMode === 'readonly' || activeMode === 'both'">
        <FormReadonly :data="dataRef" :backend-validation="validation" :spec="spec"></FormReadonly>
      </div>

      <HelpText :help="spec.help" />
      <div v-if="activeMode === 'edit' || activeMode === 'both'">
        <table class="nform">
          <tbody>
            <tr>
              <td>
                <FormEdit
                  v-model:data="dataRef"
                  :v-if="display_mode === 'edit' || display_mode === 'both'"
                  :backend-validation="validation"
                  :spec="spec"
                />
                <!-- This input field contains the computed json value which is sent when the form is submitted -->
                <input v-model="valueAsJSON" :name="id" type="hidden" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ErrorBoundary>
  </div>
</template>

<style scoped>
.nform {
  margin: 0;
  background: transparent;

  > tbody > tr:first-child > td {
    padding: 0;
  }
}
</style>
