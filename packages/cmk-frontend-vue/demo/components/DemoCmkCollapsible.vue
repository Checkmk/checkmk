<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()

const open = ref(false)
</script>

<template>
  <div class="demo-cmk-collapsible__title_container">
    <CmkCollapsibleTitle
      :title="'Collapsible Title'"
      :side-title="'Side Title'"
      :open="open"
      :help_text="'Some help text'"
      class="demo-cmk-collapsible__collapsible"
      @toggle-open="open = !open"
    />
    <CmkCollapsible :open="open">
      <CmkIndent> Some text inside the collapsible </CmkIndent>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.demo-cmk-collapsible__title-container {
  min-width: 400px;
}

.demo-cmk-collapsible__collapsible {
  width: 100%;
}
</style>
