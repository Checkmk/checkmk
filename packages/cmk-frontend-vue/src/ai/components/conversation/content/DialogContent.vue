<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkDialog from '@/components/CmkDialog.vue'

import type {
  DialogConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

defineProps<DialogConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <CmkDialog :title="title" :message="message as TranslatedString" />
</template>

<style scoped>
.ai-dialog-content {
  width: 100%;
  padding-bottom: var(--dimension-4);
}
</style>
