<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()

const open = ref(false)
</script>

<template>
  <div class="demo-container">
    <CmkCollapsibleTitle
      :title="'Collapsible Title'"
      :side-title="'Side Title'"
      :open="open"
      :help_text="'Some help text'"
      class="collapsible"
      @toggle-open="open = !open"
    />
    <CmkCollapsible :open="open">
      <CmkIndent> Some text inside the collapsible </CmkIndent>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.demo-container {
  min-width: 400px;
}

.collapsible {
  width: 100%;
}
</style>
