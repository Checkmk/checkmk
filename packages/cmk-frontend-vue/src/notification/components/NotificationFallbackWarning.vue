<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { NotificationFallbackWarning } from 'cmk-shared-typing/typescript/notifications'
import CmkDialog from '@/components/CmkDialog.vue'

const WARNING_KEY = 'notification_fallback'

const props = defineProps<{
  properties: NotificationFallbackWarning
}>()

function openInSameTab(url: string) {
  window.open(url, '_self')
}
</script>

<template>
  <CmkDialog
    :title="props.properties['i18n']['title']"
    :message="props.properties['i18n']['message']"
    :buttons="[
      {
        title: properties['i18n']['setup_link_title'],
        variant: 'info',
        onclick: () => openInSameTab(properties['setup_link'])
      }
    ]"
    :dismissal_button="{ title: properties['i18n']['do_not_show_again_title'], key: WARNING_KEY }"
  />
</template>
