<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The dialogs the one-object commands open, as a set.

Which of them is up is decided by ``useObjectActions``, and every surface that
offers those commands needs all four — so they are declared here once rather
than repeated by each map view.
-->
<script setup lang="ts">
import type { UseObjectActions } from '@/maps/map/commands/useObjectActions'

import AckModal from './AckModal.vue'
import CommentModal from './CommentModal.vue'
import DowntimeModal from './DowntimeModal.vue'
import RemoveDowntimeModal from './RemoveDowntimeModal.vue'

const props = defineProps<{
  actions: UseObjectActions
  /** Where the commands are sent; without one there is nothing to send to. */
  checkmkUrl: string | null
}>()
</script>

<template>
  <template v-if="checkmkUrl">
    <AckModal
      v-if="props.actions.ackModalObject.value"
      :object="props.actions.ackModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="props.actions.closeAckModal"
    />
    <DowntimeModal
      v-if="props.actions.downtimeModalObject.value"
      :object="props.actions.downtimeModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="props.actions.closeDowntimeModal"
    />
    <CommentModal
      v-if="props.actions.commentModalObject.value"
      :object="props.actions.commentModalObject.value"
      :checkmk-url="checkmkUrl"
      @close="props.actions.closeCommentModal"
    />
    <RemoveDowntimeModal
      v-if="props.actions.removeDowntimeModal.visible"
      :downtimes="props.actions.removeDowntimeModal.downtimes"
      :checkmk-url="checkmkUrl"
      :object-name="props.actions.removeDowntimeModal.objectName"
      @close="props.actions.closeRemoveDowntimeModal"
    />
  </template>
</template>
