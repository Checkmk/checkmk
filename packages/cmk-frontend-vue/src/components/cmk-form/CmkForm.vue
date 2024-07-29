<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CmkFormDispatcher from './CmkFormDispatcher.vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/lib/validation'
import CmkFormReadonly from '@/components/cmk-form/CmkFormReadonly.vue'

const props = defineProps<{
  id: string
  spec: FormSpec
  backendValidation: ValidationMessages
  renderMode: 'edit' | 'readonly' | 'both'
}>()

onMounted(() => {
  activeMode.value = props.renderMode
})

const data = defineModel<unknown>('data', { required: true })
const valueAsJSON = computed(() => {
  return JSON.stringify(data.value)
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
    <CmkFormReadonly
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="spec"
    ></CmkFormReadonly>
  </div>

  <div v-if="activeMode === 'edit' || activeMode === 'both'">
    <table class="nform">
      <tr>
        <td>
          <CmkFormDispatcher
            v-model:data="data"
            :v-if="renderMode === 'edit' || renderMode === 'both'"
            :backend-validation="backendValidation"
            :spec="spec"
          />
        </td>
      </tr>
      <!-- This input field contains the computed json value which is sent when the form is submitted -->
      <input v-model="valueAsJSON" :name="id" type="hidden" />
    </table>
    <pre>{{ data }}</pre>
  </div>
</template>
