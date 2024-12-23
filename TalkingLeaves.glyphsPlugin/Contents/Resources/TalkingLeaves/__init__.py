# MenuTitle: TalkingLeaves
# -*- coding: utf-8 -*-

__doc__ = '''
Developers: this script (TalkingLeaves.py) can be run directly from within
Glyphs. In your Scripts folder, add an alias to the TalkingLeaves parent
folder. Then you don't have to restart Glyphs each time you make changes to
this file, like you normally do when you're developing a plugin.
'''

import sys
from GlyphsApp import Glyphs, GSGlyph, Message
from vanilla import (
  Window, Group, List2, Button, HelpButton, SplitView, CheckBox, TextBox, EditTextList2Cell, dialogs
)
import unicodedata
import TalkingLeaves.utils as utils
import TalkingLeaves.data as data

# Tell older Glyphs where to find dependencies
if Glyphs.versionNumber < 3.2:
  from pathlib import Path
  PKGS_PATH = str(Path('~/Library/Application Support/Glyphs 3/Scripts/site-packages').expanduser())
  if PKGS_PATH not in sys.path:
    scriptsPath = str(Path('~/Library/Application Support/Glyphs 3/Scripts').expanduser())
    pos = sys.path.index(scriptsPath) + 1
    sys.path.insert(pos, PKGS_PATH)

try:
  import hyperglot
  import hyperglot.languages
  import hyperglot.language
  import hyperglot.orthography
except ModuleNotFoundError:
  hyperglot = None

HYPERGLOT_MIN_VER = "0.7.0"
MIN_COLUMN_WIDTH = 20


def main():

  Glyphs.clearLog()
  print("Running as script…")

  if len(Glyphs.documents) == 0:
    Message("Please open a font before running TalkingLeaves.", title='Cannot load TalkingLeaves', OKButton="Dismiss")
    return

  TalkingLeaves()


