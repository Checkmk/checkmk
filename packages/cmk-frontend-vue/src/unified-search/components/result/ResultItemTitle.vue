<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PropType, defineComponent, h } from 'vue'

type HtmlString = string

export default defineComponent({
  props: {
    title: { type: String as PropType<HtmlString>, required: true },
    context: { type: String, required: true }
  },
  render() {
    return h('div', [
      h('span', { innerHTML: this.title, class: 'title' }),
      h('span', { class: 'context' }, this.context)
    ])
  }
})
</script>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.highlight-query) {
  display: inline-block;
  background: transparent;
  color: var(--success);
  line-height: 14px;
}

div {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
}

span {
  position: relative;
  display: inline-block;
  padding: 0;
}

.title {
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.context {
  padding-left: var(--spacing-half);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
