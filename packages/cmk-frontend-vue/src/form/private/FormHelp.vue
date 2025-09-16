<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'
import CmkIcon from '@/components/CmkIcon.vue'

defineProps<{
  help: string
}>()
</script>

<template>
  <div v-if="help" class="help form-help__container">
    <div class="info_icon">
      <CmkIcon name="info" size="small" />
    </div>
    <div class="help_text"><CmkHtml :html="help" /></div>
  </div>
</template>

<style scoped>
div.form-help__container {
  display: none;
}

/* the old frontend sets a class on the body to hide or show the inline help */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
:global(body.inline_help_as_text) {
  div.form-help__container {
    display: flex;
  }
}
</style>
