<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type {
  TBaseConversationElementEmits,
  TextConversationElementContent
} from '@/ai/lib/conversation-templates/base-template'
import { typewriter } from '@/ai/lib/utils'

const props = defineProps<TextConversationElementContent>()
const typedText = ref<string>('')

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  if (props.noAnimation) {
    typedText.value = props.text
  } else {
    typewriter(typedText, props.text, () => {
      emit('done')
    })
  }
})
</script>

<template>
  <p class="ai-text-content">
    {{ typedText }}
  </p>
</template>

<style scoped>
.ai-text-content {
  padding-bottom: var(--dimension-4);
}
</style>
