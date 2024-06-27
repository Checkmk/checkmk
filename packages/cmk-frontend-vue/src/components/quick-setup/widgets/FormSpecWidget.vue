<script setup lang="ts">
import { ref, watch } from 'vue'
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import { type FormSpecWidgetProps } from './widget_types'

const props = defineProps<FormSpecWidgetProps>()
const emit = defineEmits(['update'])
const internal = ref(props?.data || {})

watch(internal.value, (newValue) => {
  emit('update', props.id, newValue)
})
</script>

<template>
  <table class="nform">
    <tr>
      <td>
        <CmkFormDispatcher v-model:data="internal" :spec="schema" :validation="[]" />
      </td>
    </tr>
  </table>
</template>
