/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import UclCmkBadgeCodeExample from '@ucl/components/basic-elements/CmkBadge/UclCmkBadgeCodeExample.vue'
import UclCmkButtonCodeExample from '@ucl/components/basic-elements/CmkButton/UclCmkButtonCodeExample.vue'
import UclCmkChipCodeExample from '@ucl/components/basic-elements/CmkChip/UclCmkChipCodeExample.vue'
import UclCmkCodeCodeExample from '@ucl/components/basic-elements/CmkCode/UclCmkCodeCodeExample.vue'
import UclCmkColorPickerCodeExample from '@ucl/components/basic-elements/CmkColorPicker/UclCmkColorPickerCodeExample.vue'
import UclCmkIconButtonCodeExample from '@ucl/components/basic-elements/CmkIconButton/UclCmkIconButtonCodeExample.vue'
import UclCmkInlineButtonCodeExample from '@ucl/components/basic-elements/CmkInlineButton/UclCmkInlineButtonCodeExample.vue'
import UclCmkSwitchCodeExample from '@ucl/components/basic-elements/CmkSwitch/UclCmkSwitchCodeExample.vue'
import UclCmkTagCodeExample from '@ucl/components/basic-elements/CmkTag/UclCmkTagCodeExample.vue'
import UclCmkAccordionCodeExample from '@ucl/components/content-organization/CmkAccordion/UclCmkAccordionCodeExample.vue'
import UclAccordionCmkStepPanelCodeExample from '@ucl/components/content-organization/CmkAccordionStepPanel/UclCmkAccordionStepPanelCodeExample.vue'
import UclCmkCatalogPanelCodeExample from '@ucl/components/content-organization/CmkCatalogPanel/UclCmkCatalogPanelCodeExample.vue'
import UclCmkCollapsibleCodeExample from '@ucl/components/content-organization/CmkCollapsible/UclCmkCollapsibleCodeExample.vue'
import UclCmkScrollContainerCodeExample from '@ucl/components/content-organization/CmkScrollContainer/UclCmkScrollContainerCodeExample.vue'
import UclCmkSlideInCodeExample from '@ucl/components/content-organization/CmkSlideIn/UclCmkSlideInCodeExample.vue'
import UclCmkSlideInDialogCodeExample from '@ucl/components/content-organization/CmkSlideInDialog/UclCmkSlideInDialogCodeExample.vue'
import UclCmkTabsCodeExample from '@ucl/components/content-organization/CmkTabs/UclCmkTabsCodeExample.vue'
import UclCmkWizardCodeExample from '@ucl/components/content-organization/CmkWizard/UclCmkWizardCodeExample.vue'
import UclTwoFactorAuthenticationCodeExample from '@ucl/components/content-organization/TwoFactorAuthentication/UclTwoFactorAuthenticationCodeExample.vue'
import UclCmkCheckboxCodeExample from '@ucl/components/form-elements/CmkCheckbox/UclCmkCheckboxCodeExample.vue'
import UclCmkDropdownCodeExample from '@ucl/components/form-elements/CmkDropdown/UclCmkDropdownCodeExample.vue'
import UclCmkDualListCodeExample from '@ucl/components/form-elements/CmkDualList/UclCmkDualListCodeExample.vue'
import UclCmkInputCodeExample from '@ucl/components/form-elements/CmkInput/UclCmkInputCodeExample.vue'
import UclCmkListCodeExample from '@ucl/components/form-elements/CmkList/UclCmkListCodeExample.vue'
import UclCmkToggleButtonGroupCodeExample from '@ucl/components/form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroupCodeExample.vue'
import UclCmkHtmlCodeExample from '@ucl/components/foundation-elements/CmkHtml/UclCmkHtmlCodeExample.vue'
import UclCmkIconCodeExample from '@ucl/components/foundation-elements/CmkIcon/UclCmkIconCodeExample.vue'
import UclCmkIconEmblemCodeExample from '@ucl/components/foundation-elements/CmkIcon/UclCmkIconEmblemCodeExample.vue'
import UclCmkMultitoneIconCodeExample from '@ucl/components/foundation-elements/CmkIcon/UclCmkMultitoneIconCodeExample.vue'
import UclCmkIndentCodeExample from '@ucl/components/foundation-elements/CmkIndent/UclCmkIndentCodeExample.vue'
import UclCmkKeyboardKeyCodeExample from '@ucl/components/foundation-elements/CmkKeyboardKey/UclCmkKeyboardKeyCodeExample.vue'
import UclCmkLabelRequiredCodeExample from '@ucl/components/foundation-elements/CmkLabelRequired/UclCmkLabelRequiredCodeExample.vue'
import UclCmkSpaceCodeExample from '@ucl/components/foundation-elements/CmkSpace/UclCmkSpaceCodeExample.vue'
import UclCmkZebraCodeExample from '@ucl/components/foundation-elements/CmkZebra/UclCmkZebraCodeExample.vue'
import UclCmkHeadingCodeExample from '@ucl/components/foundation-elements/typography/UclCmkHeadingCodeExample.vue'
import UclCmkParagraphCodeExample from '@ucl/components/foundation-elements/typography/UclCmkParagraphCodeExample.vue'
import UclI18nCodeExample from '@ucl/components/foundation-elements/typography/UclI18nCodeExample.vue'
import UclCmkLinkCardCodeExample from '@ucl/components/navigation/CmkLinkCard/UclCmkLinkCardCodeExample.vue'
import UclCmkAlertBoxCodeExample from '@ucl/components/system-feedback/CmkAlertBox/UclCmkAlertBoxCodeExample.vue'
import UclCmkCopyButtonCodeExample from '@ucl/components/system-feedback/CmkCopy/UclCmkCopyButtonCodeExample.vue'
import UclCmkCopyCodeExample from '@ucl/components/system-feedback/CmkCopy/UclCmkCopyCodeExample.vue'
import UclCmkDialogCodeExample from '@ucl/components/system-feedback/CmkDialog/UclCmkDialogCodeExample.vue'
import UclCmkErrorBoundaryCodeExample from '@ucl/components/system-feedback/CmkErrorBoundary/UclCmkErrorBoundaryCodeExample.vue'
import UclCmkHelpCodeExample from '@ucl/components/system-feedback/CmkHelp/UclCmkHelpCodeExample.vue'
import UclCmkInlineValidationCodeExample from '@ucl/components/system-feedback/CmkInlineValidation/UclCmkInlineValidationCodeExample.vue'
import UclCmkLoadingCodeExample from '@ucl/components/system-feedback/CmkLoading/UclCmkLoadingCodeExample.vue'
import UclCmkPerfometerCodeExample from '@ucl/components/system-feedback/CmkPerfometer/UclCmkPerfometerCodeExample.vue'
import UclCmkPopupDialogCodeExample from '@ucl/components/system-feedback/CmkPopupDialog/UclCmkPopupDialogCodeExample.vue'
import UclCmkProgressbarCodeExample from '@ucl/components/system-feedback/CmkProgressbar/UclCmkProgressbarCodeExample.vue'
import UclCmkSkeletonCodeExample from '@ucl/components/system-feedback/CmkSkeleton/UclCmkSkeletonCodeExample.vue'
import UclCmkTooltipCodeExample from '@ucl/components/system-feedback/CmkTooltip/UclCmkTooltipCodeExample.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ resolve: () => ({ href: '/' }) }),
  useRoute: () => ({ query: {} })
}))

