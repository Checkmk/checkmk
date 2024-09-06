<script setup lang="ts">
import '@/assets/variables.css'
import FormMultilineText from './FormMultilineText.vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: FormSpec.CommentTextArea
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: String, required: true })

const prependDateAndUsername = (): void => {
  const date = new Date()
  const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  data.value = `${formattedDate} ${props.spec.user_name || ''}:\n${data.value}`
}
</script>
<template>
  <div style="display: flex">
    <FormMultilineText v-model:data="data" :backend-validation="backendValidation" :spec="spec" />
    <img
      :alt="props.spec.i18n.prefix_date_and_comment"
      :title="props.spec.i18n.prefix_date_and_comment"
      :style="{ content: 'var(--icon-insertdate)', cursor: 'pointer' }"
      @click="prependDateAndUsername()"
    />
  </div>
</template>

<style scoped>
img {
  width: 20px;
  height: 20px;
  margin-left: 10px;
}
</style>
