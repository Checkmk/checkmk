<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'
import type { FormSpec } from '@/vue_formspec_components'
import { CmkForm } from '@/components/cmk-form/'
import type { ValidationMessages } from '@/lib/validation'

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
</script>

<template>
  <CmkForm :id="id" v-model:data="data_ref" :backend-validation="validation" :spec="spec" />
</template>
