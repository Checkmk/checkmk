<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon'
import type { SimpleIcons } from '@/components/CmkIcon'

defineProps<{ icon: SimpleIcons; icon_emblem?: SimpleIcons | undefined }>()
</script>

<template>
  <div class="icon-with-emblem__wrapper">
    <CmkIcon :name="icon" size="xxlarge" />
    <div v-if="icon_emblem" class="icon-with-emblem__icon_emblem">
      <CmkIcon :name="icon_emblem" size="large" />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.icon-with-emblem__icon_emblem {
  position: absolute;
  bottom: -5px;
  right: -5px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.icon-with-emblem__wrapper {
  position: relative;
  flex-shrink: 0;
}
</style>