class TalkingLeaves:

  def __init__(self):

    # Warn user and cancel startup if incompatible pyobjc version is installed
    import objc
    if objc.__version__ == "10.3":
      answer = dialogs.message(
        messageText='Incompatible pyobjc version',
        informativeText='pyobjc 10.3 is incompatible with TalkingLeaves because it breaks the Vanilla library. Please upgrade to pyobjc>=10.3.1 and restart Glyphs.',
      )
      self._closeAppDevMode()
      return

    # Warn user and cancel startup if Hyperglot is not installed
    if not hyperglot:
      answer = dialogs.ask(
        messageText='Hyperglot module is missing',
        informativeText='Follow the installation instructions at https://github.com/justinpenner/TalkingLeaves#installation',
        buttonTitles=[('Open in browser', 1), ('Cancel', 0)],
      )
      if answer:
        utils.webbrowser.open('https://github.com/justinpenner/TalkingLeaves#installation')
      self._closeAppDevMode()
      return

    # Warn user and cancel startup if minimum Hyperglot is not met
    elif utils.SimpleVersion(hyperglot.__version__) < utils.SimpleVersion(HYPERGLOT_MIN_VER):
      import sys
      pythonVersion = '.'.join([str(x) for x in sys.version_info][:3])
      message = f"Hyperglot >= {HYPERGLOT_MIN_VER} is required, but you have {hyperglot.__version__}.\n\nTo update, copy the following command, then paste it into Terminal:\n\npip3 install --python-version={pythonVersion} --only-binary=:all: --target=\"/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages\" --upgrade hyperglot\n\nThen, restart Glyphs."
      dialogs.message(
        messageText='Update required',
        informativeText=message,
      )
      self._closeAppDevMode()
      return


    self.font = Glyphs.font
    self.windowSize = (1000, 600)

    self.startGUI()

    # Stand-alone developer mode uses a "fake" GlyphsApp API for testing
    # without opening GlyphsApp.
    if getattr(Glyphs, "devMode", False):
      self._addDevTools()

    self.data = data.Data()
    self.defaultScriptIndex = 0
    self.fillTables()

    self.checkForHyperglotUpdates()

  def _closeAppDevMode(self):
    if getattr(Glyphs, "devMode", False):
      from AppKit import NSApplication
      app = NSApplication.sharedApplication()
      app.terminate_(self)

  def _addDevTools(self):
    # Add menu item with Cmd-W shortcut to easily close window
    from AppKit import NSApplication
    app = NSApplication.sharedApplication()
    fileMenu = app.mainMenu().itemAtIndex_(0)
    fileMenu.submenu().addItemWithTitle_action_keyEquivalent_("Close Window", self.w.close, "w")

  def startGUI(self):

    self.scriptsColHeaders = [
      # TODO: add ISO column, visible or hidden for indexing only?
      # dict(
      #   identifier='id',
      #   title='ISO',
      #   width=60,
      # ),
      dict(
        identifier='name',
        title='Script',
        width=100,
      ),
      dict(
        identifier='speakers',
        title='L1 Speakers',
        width=100,
      ),
    ]
    self.langsColHeaders = [
      # TODO: add ISO column, visible or hidden for indexing only?
      # dict(
      #   identifier='id',
      #   title='ISO',
      #   width=60,
      # ),
      dict(
        identifier='name',
        title='Language',
        width=160,
      ),
      dict(
        identifier='speakers',
        title='L1 Speakers',
        width=100,
        valueToCellConverter=self.langSpeakersValue_toCell,
        cellClass=TableCell,
      ),
      dict(
        identifier='ortho_status',
        title='Ortho. Status',
        width=94,
        valueToCellConverter=self.statusValue_toCell,
        cellClass=TableCell,
      ),
      dict(
        identifier='lang_status',
        title='Lang. Status',
        width=94,
        valueToCellConverter=self.statusValue_toCell,
        cellClass=TableCell,
      ),
      dict(
        identifier='chars',
        title='Missing Chars',
        valueToCellConverter=self.missingValue_toCell,
        cellClass=TableCell,
      ),
    ]
    for colHeader in self.scriptsColHeaders + self.langsColHeaders:
      colHeader['maxWidth'] = self.windowSize[0]
      colHeader['minWidth'] = MIN_COLUMN_WIDTH
      colHeader['sortable'] = True

    # Build GUI with Vanilla
    self.w = Window(
      self.windowSize,
      f"TalkingLeaves ({(Glyphs.currentDocument.filePath or self.font.familyName).split('/')[-1]} - {self.font.familyName})",
      minSize=(640, 180),
    )
    self.scriptsTable = List2(
      (0, 0, -0, -0),
      [],
      columnDescriptions=self.scriptsColHeaders,
      allowsMultipleSelection=False,
      enableTypingSensitivity=True,
      selectionCallback=self.refreshLangs,
      menuCallback=self.scriptsUpdateMenu,
    )
    self.w.showComplete = CheckBox(
      "auto",
      "Show completed",
      sizeStyle="regular",
      value=False,
      callback=self.showCompleteCallback,
    )
    self.w.showComplete._nsObject.setToolTip_(
      "Show languages whose basic set of Unicode characters is covered by your font. Some languages require additional unencoded glyphs and features."
    )
    self.w.showIncomplete = CheckBox(
      "auto",
      "Show incomplete",
      sizeStyle="regular",
      value=True,
      callback=self.showIncompleteCallback,
    )
    self.w.showIncomplete._nsObject.setToolTip_(
      "Show languages whose basic set of Unicode characters is not yet covered by your font."
    )
    self.langsTable = List2(
      (0, 0, -0, -0),
      [],
      columnDescriptions=self.langsColHeaders,
      enableTypingSensitivity=True,
      selectionCallback=self.langsSelectionCallback,
      menuCallback=self.langsUpdateMenu,
    )
    panes = [
      dict(view=self.scriptsTable, identifier="scripts", canCollapse=False, minSize=MIN_COLUMN_WIDTH),
      dict(view=self.langsTable, identifier="langs", canCollapse=False, minSize=MIN_COLUMN_WIDTH),
    ]
    self.w.top = SplitView("auto", panes)
    self.w.addGlyphs = Button(
      "auto",
      "Add selected glyphs",
      sizeStyle="regular",
      callback=self.addGlyphsCallback,
    )
    self.w.openRepo = HelpButton(
      "auto",
      callback=self.openRepoCallback,
    )
    self.w.statusBar = TextBox(
      "auto",
      text="",
      sizeStyle="regular",
      alignment="natural",
      selectable=True,
    )
    self.w.flex = Group("auto")
    rules = [
      "H:|[top]|",
      "H:|-pad-[statusBar]-gap-[flex(>=pad)]-gap-[showComplete]-gap-[showIncomplete]-gap-[addGlyphs]-gap-[openRepo]-gap-|",
      "V:|[top]-pad-[statusBar]-pad-|",
      "V:|[top]-pad-[flex]-pad-|",
      "V:|[top]-pad-[showComplete]-pad-|",
      "V:|[top]-pad-[showIncomplete]-pad-|",
      "V:|[top]-pad-[addGlyphs]-pad-|",
      "V:|[top]-pad-[openRepo]-pad-|",
    ]
    metrics = dict(pad=12, gap=16)
    self.w.addAutoPosSizeRules(rules, metrics)

    # Open GUI
    self.w.open()

    # Pane widths don't work when SplitView is in auto layout
    # Divider position has to be set after opening window
    self.w.top.getNSSplitView().setPosition_ofDividerAtIndex_(260, 0)

  def fillTables(self):

    '''
    Fill script and language lists with initial data
    '''

    self.scriptsTable.set(self.data.scriptsAsTable())

    # Fix some UI details…

    # This triggers selectionCallback, which can't be done at instantiation
    # time, or it will refresh langTable which doesn't exist yet.
    self.scriptsTable._tableView.setAllowsEmptySelection_(False)
    self.scriptsTable.setSelectedIndexes([self.defaultScriptIndex])

    # Tables begin scrolled to 2nd row for some reason
    self.scriptsTable.getNSTableView().scrollRowToVisible_(0)
    self.langsTable.getNSTableView().scrollRowToVisible_(0)

    # Refresh langs when window becomes active
    self.w.bind('became key', self.windowBecameKey)

  def refreshLangs(self, sender=None):

    '''
    Load/reload languages for the currently selected script
    '''

    rows = self.data.langsAsTable(
      scriptName=self.scriptsTable.getSelectedItems()[0]['name'],
      font=self.font,
      showIncomplete=self.w.showIncomplete.get(),
      showComplete=self.w.showComplete.get(),
    )
    self.langsTable.set(rows)
    self.updateStatusBar()

  def updateStatusBar(self):

    '''
    Write some useful info in the bottom of the window
    '''

    scriptName = self.scriptsTable.getSelectedItems()[0]['name']
    self.currentScriptComplete = len(self.data.completeLangs)
    self.currentScriptIncomplete = len(self.data.incompleteLangs)

    self.selectedChars = []
    for i in self.langsTable.getSelectedIndexes():
      self.selectedChars.extend(self.langsTable.get()[i]['chars'])
    self.selectedChars = set(self.selectedChars)

    m = "{completed}/{total} = {percent}% {script} completed".format(
      script=scriptName,
      total=len(self.data.completeLangs) + len(self.data.incompleteLangs),
      completed=self.currentScriptComplete,
      percent=self.currentScriptComplete * 100 // (len(self.data.completeLangs) + len(self.data.incompleteLangs)),
    )
    langSel = len(self.langsTable.getSelectedIndexes())
    if langSel:
      m += " ({langs} langs, {chars} missing chars selected)".format(
        langs=langSel,
        chars=len(self.selectedChars),
      )
    self.w.statusBar.set(m)

  def glyphInfoByChar_(self, char):
    return Glyphs.glyphInfoForUnicode(ord(char))

  def langSpeakersValue_toCell(self, value):

    '''
    Unknown speaker count has already been set to -1, so display it in the
    cell as "no data"
    '''

    if value == -1:
      return "(no data)"
    else:
      return value

  def statusValue_toCell(self, value):

    '''
    Unknown status is "", so display it as "no data"
    '''

    if value == "":
      return "(no data)"
    else:
      return value

  def missingValue_toCell(self, value, displayLimit=50):

    '''
    If no chars are missing, display as "complete".
    Add dotted circle to combining chars.
    '''

    if len(value) == 0:
      return "(complete)"
    else:
      chars = list(value)

      # Truncate to displayLimit
      if len(chars) > displayLimit:
        displayChars = chars[:displayLimit]
      else:
        displayChars = chars

      # Add dotted circle to marks
      for i, char in enumerate(displayChars):
        if unicodedata.combining(char):
          displayChars[i] = '◌' + char

      text = ' '.join(displayChars)

      # Add note if truncated
      if len(chars) > displayLimit:
        text = f"{text} {chr(0x200e)}(+ {len(chars)-displayLimit} more)"

      return text

  def addGlyphsCallback(self, sender=None):

    '''
    Add missing glyphs from selected languages to the font
    '''

    charset = [g.string for g in self.font.glyphs if g.unicode]
    glyphset = [g.name for g in self.font.glyphs]

    selected = self.langsTable.getSelectedIndexes()
    newGlyphs = []
    for i in selected:
      for char in self.langsTable.get()[i]['chars']:
        newGlyph = GSGlyph(char[-1])

        # Skip if codepoint is present in font
        if newGlyph.string in charset:
          continue
        # Skip if glyph name is present in font
        if newGlyph.name in glyphset:
          continue

        if newGlyph not in newGlyphs:
          newGlyphs.append(newGlyph)

    for g in newGlyphs:
      self.font.glyphs.append(g)

    # Dev mode can leave early at this point
    if getattr(Glyphs, "devMode", False):
      self.refreshLangs()
      return

    for g in newGlyphs:
      # Try to make glyph from components
      for layer in self.font.glyphs[g.name].layers:
        layer.makeComponents()

    tab = self.font.newTab()
    tab.text = ''.join([f"/{g.name} " for g in newGlyphs])
    tab.setTitle_("New glyphs added")
    self.refreshLangs()

  def scriptsUpdateMenu(self, sender=None):
    self.scriptsMenu = [
      dict(
        title=f"Look up {self.scriptsTable.getSelectedItems()[0]['name']} on Wikipedia",
        enabled=True,
        callback=self.scriptsWikipediaCallback,
      ),
      dict(
        title='Copy selected row',
        enabled=True,
        callback=self.scriptsCopySelectedRowCallback,
      ),
      dict(
        title='Copy all rows',
        enabled=True,
        callback=self.scriptsCopyAllRowsCallback,
      ),
    ]
    self.scriptsTable.setMenu(self.scriptsMenu)

  def langsUpdateMenu(self, sender=None):

    if len(self.langsTable.getSelectedIndexes()) == 1:
      language = self.langsTable.getSelectedItems()[0]['name']
    else:
      language = 'language'

    selectionHasMissingChars = any(
      len(r['chars']) for r in self.langsTable.getSelectedItems()
    )
    numRowsSelected = len(self.langsTable.getSelectedIndexes())

    self.langsMenu = [
      dict(
        title=f'Look up {language} on Wikipedia',
        enabled=numRowsSelected == 1,
        callback=self.langsWikipediaCallback,
      ),
      dict(
        title='Copy missing characters',
        enabled=selectionHasMissingChars,
        items=[
          dict(
            title='Space separated (marks keep dotted circles)',
            callback=self.copyMissingSpaceSeparatedCallback,
          ),
          dict(
            title='One per line',
            callback=self.copyMissingOnePerLineCallback,
          ),
          dict(
            title='Python list',
            callback=self.copyMissingPythonListCallback,
          ),
        ],
      ),
      dict(
        title='Copy missing codepoints',
        enabled=selectionHasMissingChars,
        items=[
          dict(
            title='One per line, Unicode notated',
            callback=self.copyMissingCodepointsUnicode,
          ),
          dict(
            title='One per line, hexadecimal',
            callback=self.copyMissingCodepointsHex,
          ),
          dict(
            title='One per line, decimal',
            callback=self.copyMissingCodepointsDec,
          ),
        ],
      ),
      dict(
        title='Copy selected rows',
        enabled=numRowsSelected,
        callback=self.langsCopySelectedRowsCallback,
      ),
      dict(
        title='Copy all rows',
        enabled=True,
        callback=self.langsCopyAllRowsCallback,
      ),
      dict(
        title='Completed characters',
        enabled=True,
        items=[
          dict(
            title='Select in Font View',
            callback=self.langsSelectCompleteInFontView,
          ),
          dict(
            title='Open in a new Edit View tab',
            callback=self.langsOpenCompleteInNewTab,
          ),
        ],
      ),
    ]
    self.langsTable.setMenu(self.langsMenu)
    # Auto-enabling is on by default but Vanilla doesn't support it
    self.langsTable._menu.setAutoenablesItems_(False)

  def scriptsCopySelectedRowCallback(self, sender=None):
    self.copyRows_fromTable_(
      rowIndexes=self.scriptsTable.getSelectedIndexes(),
      table=self.scriptsTable,
    )

  def scriptsCopyAllRowsCallback(self, sender=None):
    self.copyRows_fromTable_(
      rowIndexes=self.scriptsTable.getArrangedIndexes(),
      table=self.scriptsTable,
    )

  def langsCopySelectedRowsCallback(self, sender=None):
    self.copyRows_fromTable_(
      rowIndexes=self.langsTable.getSelectedIndexes(),
      table=self.langsTable,
    )

  def langsCopyAllRowsCallback(self, sender=None):
    self.copyRows_fromTable_(
      rowIndexes=self.langsTable.getArrangedIndexes(),
      table=self.langsTable,
    )

  def copyRows_fromTable_(self, rowIndexes, table):

    '''
    Copy List2 rows to pasteboard in CSV format with tab delimiters
    User can paste into Numbers or other spreadsheet apps
    '''

    rows = []
    for i in rowIndexes:
      rows.append(table.get()[i].values())
    utils.writePasteboardText_(utils.csvFromRows_(rows))

  def addDottedCircles(self, chars):
    for i, char in enumerate(chars):
      if unicodedata.combining(char):
        chars[i] = '◌' + char
    return chars

  def removeDottedCircles(self, chars):
    for i, char in enumerate(chars):
      if len(char) >= 2 and char[0] == '◌':
        chars[i] = char[1:]
    return chars

  def getSelectedMissingChars(self, marksAddDottedCircles=False):
    chars = []
    rows = self.langsTable.getSelectedItems()

    for row in rows:
      chars += row['chars']

    if marksAddDottedCircles:
      chars = self.addDottedCircles(chars)

    return sorted(list(set(chars)))

  def getSelectedCompleteChars(self, marksAddDottedCircles=False):
    selectedLangNames = [lang['name'] for lang in self.langsTable.getSelectedItems()]
    charLists = list(self.data.langs[self.data.langs['name'].isin(selectedLangNames)].loc[:, 'chars'])

    # Flatten nested lists
    chars = utils.flatten(charLists)

    # Sort and remove dupes
    chars = sorted(list(set(chars)))

    # Remove glyphs not present in the font
    chars = [c for c in chars if c in self.font.glyphs]

    if marksAddDottedCircles:
      chars = self.addDottedCircles(chars)

    return chars

  def copyMissingSpaceSeparatedCallback(self, sender=None):
    utils.writePasteboardText_(
      ' '.join(self.getSelectedMissingChars(marksAddDottedCircles=True))
    )

  def copyMissingOnePerLineCallback(self, sender=None):
    utils.writePasteboardText_('\n'.join(self.getSelectedMissingChars()) + '\n')

  def copyMissingPythonListCallback(self, sender=None):
    utils.writePasteboardText_(
      str(self.getSelectedMissingChars())
    )

  def copyMissingCodepointsUnicode(self, sender=None):
    utils.writePasteboardText_(
      '\n'.join([f"U+{ord(c):04X}" for c in self.getSelectedMissingChars()])
    )

  def copyMissingCodepointsHex(self, sender=None):
    utils.writePasteboardText_(
      '\n'.join([f"{ord(c):0X}" for c in self.getSelectedMissingChars()])
    )

  def copyMissingCodepointsDec(self, sender=None):
    utils.writePasteboardText_(
      '\n'.join([str(ord(c)) for c in self.getSelectedMissingChars()])
    )

  def langsSelectCompleteInFontView(self, sender=None):
    completed = self.getSelectedCompleteChars()
    self.font.selection = [self.font.glyphs[self.glyphInfoByChar_(c).name] for c in completed]

  def langsOpenCompleteInNewTab(self, sender=None):
    selectedLangNames = [r['name'] for r in self.langsTable.getSelectedItems()]
    completed = self.getSelectedCompleteChars()
    tab = self.font.newTab()
    tab.text = ''.join(
      [f"/{self.glyphInfoByChar_(c).name} " for c in completed]
    )
    tab.setTitle_(f"Completed for {', '.join(selectedLangNames)}")

  def langsWikipediaCallback(self, sender=None):
    utils.webbrowser.open(
      'https://en.wikipedia.org/w/index.php?search={language} language'.format(
        language=self.langsTable.getSelectedItems()[0]['name']
      )
    )

  def scriptsWikipediaCallback(self, sender=None):
    utils.webbrowser.open(
      'https://en.wikipedia.org/w/index.php?search={script} script'.format(
        script=self.scriptsTable.getSelectedItems()[0]['name']
      )
    )

  def langsSelectionCallback(self, sender=None):
    self.updateStatusBar()

  def showIncompleteCallback(self, sender=None):
    self.refreshLangs()

  def showCompleteCallback(self, sender=None):
    self.refreshLangs()

  def windowBecameKey(self, sender=None):
    self.refreshLangs()

  def openRepoCallback(self, sender=None):
    utils.webbrowser.open('https://github.com/justinpenner/TalkingLeaves')

  def checkForHyperglotUpdates(self):

    '''
    Hyperglot is updated frequently, with new languages being added often, so
    remind the user whenever updates are available.
    '''

    def callback(data):
      try:
        metadata = utils.parseJson_(data)
      except Exception:
        # Not critical, so if anything goes wrong we can just check for updates again on next launch
        return
      if utils.SimpleVersion(metadata['info']['version']) > utils.SimpleVersion(hyperglot.__version__):
        import sys
        pythonVersion = '.'.join([str(x) for x in sys.version_info][:3])
        message = f"Hyperglot {metadata['info']['version']} is now available, but you have {hyperglot.__version__}.\n\nTo update, copy the following command, then paste it into Terminal:\n\npip3 install --python-version={pythonVersion} --only-binary=:all: --target=\"/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages\" --upgrade hyperglot\n\nThen, restart Glyphs."
        Message(
          message,
          title='Update available',
          OKButton='Dismiss',
        )

    utils.getTextFromURL_successfulThen_("https://pypi.org/pypi/hyperglot/json", callback)


# List of system colours can be found here:
# NSColorList.colorListNamed_('System').allKeys()
class Colors:
  red = utils.getSystemColorByName_('systemRedColor')
  green = utils.getSystemColorByName_('systemGreenColor')
  placeholder = utils.getSystemColorByName_('placeholderTextColor')
  text = utils.getSystemColorByName_('textColor')


class TableCell(EditTextList2Cell):

  def set(self, value):
    self.editText.set(value)
    if value == "(no data)":
      self.getNSTextField().setTextColor_(Colors.placeholder)
    elif value == "(complete)":
      self.getNSTextField().setTextColor_(Colors.placeholder)
    else:
      self.getNSTextField().setTextColor_(None)


if __name__ == '__main__':
  main()
