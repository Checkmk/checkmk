<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { NotificationFallbackWarning } from 'cmk-shared-typing/typescript/notifications'

import { untranslated } from '@/lib/i18n'
import { useDismissDialog } from '@/lib/useDismissDialog'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

const WARNING_KEY = 'notification_fallback'

const props = defineProps<{
  properties: NotificationFallbackWarning
}>()

const { isShown: dismissalShown, dismiss: dismissAlert } = useDismissDialog(WARNING_KEY)

function openInSameTab(url: string) {
  window.open(url, '_self')
}
</script>

<template>
  <CmkAlertBox
    v-if="dismissalShown"
    :heading="untranslated(props.properties['i18n']['title'])"
    :main-button="{
      title: untranslated(properties['i18n']['setup_link_title']),
      onclick: () => openInSameTab(properties['setup_link'])
    }"
    :optional-button="{
      title: untranslated(properties['i18n']['do_not_show_again_title']),
      icon: 'cancel',
      onclick: dismissAlert
    }"
  >
    {{ untranslated(props.properties['i18n']['message']) }}
  </CmkAlertBox>
</template>
