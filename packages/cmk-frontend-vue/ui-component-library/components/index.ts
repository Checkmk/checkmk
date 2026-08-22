/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import { pages as aiPages } from '../ai'
import { pages as dashboardPages } from '../dashboard'
import { pages as filtersPages } from '../filters'
import { pages as formSpecPages } from '../form'
import UclBreakpoints from '../foundations/Breakpoints/UclBreakpoints.vue'
import UclColors from '../foundations/Colors/UclColors.vue'
import UclIcons from '../foundations/Icons/UclIcons.vue'
import { pages as globalSettingsPages } from '../global-settings'
import { pages as graphingPages } from '../graphing'
import { pages as metricBackendPages } from '../metric-backend'
import { pages as monitoringPages } from '../monitoring'
import { pages as networkFlowPages } from '../network-flow'
import { pages as twoFactorAuthPages } from '../two-factor-authentication'
import UclCmkBadge from './basic-elements/CmkBadge/UclCmkBadge.vue'
import UclCmkButton from './basic-elements/CmkButton/UclCmkButton.vue'
import UclCmkChip from './basic-elements/CmkChip/UclCmkChip.vue'
import UclCmkCode from './basic-elements/CmkCode/UclCmkCode.vue'
import UclCmkColorPicker from './basic-elements/CmkColorPicker/UclCmkColorPicker.vue'
import UclCmkIconButton from './basic-elements/CmkIconButton/UclCmkIconButton.vue'
import UclCmkIconLink from './basic-elements/CmkIconLink/UclCmkIconLink.vue'
import UclCmkInlineButton from './basic-elements/CmkInlineButton/UclCmkInlineButton.vue'
import UclCmkLabeledSwitch from './basic-elements/CmkLabeledSwitch/UclCmkLabeledSwitch.vue'
import UclCmkLink from './basic-elements/CmkLink/UclCmkLink.vue'
import UclCmkSwitch from './basic-elements/CmkSwitch/UclCmkSwitch.vue'
import UclCmkTag from './basic-elements/CmkTag/UclCmkTag.vue'
import UclCmkAccordion from './content-organization/CmkAccordion/UclCmkAccordion.vue'
import UclCmkAccordionStepPanel from './content-organization/CmkAccordionStepPanel/UclCmkAccordionStepPanel.vue'
import UclCmkCatalogPanel from './content-organization/CmkCatalogPanel/UclCmkCatalogPanel.vue'
import UclCmkCollapsible from './content-organization/CmkCollapsible/UclCmkCollapsible.vue'
import UclCmkFlyout from './content-organization/CmkFlyout/UclCmkFlyout.vue'
import UclCmkScrollContainer from './content-organization/CmkScrollContainer/UclCmkScrollContainer.vue'
import UclCmkSlideIn from './content-organization/CmkSlideIn/UclCmkSlideIn.vue'
import UclCmkSlideInDialog from './content-organization/CmkSlideInDialog/UclCmkSlideInDialog.vue'
import UclCmkSlideInTabbed from './content-organization/CmkSlideInTabbed/UclCmkSlideInTabbed.vue'
import UclCmkSplitPane from './content-organization/CmkSplitPane/UclCmkSplitPane.vue'
import UclCmkTabs from './content-organization/CmkTabs/UclCmkTabs.vue'
import UclCmkWizard from './content-organization/CmkWizard/UclCmkWizard.vue'
import UclCmkAddDropdown from './form-elements/CmkAddDropdown/UclCmkAddDropdown.vue'
import UclCmkCheckbox from './form-elements/CmkCheckbox/UclCmkCheckbox.vue'
import UclCmkChipAutocomplete from './form-elements/CmkChipAutocomplete/UclCmkChipAutocomplete.vue'
import UclCmkChipSelect from './form-elements/CmkChipSelect/UclCmkChipSelect.vue'
import UclCmkDeprecatedDateTimePicker from './form-elements/CmkDeprecatedDateTimePicker/UclCmkDeprecatedDateTimePicker.vue'
import UclCmkDropdown from './form-elements/CmkDropdown/UclCmkDropdown.vue'
import UclCmkDualList from './form-elements/CmkDualList/UclCmkDualList.vue'
import UclCmkInput from './form-elements/CmkInput/UclCmkInput.vue'
import UclCmkList from './form-elements/CmkList/UclCmkList.vue'
import UclCmkRadioButton from './form-elements/CmkRadioButton/UclCmkRadioButton.vue'
import UclCmkSearchInput from './form-elements/CmkSearchInput/UclCmkSearchInput.vue'
import UclCmkSlideInDropdown from './form-elements/CmkSlideInDropdown/UclCmkSlideInDropdown.vue'
import UclCmkTimeSpan from './form-elements/CmkTimeSpan/UclCmkTimeSpan.vue'
import UclCmkToggleButtonGroup from './form-elements/CmkToggleButtonGroup/UclCmkToggleButtonGroup.vue'
import UclCmkDatePicker from './form-elements/date-time/UclCmkDatePicker.vue'
import UclCmkDateTimePicker from './form-elements/date-time/UclCmkDateTimePicker.vue'
import UclCmkTimePicker from './form-elements/date-time/UclCmkTimePicker.vue'
import UclCmkTimeRangePicker from './form-elements/date-time/UclCmkTimeRangePicker.vue'
import UclCmkTimeRangeTooltip from './form-elements/date-time/UclCmkTimeRangeTooltip.vue'
import UclCmkFilterDisplayItem from './form-elements/filter/UclCmkFilterDisplayItem.vue'
import UclCmkFilterInputItem from './form-elements/filter/UclCmkFilterInputItem.vue'
import UclCmkFilterSelection from './form-elements/filter/UclCmkFilterSelection.vue'
import UclCmkGhostWidth from './foundation-elements/CmkGhostWidth/UclCmkGhostWidth.vue'
import UclCmkHtml from './foundation-elements/CmkHtml/UclCmkHtml.vue'
import UclCmkIcon from './foundation-elements/CmkIcon/UclCmkIcon.vue'
import UclCmkIconEmblem from './foundation-elements/CmkIcon/UclCmkIconEmblem.vue'
import UclCmkMultitoneIcon from './foundation-elements/CmkIcon/UclCmkMultitoneIcon.vue'
import UclCmkIndent from './foundation-elements/CmkIndent/UclCmkIndent.vue'
import UclCmkKeyboardKey from './foundation-elements/CmkKeyboardKey/UclCmkKeyboardKey.vue'
import UclCmkLabel from './foundation-elements/CmkLabel/UclCmkLabel.vue'
import UclCmkLabelRequired from './foundation-elements/CmkLabelRequired/UclCmkLabelRequired.vue'
import UclCmkSpace from './foundation-elements/CmkSpace/UclCmkSpace.vue'
import UclCmkVisuallyHidden from './foundation-elements/CmkVisuallyHidden/UclCmkVisuallyHidden.vue'
import UclCmkZebra from './foundation-elements/CmkZebra/UclCmkZebra.vue'
import UclCmkHeading from './foundation-elements/typography/UclCmkHeading.vue'
import UclCmkParagraph from './foundation-elements/typography/UclCmkParagraph.vue'
import UclArrowDown from './graphics/ArrowDown/UclArrowDown.vue'
import UclCmkBreadcrumb from './navigation/CmkBreadcrumb/UclCmkBreadcrumb.vue'
import UclCmkLinkCard from './navigation/CmkLinkCard/UclCmkLinkCard.vue'
import UclCmkAlertBox from './system-feedback/CmkAlertBox/UclCmkAlertBox.vue'
import UclCmkCopy from './system-feedback/CmkCopy/UclCmkCopy.vue'
import UclCmkErrorBoundary from './system-feedback/CmkErrorBoundary/UclCmkErrorBoundary.vue'
import UclCmkHelpText from './system-feedback/CmkHelpText/UclCmkHelpText.vue'
import UclCmkInlineValidation from './system-feedback/CmkInlineValidation/UclCmkInlineValidation.vue'
import UclCmkLoading from './system-feedback/CmkLoading/UclCmkLoading.vue'
import UclCmkPaste from './system-feedback/CmkPaste/UclCmkPaste.vue'
import UclCmkPerfometer from './system-feedback/CmkPerfometer/UclCmkPerfometer.vue'
import UclCmkPopup from './system-feedback/CmkPopup/UclCmkPopup.vue'
import UclCmkPopupDialog from './system-feedback/CmkPopupDialog/UclCmkPopupDialog.vue'
import UclCmkSkeleton from './system-feedback/CmkSkeleton/UclCmkSkeleton.vue'
import UclCmkStateCountBar from './system-feedback/CmkStateCountBar/UclCmkStateCountBar.vue'
import UclCmkTooltip from './system-feedback/CmkTooltip/UclCmkTooltip.vue'
import UclStateTag from './system-feedback/StateTag/UclStateTag.vue'
import UclCmkProgressCircle from './system-feedback/progress/UclCmkProgressCircle.vue'
import UclCmkProgressbar from './system-feedback/progress/UclCmkProgressbar.vue'

