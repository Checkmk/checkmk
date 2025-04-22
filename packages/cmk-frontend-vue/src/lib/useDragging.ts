/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, type Ref } from 'vue'

export default function useDragging(): {
  tableRef: Ref<HTMLTableElement | null>
  dragStart: (event: DragEvent) => void
  dragEnd: (event: DragEvent) => void
  dragging: (event: DragEvent) => { draggedIndex: number; targetIndex: number } | null
} {
  /**
   * This is a workaround for the fact that a bug in Firefox prevents us from
   * using the clientX/clientY values from a drag event to get the mouse
   * position
   *
   * ref: https://bugzilla.mozilla.org/show_bug.cgi?id=505521
   */
  const clientY = ref(0)

  function update(event: MouseEvent) {
    clientY.value = event.clientY
  }

  const tableRef = ref<HTMLTableElement | null>(null)

  function dragStart(event: DragEvent) {
    ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.add('dragging')
    update(event)
    window.addEventListener('dragover', update)
  }

  function dragEnd(event: DragEvent) {
    ;(event.target! as HTMLTableCellElement).closest('tr')!.classList.remove('dragging')
    window.removeEventListener('dragover', update)
  }

  function dragging(event: DragEvent): { draggedIndex: number; targetIndex: number } | null {
    if (tableRef.value === null || clientY.value === 0) {
      return null
    }
    const tableChildren = [...tableRef.value!.children]
    const draggedRow = (event.target! as HTMLImageElement).closest('tr')!
    const draggedIndex = tableChildren.indexOf(draggedRow)

    function siblingMiddlePoint(sibling: Element) {
      const siblingRect = sibling.getBoundingClientRect()
      return siblingRect.top + siblingRect.height / 2
    }

    let targetIndex = -1
    let previous: null | undefined | Element = draggedRow.previousElementSibling
    while (previous && clientY.value < siblingMiddlePoint(previous)) {
      targetIndex = tableChildren.indexOf(previous)
      previous = tableRef.value!.children[targetIndex - 1]
    }

    let next: null | undefined | Element = draggedRow.nextElementSibling
    while (next && clientY.value > siblingMiddlePoint(next)) {
      targetIndex = tableChildren.indexOf(next)
      next = tableRef.value!.children[targetIndex + 1]
    }

    if (draggedIndex === targetIndex || targetIndex === -1) {
      return null
    }
    return { draggedIndex, targetIndex }
  }

  return { tableRef, dragStart, dragEnd, dragging }
}