// ─── Basic elements ───────────────────────────────────────────────────────────

test('CmkBadge code example renders without errors', () => {
  const { container } = render(UclCmkBadgeCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkButton code example renders without errors', () => {
  const { container } = render(UclCmkButtonCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkChip code example renders without errors', () => {
  const { container } = render(UclCmkChipCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkCode code example renders without errors', () => {
  const { container } = render(UclCmkCodeCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkColorPicker code example renders without errors', () => {
  const { container } = render(UclCmkColorPickerCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkIconButton code example renders without errors', () => {
  const { container } = render(UclCmkIconButtonCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkInlineButton code example renders without errors', () => {
  const { container } = render(UclCmkInlineButtonCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkSwitch code example renders without errors', () => {
  const { container } = render(UclCmkSwitchCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkTag code example renders without errors', () => {
  const { container } = render(UclCmkTagCodeExample)
  expect(container.firstChild).toBeTruthy()
})

// ─── Content organization ─────────────────────────────────────────────────────

test('CmkAccordion code example renders without errors', () => {
  const { container } = render(UclCmkAccordionCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkAccordionStepPanel code example renders without errors', () => {
  const { container } = render(UclAccordionCmkStepPanelCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkCatalogPanel code example renders without errors', () => {
  const { container } = render(UclCmkCatalogPanelCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkCollapsible code example renders without errors', () => {
  const { container } = render(UclCmkCollapsibleCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkScrollContainer code example renders without errors', () => {
  const { container } = render(UclCmkScrollContainerCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkSlideIn code example renders without errors', () => {
  const { container } = render(UclCmkSlideInCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkSlideInDialog code example renders without errors', () => {
  const { container } = render(UclCmkSlideInDialogCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkTabs code example renders without errors', () => {
  const { container } = render(UclCmkTabsCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkWizard code example renders without errors', () => {
  const { container } = render(UclCmkWizardCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('TwoFactorAuthentication code example renders without errors', () => {
  const { container } = render(UclTwoFactorAuthenticationCodeExample)
  expect(container.firstChild).toBeTruthy()
})

// ─── Form elements ────────────────────────────────────────────────────────────

test('CmkCheckbox code example renders without errors', () => {
  const { container } = render(UclCmkCheckboxCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkDropdown code example renders without errors', () => {
  const { container } = render(UclCmkDropdownCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkDualList code example renders without errors', () => {
  const { container } = render(UclCmkDualListCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkInput code example renders without errors', () => {
  const { container } = render(UclCmkInputCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkList code example renders without errors', () => {
  const { container } = render(UclCmkListCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkToggleButtonGroup code example renders without errors', () => {
  const { container } = render(UclCmkToggleButtonGroupCodeExample)
  expect(container.firstChild).toBeTruthy()
})

// ─── Foundation elements ──────────────────────────────────────────────────────

test('CmkHtml code example renders without errors', () => {
  const { container } = render(UclCmkHtmlCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkIcon code example renders without errors', () => {
  const { container } = render(UclCmkIconCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkIconEmblem code example renders without errors', () => {
  const { container } = render(UclCmkIconEmblemCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkMultitoneIcon code example renders without errors', () => {
  const { container } = render(UclCmkMultitoneIconCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkIndent code example renders without errors', () => {
  const { container } = render(UclCmkIndentCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkKeyboardKey code example renders without errors', () => {
  const { container } = render(UclCmkKeyboardKeyCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkLabelRequired code example renders without errors', () => {
  const { container } = render(UclCmkLabelRequiredCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkSpace code example renders without errors', () => {
  const { container } = render(UclCmkSpaceCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkZebra code example renders without errors', () => {
  const { container } = render(UclCmkZebraCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkHeading code example renders without errors', () => {
  const { container } = render(UclCmkHeadingCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkParagraph code example renders without errors', () => {
  const { container } = render(UclCmkParagraphCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('UclI18n code example renders without errors', () => {
  const { container } = render(UclI18nCodeExample)
  expect(container.firstChild).toBeTruthy()
})

// ─── Navigation ───────────────────────────────────────────────────────────────

test('CmkLinkCard code example renders without errors', () => {
  const { container } = render(UclCmkLinkCardCodeExample)
  expect(container.firstChild).toBeTruthy()
})

// ─── System feedback ──────────────────────────────────────────────────────────

test('CmkAlertBox code example renders without errors', () => {
  const { container } = render(UclCmkAlertBoxCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkCopyButton code example renders without errors', () => {
  const { container } = render(UclCmkCopyButtonCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkCopyIcon code example renders without errors', () => {
  const { container } = render(UclCmkCopyCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkDialog code example renders without errors', () => {
  const { container } = render(UclCmkDialogCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkErrorBoundary code example renders without errors', () => {
  const { container } = render(UclCmkErrorBoundaryCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkHelp code example renders without errors', () => {
  const { container } = render(UclCmkHelpCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkInlineValidation code example renders without errors', () => {
  const { container } = render(UclCmkInlineValidationCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkLoading code example renders without errors', () => {
  const { container } = render(UclCmkLoadingCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkPerfometer code example renders without errors', () => {
  const { container } = render(UclCmkPerfometerCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkPopupDialog code example renders without errors', () => {
  const { container } = render(UclCmkPopupDialogCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkProgressbar code example renders without errors', () => {
  const { container } = render(UclCmkProgressbarCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkSkeleton code example renders without errors', () => {
  const { container } = render(UclCmkSkeletonCodeExample)
  expect(container.firstChild).toBeTruthy()
})

test('CmkTooltip code example renders without errors', () => {
  const { container } = render(UclCmkTooltipCodeExample)
  expect(container.firstChild).toBeTruthy()
})
