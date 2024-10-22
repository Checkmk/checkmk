<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FallbackWarning } from '@/notification/type_defs'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkButton from '@/components/CmkButton.vue'

const props = defineProps<{
  properties: FallbackWarning
}>()

import { ref, onMounted } from 'vue'

const isContentVisible = ref(true)

function hideContent() {
  isContentVisible.value = false
  localStorage.setItem(`${props.properties.user_id}-notificationFallbackVisibility`, 'hidden')
}

onMounted(() => {
  const savedState = localStorage.getItem(
    `${props.properties.user_id}-notificationFallbackVisibility`
  )
  if (savedState === 'hidden') {
    isContentVisible.value = false
  }
})

function openInNewTab(url: string) {
  window.open(url, '_blank')
}
</script>

<template>
  <div v-if="isContentVisible" class="help always_on">
    <div class="info_icon">
      <CmkIcon name="info" />
    </div>
    <div class="help_text">
      <p>{{ props.properties['i18n']['title'] }}</p>
      <p>{{ props.properties['i18n']['message'] }}</p>
      <div class="buttons">
        <CmkButton variant="info" @click="openInNewTab(properties['setup_link'])">
          {{ properties['i18n']['setup_link_title'] }}
        </CmkButton>
        <CmkButton @click="hideContent">
          {{ properties['i18n']['do_not_show_again_title'] }}
        </CmkButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
div.help {
  display: flex;
  margin-bottom: 24px;

  div.help_text {
    background-color: rgb(38 47 56);
    color: var(--white);
  }

  p {
    margin-left: var(--spacing);

    &:first-child {
      font-weight: var(--font-weight-bold);
    }

    &:last-child {
      padding-bottom: var(--spacing);
    }
  }

  a:first-child {
    margin-right: var(--spacing);
  }
}
</style>
