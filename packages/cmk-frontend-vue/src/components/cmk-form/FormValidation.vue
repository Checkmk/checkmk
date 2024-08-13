<script setup lang="ts">
import { computed } from 'vue'
import type { ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  validation: ValidationMessages
}>()

const messages = computed((): string[] => {
  const messages: string[] = []
  props.validation.forEach((msg) => {
    if (msg.location.length === 0) {
      messages.push(msg.message)
    }
  })
  return messages
})
</script>

<template>
  <div v-if="messages.length > 0" class="validation">
    <ul>
      <li v-for="message in messages" :key="message" style="background: #ff5e5e">{{ message }}</li>
    </ul>
  </div>
</template>
