/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref } from 'vue'

// Native HTML5 drag&drop list reorder (no sortablejs), following the pattern
// of cmk-frontend-vue's SidebarApp snapin drag. The list is reordered live on
// dragover via Vue reactivity; a cancelled drag (Escape / drop outside, i.e.
// dropEffect 'none') reverts to the order captured at dragstart. `onFinished`
// fires once per completed drag so the caller can persist the new order.
export function useDragReorder<T>(
  getList: () => readonly T[],
  setList: (list: T[]) => void,
  onFinished: () => void,
  isEnabled: () => boolean = () => true
) {
  const dragIndex = ref<number | null>(null)
  let originalOrder: T[] | null = null

  function onDragStart(event: DragEvent, index: number) {
    // Children like the card's <a> are natively draggable and bubble their
    // dragstart up here — without this guard a drag could start (and reorder
    // a filtered subset) even while reordering is disabled.
    if (!isEnabled() || !event.dataTransfer) {
      return
    }
    event.dataTransfer.effectAllowed = 'move'
    // Firefox refuses to start a drag without data attached.
    event.dataTransfer.setData('text/plain', '')
    // Uniform ghost: always render the whole card, not a nested <img> the
    // drag happened to start from.
    if (event.currentTarget instanceof HTMLElement) {
      const rect = event.currentTarget.getBoundingClientRect()
      event.dataTransfer.setDragImage(
        event.currentTarget,
        event.clientX - rect.left,
        event.clientY - rect.top
      )
    }
    dragIndex.value = index
    originalOrder = [...getList()]
  }

  function onDragOver(event: DragEvent, index: number) {
    // Only claim the drop target for our own reorder drag — external drags
    // (files, links from other windows) keep their browser default.
    if (dragIndex.value === null) {
      return
    }
    event.preventDefault()
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move'
    }
    if (dragIndex.value === index) {
      return
    }
    const list = [...getList()]
    const moved = list.splice(dragIndex.value, 1)[0]
    if (moved === undefined) {
      return
    }
    list.splice(index, 0, moved)
    setList(list)
    dragIndex.value = index
  }

  function onDrop(event: DragEvent) {
    if (dragIndex.value !== null) {
      event.preventDefault()
    }
  }

  function onDragEnd(event: DragEvent) {
    if (dragIndex.value === null) {
      return
    }
    const cancelled = event.dataTransfer?.dropEffect === 'none'
    dragIndex.value = null
    if (cancelled && originalOrder) {
      setList(originalOrder)
      originalOrder = null
      return
    }
    originalOrder = null
    onFinished()
  }

  return { dragIndex, onDragStart, onDragOver, onDrop, onDragEnd }
}
