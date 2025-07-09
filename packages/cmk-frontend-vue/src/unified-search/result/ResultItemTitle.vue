<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { defineComponent, h, type PropType } from 'vue'

export default defineComponent({
  props: {
    title: { type: Object as PropType<string>, required: true }
  },
  render() {
    return h('span', { innerHTML: this.title })
  }
})
</script>

<style scoped>
:deep(.highlight-query) {
  display: inline-block;
  background: var(--success-dimmed-2);
  color: var(--white);
  line-height: 14px;
}
</style>
