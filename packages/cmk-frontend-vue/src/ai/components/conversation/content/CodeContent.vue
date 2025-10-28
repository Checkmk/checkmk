<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import CmkCode from '@/components/CmkCode.vue'

import type {
  CodeBlockConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/conversation-templates/base-template'

defineProps<CodeBlockConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <CmkCode class="ai-code-content" :code_txt="code" />
</template>

<style scoped>
.ai-code-content {
  width: 100%;
  position: relative;

  /* stylelint-disable checkmk/vue-bem-naming-convention */
  /* stylelint-disable-next-line selector-pseudo-class-no-unknown  */
  &:deep(.code_container) {
    width: 80%;
    position: relative;
  }
}
</style>
