<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

import type {
  AlertConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

defineProps<AlertConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <CmkAlertBox :variant="variant">{{ text }}</CmkAlertBox>
</template>

<style scoped>
.ai-alert-content {
  padding-bottom: var(--dimension-4);
}
</style>