const basicElementsPages = [
  new Page('CmkBadge', UclCmkBadge),
  new Page('CmkButton', UclCmkButton),
  new Page('CmkIconButton', UclCmkIconButton),
  new Page('CmkIconLink', UclCmkIconLink),
  new Page('CmkInlineButton', UclCmkInlineButton),
  new Page('CmkChip', UclCmkChip),
  new Page('CmkCode', UclCmkCode),
  new Page('CmkColorPicker', UclCmkColorPicker),
  new Page('CmkLabeledSwitch', UclCmkLabeledSwitch),
  new Page('CmkLink', UclCmkLink),
  new Page('CmkSwitch', UclCmkSwitch),
  new Page('CmkTag', UclCmkTag)
]

const contentOrganizationPages = [
  new Page('CmkAccordion', UclCmkAccordion),
  new Page('CmkAccordionStepPanel', UclCmkAccordionStepPanel),
  new Page('CmkTabs', UclCmkTabs),
  new Page('CmkCatalogPanel', UclCmkCatalogPanel),
  new Page('CmkCollapsible', UclCmkCollapsible),
  new Page('CmkFlyout', UclCmkFlyout),
  new Page('CmkScrollContainer', UclCmkScrollContainer),
  new Page('CmkSlideIn', UclCmkSlideIn),
  new Page('CmkSlideInDialog', UclCmkSlideInDialog),
  new Page('CmkSlideInTabbed', UclCmkSlideInTabbed),
  new Page('CmkSplitPane', UclCmkSplitPane),
  new Page('CmkWizard', UclCmkWizard)
]

