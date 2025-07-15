<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n'

const { t } = usei18n('unified-search-app')
</script>

<template>
  <div class="unified-search-footer">
    <div>
      {{
        t(
          'not-found-ask-ai',
          "You looked through the results and still haven't found what you are looking for?"
        )
      }}
    </div>
    <div>
      <CmkIcon variant="inline" name="sparkle" :title="t('ask-ai', 'Ask Checkmk AI')" />
      <a href="https://chat.checkmk.com/" target="_blank">{{ t('ask-ai', 'Go Ask AI') }}</a>
    </div>
  </div>
</template>

<style scoped>
.unified-search-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  bottom: 32px;
  position: fixed;
  width: 750px;
}
</style>
