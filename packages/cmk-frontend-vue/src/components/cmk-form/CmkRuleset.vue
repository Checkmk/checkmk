<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'
import { CmkForm } from '@/components/cmk-form/'

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
  <CmkForm :id="id" v-model:data="data_ref" :spec="spec" :validation="validation" />
</template>
