<script setup lang="ts">
import { computed, ref } from 'vue'
import FormEdit from './components/FormEdit.vue'
import FormReadonly from '@/form/components/FormReadonly.vue'
import type { FormSpec } from '@/form/components/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'
import { immediateWatch } from '@/form/components/utils/watch'

const props = defineProps<{
  id: string
  spec: FormSpec
  data: unknown
  backendValidation: ValidationMessages
  renderMode: 'edit' | 'readonly' | 'both'
}>()

const dataRef = ref()
immediateWatch(
  () => props.data,
  (newValue) => {
    dataRef.value = newValue
  }
)

immediateWatch(
  () => props.renderMode,
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
</script>

<template>
  <input v-if="showToggleMode" type="button" value="TOGGLE MODE" @click="toggleActiveMode" /><label
    v-if="showToggleMode"
    >{{ activeMode }}</label
  >
  <div v-if="activeMode === 'readonly' || activeMode === 'both'">
    <FormReadonly
      v-model:data="dataRef"
      :backend-validation="backendValidation"
      :spec="spec"
    ></FormReadonly>
  </div>

  <div v-if="activeMode === 'edit' || activeMode === 'both'">
    <table class="nform">
      <tr>
        <td>
          <FormEdit
            v-model:data="dataRef"
            :v-if="renderMode === 'edit' || renderMode === 'both'"
            :backend-validation="backendValidation"
            :spec="spec"
          />
        </td>
      </tr>
      <!-- This input field contains the computed json value which is sent when the form is submitted -->
      <input v-model="valueAsJSON" :name="id" type="hidden" />
    </table>
    <pre>{{ dataRef }}</pre>
  </div>
</template>
