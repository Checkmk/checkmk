<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkHelpText from '@/components/CmkHelpText.vue'

interface FieldDescriptionProps {
  dots?: boolean
  help?: TranslatedString | null
}

const props = withDefaults(defineProps<FieldDescriptionProps>(), {
  dots: true,
  help: null
})
</script>

<template>
  <div class="db-field-description__row">
    <div class="db-field-description__inner">
      <span class="db-field-description__label">
        <slot />
        <span v-if="props.help">&nbsp;<CmkHelpText :help="props.help" /></span>
        <span v-if="dots" class="db-field-description__dots"></span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.db-field-description__row {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
}

.db-field-description__inner {
  flex: 1;
  direction: ltr;
  overflow-wrap: break-word;
  overflow: hidden;
  text-align: left;
  text-wrap-mode: nowrap;
  position: relative;
  margin-right: 10px;
}

.db-field-description__label {
  width: 100%;
  display: block;
}

.db-field-description__dots {
  position: absolute;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.db-field-description__dots::after {
  content: '........................................................................................................................................................................................................';
}
</style>
