/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type MaybeRefOrGetter, type Ref, computed, ref, toValue } from 'vue'

import {
  DEFAULT_TITLE_MACRO,
  type Domain,
  type FormulaDraft,
  type FormulaItem,
  type GraphItem,
  type ItemId,
  isDynamic,
  isFormula
} from '../../types'
import {
  collectDirectRefs,
  collectTransitiveDependents,
  isArithmetic,
  serializeFormula
} from '../formula'
import { type FormulaEditor, useFormulaEditor } from './useFormulaEditor'
import { type TransformationEditor, useTransformationEditor } from './useTransformationEditor'

export type EditorMode = 'operations' | 'transformation'

/** Visibility change to apply to the committed AST's direct refs; null means "leave as is". */
export type RefVisibility = { ids: ItemId[]; visible: boolean } | null

export type CalculationCommit =
  | { kind: 'add'; draft: FormulaDraft; refVisibility: RefVisibility }
  | { kind: 'update'; id: ItemId; draft: FormulaDraft; refVisibility: RefVisibility }
  | { errors: string[] }

export interface SuccessAlert {
  id: ItemId
  kind: 'added' | 'updated'
  /** Distinguishes consecutive alerts on the same row so the display restarts its timer. */
  nonce: number
}

export interface CalculationEditor {
  mode: ComputedRef<EditorMode>
  editingId: ComputedRef<ItemId | null>
  title: Ref<string>
  /** The item's line color; defaults to `nextColor` (adding) or the edited item's color. */
  color: Ref<string>
  /** 'indeterminate' only occurs while editing, when the refs' visibilities are mixed. */
  hideSourceMetrics: Ref<boolean | 'indeterminate'>
  formula: FormulaEditor
  transformation: TransformationEditor
  successAlert: ComputedRef<SuccessAlert | null>
  /** Rows the building-blocks list must disable in the current mode/edit context. */
  isItemDisabled: (item: GraphItem) => boolean
  /** Toggle handler: switching discards in-progress input and cancels an active edit. */
  switchMode: (mode: EditorMode) => void
  startEdit: (item: FormulaItem) => void
  /** Badge click: appends a ref (operations) or selects the metric (transformation). */
  insertRef: (id: ItemId) => void
  commit: () => CalculationCommit
  dismissAlert: () => void
}

/** Orchestrates the two editors behind the calculation form: mode toggling, edit seeding, title, color, hide-source-metrics and the commit payloads. */
export function useCalculationEditor(
  items: MaybeRefOrGetter<readonly GraphItem[]>,
  domain: Domain,
  nextId: MaybeRefOrGetter<ItemId>,
  nextColor: MaybeRefOrGetter<string>
): CalculationEditor {
  const mode = ref<EditorMode>('operations')
  const editingId = ref<ItemId | null>(null)
  const title = ref('')
  const itemsById = computed(() => new Map(toValue(items).map((item) => [item.id, item])))

  /** Explicit choice only; null falls back to `nextColor` so it stays fresh as items change. */
  const pickedColor = ref<string | null>(null)
  const color = computed({
    get: () => pickedColor.value ?? toValue(nextColor),
    set: (value: string) => {
      pickedColor.value = value
    }
  })

  const stickyHide = ref(false)
  const hideState = ref<boolean | 'indeterminate'>(false)
  const hideSourceMetrics = computed({
    get: () => hideState.value,
    set: (value) => {
      hideState.value = value
      if (editingId.value === null && value !== 'indeterminate') {
        stickyHide.value = value
      }
    }
  })

  const formula = useFormulaEditor(items, domain, () => editingId.value)
  const transformation = useTransformationEditor(items, domain, () => editingId.value)

  const alert = ref<SuccessAlert | null>(null)
  let alertNonce = 0

  function clearForm(): void {
    editingId.value = null
    formula.reset()
    transformation.reset()
    title.value = ''
    pickedColor.value = null
    hideState.value = stickyHide.value
  }

  function switchMode(next: EditorMode): void {
    if (next === mode.value) {
      return
    }
    mode.value = next
    clearForm()
  }

  function startEdit(item: FormulaItem): void {
    clearForm()
    editingId.value = item.id
    title.value = item.title === DEFAULT_TITLE_MACRO ? '' : item.title
    pickedColor.value = item.color
    hideState.value = refsHideState(item)
    if (item.ast.op === 'percentile') {
      mode.value = 'transformation'
      transformation.selectedId.value = item.ast.operand.op === 'ref' ? item.ast.operand.id : null
      transformation.percentile.value = String(item.ast.percentile)
    } else {
      mode.value = 'operations'
      formula.text.value = isArithmetic(item.ast) ? serializeFormula(item.ast) : ''
    }
  }

  function refsHideState(item: FormulaItem): boolean | 'indeterminate' {
    const states = collectDirectRefs(item.ast).map((id) => itemsById.value.get(id)?.visible ?? true)
    if (states.length === 0 || states.every((visible) => visible)) {
      return false
    }
    return states.every((visible) => !visible) ? true : 'indeterminate'
  }

  function insertRef(id: ItemId): void {
    if (mode.value === 'operations') {
      formula.appendRef(id)
    } else {
      transformation.selectItem(id)
    }
  }

  const disabledIds = computed<Set<ItemId>>(() => {
    const all = toValue(items)
    const disabled = new Set<ItemId>()
    if (mode.value === 'transformation') {
      for (const item of all) {
        if (isDynamic(item.type)) {
          disabled.add(item.id)
        }
      }
    }
    const edited = editingId.value
    if (edited !== null) {
      // The edited item itself and everything that (transitively) references it are off limits.
      disabled.add(edited)
      for (const dependent of collectTransitiveDependents(all.filter(isFormula), edited)) {
        disabled.add(dependent)
      }
    }
    return disabled
  })

  function isItemDisabled(item: GraphItem): boolean {
    return disabledIds.value.has(item.id)
  }

  function commit(): CalculationCommit {
    const active = mode.value === 'operations' ? formula : transformation
    const result = active.commit()
    if ('errors' in result) {
      return { errors: result.errors }
    }
    const trimmed = title.value.trim()
    const draft: FormulaDraft = {
      type: 'rrd_formula',
      ast: result.ast,
      title: trimmed === '' ? DEFAULT_TITLE_MACRO : trimmed,
      color: color.value
    }
    const refIds = collectDirectRefs(result.ast)
    const hide = hideState.value
    const edited = editingId.value
    const refVisibility: RefVisibility =
      hide === 'indeterminate'
        ? null
        : hide
          ? { ids: refIds, visible: false }
          : edited !== null
            ? { ids: refIds, visible: true }
            : null // adding with the box unchecked changes nothing
    alert.value = null
    if (edited !== null) {
      clearForm()
      alert.value = { id: edited, kind: 'updated', nonce: ++alertNonce }
      return { kind: 'update', id: edited, draft, refVisibility }
    }
    // The store assigns ids deterministically, so the commit already knows the added row's id.
    const addedId = toValue(nextId)
    clearForm()
    alert.value = { id: addedId, kind: 'added', nonce: ++alertNonce }
    return { kind: 'add', draft, refVisibility }
  }

  function dismissAlert(): void {
    alert.value = null
  }

  return {
    mode: computed(() => mode.value),
    editingId: computed(() => editingId.value),
    title,
    color,
    hideSourceMetrics,
    formula,
    transformation,
    successAlert: computed(() => alert.value),
    isItemDisabled,
    switchMode,
    startEdit,
    insertRef,
    commit,
    dismissAlert
  }
}
