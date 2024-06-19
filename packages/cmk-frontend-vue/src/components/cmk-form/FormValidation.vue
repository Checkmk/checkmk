<script setup lang="ts">
import type { ValidationMessages } from '@/utils'
import { computed } from 'vue'

const props = defineProps<{
  validation: ValidationMessages
}>()

const messages = computed((): string[] => {
  const messages: string[] = []
  props.validation.forEach((msg) => {
    messages.push(msg.message)
  })
  return messages
})
</script>

<template>
  <div v-if="messages" class="validation">
    <ul>
      <li v-for="message in messages" :key="message" style="background: #ff5e5e">{{ message }}</li>
    </ul>
  </div>
</template>
