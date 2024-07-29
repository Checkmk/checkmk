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
  active_mode.value = props.renderMode
})

const data = defineModel<unknown>('data', { required: true })
const value_as_json = computed(() => {
  return JSON.stringify(data.value)
})

const active_mode = ref<string>('readonly')

// Debug utiltilies
const show_toggle_mode = false
function toggleActiveMode() {
  if (active_mode.value === 'edit') {
    active_mode.value = 'readonly'
  } else if (active_mode.value === 'readonly') {
    active_mode.value = 'both'
  } else if (active_mode.value === 'both') {
    active_mode.value = 'edit'
  }
}
</script>

<template>
  <input
    v-if="show_toggle_mode"
    type="button"
    value="TOGGLE MODE"
    @click="toggleActiveMode"
  /><label v-if="show_toggle_mode">{{ active_mode }}</label>
  <div v-if="active_mode === 'readonly' || active_mode === 'both'">
    <CmkFormReadonly
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="spec"
    ></CmkFormReadonly>
  </div>

  <div v-if="active_mode === 'edit' || active_mode === 'both'">
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
      <input v-model="value_as_json" :name="id" type="hidden" />
    </table>
    <pre>{{ data }}</pre>
  </div>
</template>
