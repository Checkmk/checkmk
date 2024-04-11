<script setup lang="ts">
import { onBeforeMount, onMounted, ref } from 'vue'
import type { VueSchema } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'
import { CmkForm } from '@/components/cmk-form/'

const props = defineProps<{
  id: string
  spec: VueSchema
  data: unknown
  validation: ValidationMessages
}>()

const data_ref = ref()
onBeforeMount(() => {
  data_ref.value = props.data
})

function get_value() {
  return data_ref.value
}
</script>

<template>
  <CmkForm :id="id" :spec="spec" :validation="validation" v-model:data="data_ref" />
</template>
