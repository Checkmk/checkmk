<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { isWarningDismissed } from '@/lib/userConfig'
import type { FallbackWarning } from 'cmk-shared-typing/typescript/notifications'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkButton from '@/components/CmkButton.vue'
import { persistWarningDismissal } from '@/lib/rest-api-client/userConfig'

const WARNING_KEY = 'notification_fallback'

const props = defineProps<{
  properties: FallbackWarning
  user_id: string
}>()

const warningHidden = ref(false)

async function hideContent() {
  warningHidden.value = true
  await persistWarningDismissal(WARNING_KEY)
}

onMounted(() => {
  warningHidden.value = isWarningDismissed(WARNING_KEY, warningHidden.value)
})

function openInSameTab(url: string) {
  window.open(url, '_self')
}
</script>

<template>
  <div v-if="!warningHidden" class="help always_on">
    <div class="info_icon">
      <CmkIcon name="info" />
    </div>
    <div class="help_text">
      <p>{{ props.properties['i18n']['title'] }}</p>
      <p>{{ props.properties['i18n']['message'] }}</p>
      <div class="buttons">
        <CmkButton variant="info" @click="openInSameTab(properties['setup_link'])">
          {{ properties['i18n']['setup_link_title'] }}
        </CmkButton>
        <CmkSpace />
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
    background-color: var(--help-text-bg-color);
    color: var(--help-text-font-color);
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
