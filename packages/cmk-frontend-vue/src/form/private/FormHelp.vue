<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'
import CmkIcon from '@/components/CmkIcon'

defineProps<{
  help: string
}>()
</script>

<template>
  <div v-if="help" class="form-help__container">
    <div class="form-help__info-icon">
      <CmkIcon name="info" size="small" />
    </div>
    <div class="form-help__help-text"><CmkHtml :html="help" /></div>
  </div>
</template>

<style scoped>
.form-help__info-icon {
  display: flex;
  align-items: center;
  background-color: #0667c1;
  border-radius: 4px 0 0 4px;
  padding: 5px;
}

.form-help__help-text {
  flex-grow: 1;
  padding: 10px;
  background-color: #11181d;
  border-radius: 0 4px 4px 0;
}

div.form-help__container {
  display: none;
  margin: 8px 0;
}

/* the old frontend sets a class on the body to hide or show the inline help */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
:global(body.inline_help_as_text) {
  div.form-help__container {
    display: flex;
  }
}
</style>
