<script setup lang="ts">
import { onBeforeMount, onMounted, ref } from 'vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'
import { CmkForm } from '@/components/cmk-form/'
import type { IComponent } from '@/types'

const props = defineProps<{
  id: string
  spec: FormSpec
  data: unknown
  validation: ValidationMessages
}>()

const data_ref = ref()
onBeforeMount(() => {
  data_ref.value = props.data
})

onMounted(() => {
  component_ref.value!.setValidation(props.validation)
})

const component_ref = ref<IComponent>()
function setValidation(validation: ValidationMessages) {
  component_ref.value!.setValidation(validation)
}

defineExpose({
  setValidation
})
</script>

<template>
  <CmkForm :id="id" ref="component_ref" v-model:data="data_ref" :spec="spec" />
</template>
