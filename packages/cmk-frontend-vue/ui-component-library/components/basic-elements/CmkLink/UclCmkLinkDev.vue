<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkLink from '@/components/CmkLink.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <dl>
    <dt>Basic example</dt>
    <dd><CmkLink href="https://docs.checkmk.com">Visit documentation</CmkLink></dd>

    <dt>Opening in a new tab</dt>
    <dd>
      <CmkLink href="https://docs.checkmk.com" target="_blank"
        >Open documentation in new tab</CmkLink
      >
    </dd>

    <dt>With icon</dt>
    <dd>
      <CmkLink href="https://docs.checkmk.com" target="_blank">
        <CmkDynamicIcon
          :spec="{ type: 'default_icon', id: 'edit' }"
          size="small"
          class="result-item-icon"
        />
        Edit
      </CmkLink>
    </dd>
  </dl>
</template>

<style scoped>
dt {
  margin-top: 2em;
  margin-bottom: 0.5em;
}

dt code {
  white-space: pre;
}

dd {
  margin: 0;
  padding: 0;
}
</style>