const formElementsPages = [
  new Page('CmkAddDropdown', UclCmkAddDropdown),
  new Page('CmkCheckbox', UclCmkCheckbox),
  new Page('CmkChipAutocomplete', UclCmkChipAutocomplete),
  new Page('CmkChipSelect', UclCmkChipSelect),
  new Page('CmkDeprecatedDateTimePicker', UclCmkDeprecatedDateTimePicker),
  new Page('CmkDropdown', UclCmkDropdown),
  new Page('CmkDualList', UclCmkDualList),
  new Page('CmkInput', UclCmkInput),
  new Page('CmkList', UclCmkList),
  new Page('CmkRadioButton', UclCmkRadioButton),
  new Page('CmkSearchInput', UclCmkSearchInput),
  new Page('CmkSlideInDropdown', UclCmkSlideInDropdown),
  new Page('CmkTimeSpan', UclCmkTimeSpan),
  new Page('CmkToggleButtonGroup', UclCmkToggleButtonGroup),
  new Folder('Date & Time Pickers', [
    new Page('CmkTimePicker', UclCmkTimePicker),
    new Page('CmkDatePicker', UclCmkDatePicker),
    new Page('CmkDateTimePicker', UclCmkDateTimePicker),
    new Page('CmkTimeRangePicker', UclCmkTimeRangePicker),
    new Page('CmkTimeRangeTooltip', UclCmkTimeRangeTooltip)
  ]),
  new Folder('Filters', [
    new Page('CmkFilterInputItem', UclCmkFilterInputItem),
    new Page('CmkFilterDisplayItem', UclCmkFilterDisplayItem),
    new Page('CmkFilterSelection', UclCmkFilterSelection)
  ])
]

