/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export const workspace = {
  workspaceFolders: [
    {
      uri: { fsPath: '/mock/workspace' },
      name: 'mock',
      index: 0
    }
  ],
  getConfiguration: () => ({
    get: () => undefined,
    update: async () => {},
    inspect: () => ({})
  }),
  createFileSystemWatcher: () => ({
    onDidChange: () => ({ dispose: () => {} }),
    onDidCreate: () => ({ dispose: () => {} }),
    onDidDelete: () => ({ dispose: () => {} }),
    dispose: () => {}
  })
}

export class RelativePattern {
  constructor(
    public base: string,
    public pattern: string
  ) {}
}

export const window = {
  showInformationMessage: async () => undefined,
  showWarningMessage: async () => undefined,
  showErrorMessage: async () => undefined,
  createOutputChannel: () => ({
    appendLine: () => {},
    show: () => {},
    dispose: () => {}
  }),
  createStatusBarItem: () => ({
    show: () => {},
    hide: () => {},
    dispose: () => {},
    text: '',
    tooltip: '',
    command: '',
    color: undefined,
    backgroundColor: undefined
  }),
  createTerminal: () => ({
    sendText: () => {},
    show: () => {},
    dispose: () => {}
  }),
  createQuickPick: () => ({
    show: () => {},
    hide: () => {},
    dispose: () => {},
    items: [],
    selectedItems: [],
    onDidAccept: () => ({ dispose: () => {} }),
    onDidHide: () => ({ dispose: () => {} })
  })
}

export const commands = {
  registerCommand: () => ({ dispose: () => {} }),
  executeCommand: async () => {}
}

export const extensions = {
  getExtension: () => undefined
}

export enum ConfigurationTarget {
  Global = 1,
  Workspace = 2,
  WorkspaceFolder = 3
}

export class ThemeColor {
  constructor(public id: string) {}
}

export enum QuickPickItemKind {
  Separator = -1,
  Default = 0
}

export enum StatusBarAlignment {
  Left = 1,
  Right = 2
}
