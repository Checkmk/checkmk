<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PropType, defineComponent, h } from 'vue'

export default defineComponent({
  props: {
    text: { type: Object as PropType<string>, required: true }
  },
  render() {
    return h('span', { innerHTML: this.text })
  }
})
</script>