const foundationsPages = [
  new Page('Breakpoints', UclBreakpoints),
  new Page('Colors', UclColors),
  new Page('Icons', UclIcons)
]

const foundationElementsPages = [
  new Page('CmkIcon', UclCmkIcon),
  new Page('CmkIconEmblem', UclCmkIconEmblem),
  new Page('CmkMultitoneIcon', UclCmkMultitoneIcon),
  new Page('CmkHeading', UclCmkHeading),
  new Page('CmkParagraph', UclCmkParagraph),
  new Page('CmkGhostWidth', UclCmkGhostWidth),
  new Page('CmkHtml', UclCmkHtml),
  new Page('CmkIndent', UclCmkIndent),
  new Page('CmkKeyboardKey', UclCmkKeyboardKey),
  new Page('CmkLabel', UclCmkLabel),
  new Page('CmkLabelRequired', UclCmkLabelRequired),
  new Page('CmkSpace', UclCmkSpace),
  new Page('CmkVisuallyHidden', UclCmkVisuallyHidden),
  new Page('CmkZebra', UclCmkZebra)
]

const graphicsPages = [new Page('ArrowDown', UclArrowDown)]

const navigationPages = [
  new Page('CmkBreadcrumb', UclCmkBreadcrumb),
  new Page('CmkLinkCard', UclCmkLinkCard)
]

const systemFeedbackPages = [
  new Page('CmkAlertBox', UclCmkAlertBox),
  new Page('CmkCopy', UclCmkCopy),
  new Page('CmkErrorBoundary', UclCmkErrorBoundary),
  new Page('CmkHelpText', UclCmkHelpText),
  new Page('CmkInlineValidation', UclCmkInlineValidation),
  new Page('CmkLoading', UclCmkLoading),
  new Page('CmkPaste', UclCmkPaste),
  new Page('CmkPerfometer', UclCmkPerfometer),
  new Page('CmkPopup', UclCmkPopup),
  new Page('CmkPopupDialog', UclCmkPopupDialog),
  new Folder('Progress', [
    new Page('CmkProgressbar', UclCmkProgressbar),
    new Page('CmkProgressCircle', UclCmkProgressCircle)
  ]),
  new Page('CmkSkeleton', UclCmkSkeleton),
  new Page('CmkStateCountBar', UclCmkStateCountBar),
  new Page('StateTag', UclStateTag),
  new Page('CmkTooltip', UclCmkTooltip)
]
export const roots = [
  new Folder('Foundations', foundationsPages, true),
  new Folder(
    'Components',
    [
      new Folder('Basic elements', basicElementsPages, true),
      new Folder('Content organization', contentOrganizationPages, true),
      new Folder('Form elements', formElementsPages),
      new Folder('Foundation elements', foundationElementsPages),
      new Folder('Graphics', graphicsPages),
      new Folder('Navigation', navigationPages),
      new Folder('System feedback', systemFeedbackPages)
    ],
    true
  ),
  new Folder('Developer Playground', [
    new Folder('AI', aiPages),
    new Folder('Dashboards', dashboardPages),
    new Folder('Filters', filtersPages),
    new Folder('Form Spec Elements', formSpecPages),
    new Folder('Global settings', globalSettingsPages),
    new Folder('Graphing', graphingPages),
    new Folder('Metric backend', metricBackendPages),
    new Folder('Monitoring', monitoringPages),
    new Folder('Network flow', networkFlowPages),
    new Folder('Two Factor Authentication', twoFactorAuthPages)
  ])
]
