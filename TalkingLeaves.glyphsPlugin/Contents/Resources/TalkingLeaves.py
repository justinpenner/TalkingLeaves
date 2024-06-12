# MenuTitle: TalkingLeaves
# -*- coding: utf-8 -*-

__doc__ = '''
Developers: this script (TalkingLeaves.py) can be run directly from within
Glyphs. In your Scripts folder, add an alias to the TalkingLeaves parent
folder. Then you don't have to restart Glyphs each time you make changes to
this file, like you normally do when you're developing a plugin.
'''

from GlyphsApp import *
from vanilla import (
  Window, Group, List2, Button, HelpButton, SplitView, CheckBox, TextBox, EditTextList2Cell
)
import json, csv, io, webbrowser
from Foundation import NSURL, NSURLSession, NSPasteboard, NSString, NSColorList

# Tell older Glyphs where to find dependencies
if Glyphs.versionNumber < 3.2:
  import sys
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

    if not hyperglot:
      from vanilla import dialogs
      answer = dialogs.ask(
        messageText='Hyperglot module is missing',
        informativeText='Follow the installation instructions at https://github.com/justinpenner/TalkingLeaves#installation',
        buttonTitles=[(f'Open in browser', 1), ('Cancel', 0)],
      )
      if answer:
        webbrowser.open('https://github.com/justinpenner/TalkingLeaves#installation')
      return

    self.font = Glyphs.font
    self.windowSize = (1000, 600)
    # NSColorList.colorListNamed_('System').allKeys()
    self.colors = dict(
      red=NSColorList.colorListNamed_('System').colorWithKey_('systemRedColor'),
      green=NSColorList.colorListNamed_('System').colorWithKey_('systemGreenColor'),
      placeholder=NSColorList.colorListNamed_('System').colorWithKey_('placeholderTextColor'),
      text=NSColorList.colorListNamed_('System').colorWithKey_('textColor'),
    )

    self.startGUI()

    # Stand-alone developer mode uses a "fake" GlyphsApp API for testing 
    # without opening GlyphsApp.
    if getattr(Glyphs, "devMode", False):
      self._addDevTools()

    self.hg = hyperglot.languages.Languages()
    self.hgYaml = dict(hyperglot.languages.Languages())
    self.scriptsData = self.getScriptsAndSpeakers()
    self.scripts = list(self.scriptsData.keys())
    self.scriptsLangCount = {}
    self.defaultScriptIndex = 0
    self.defaultScript = self.scripts[self.defaultScriptIndex]
    self.glyphInfoByChar = {}
    self.charsByGlyphName = {}
    self.allMarks = []
    self.fillTables()

    self.checkForHyperglotUpdates()

  def _addDevTools(self):
    # Add menu item with Cmd-W shortcut to easily close window
    from AppKit import NSApplication, NSMenuItem
    app = NSApplication.sharedApplication()
    fileMenu = app.mainMenu().itemAtIndex_(0)
    fileMenu.submenu().addItemWithTitle_action_keyEquivalent_("Close Window", self.w.close, "w")

  def startGUI(self):

    self.scriptsColHeaders = [
      dict(
        title='Script',
        width=100,
      ),
      dict(
        title='L1 Speakers',
        width=100,
      ),
    ]
    self.langsColHeaders = [
      dict(
        title='Language',
        width=160,
      ),
      dict(
        title='L1 Speakers',
        width=100,
        valueToCellConverter=self.langSpeakersValue_toCell,
        cellClass=TableCell,
        cellClassArguments=dict(colors=self.colors),
      ),
      dict(
        title='Ortho. Status',
        width=94,
      ),
      dict(
        title='Lang. Status',
        width=94,
        valueToCellConverter=self.langStatusValue_toCell,
      ),
      dict(
        title='Missing',
        valueToCellConverter=self.missingValue_toCell,
        cellClass=TableCell,
        cellClassArguments=dict(colors=self.colors),
      ),
    ]
    for colHeader in self.scriptsColHeaders + self.langsColHeaders:
      colHeader['maxWidth'] = self.windowSize[0]
      colHeader['minWidth'] = MIN_COLUMN_WIDTH
      colHeader['sortable'] = True
      colHeader['identifier'] = colHeader['title']

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
    self.w.showSupported = CheckBox(
      "auto",
      "Show supported",
      sizeStyle="regular",
      value=False,
      callback=self.showSupportedCallback,
    )
    self.w.showUnsupported = CheckBox(
      "auto",
      "Show unsupported",
      sizeStyle="regular",
      value=True,
      callback=self.showUnsupportedCallback,
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
      "H:|-pad-[statusBar]-gap-[flex(>=pad)]-gap-[showSupported]-gap-[showUnsupported]-gap-[addGlyphs]-gap-[openRepo]-gap-|",
      "V:|[top]-pad-[statusBar]-pad-|",
      "V:|[top]-pad-[flex]-pad-|",
      "V:|[top]-pad-[showSupported]-pad-|",
      "V:|[top]-pad-[showUnsupported]-pad-|",
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

    scripts = self.tableFrom2dArray_withHeaders_(
      self.scriptsData.items(),
      self.scriptsColHeaders,
    )
    self.scriptsTable.set(scripts)
    self.langsTable.set(self.getLangsForScript_(self.defaultScript))

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

  def getLangsForScript_(self, script):

    '''
    Get languages for specified script, and compile data into an object
    formatted for a vanilla.List2 element
    '''

    charset = [g.string for g in self.font.glyphs if g.unicode]
    glyphset = [g.name for g in self.font.glyphs]
    items = []
    self.scriptsLangCount[script] = 0
    self.currentScriptUnsupported = 0
    self.currentScriptSupported = 0

    for langCode in self.hg.keys():

      lang = getattr(self.hg, langCode)
      langYaml = self.hgYaml[langCode]

      # Skip languages that don't have any orthographies listed
      if 'orthographies' not in lang:
        continue

      orthos = [o for o in lang['orthographies']
        if o['script'] == script
      ]

      if len(orthos):
        self.scriptsLangCount[script] += len(orthos)

      for ortho in orthos:

        # We just need unsupportedChars but it takes a few steps to get there
        # in somewhat-readable code
        orthography = hyperglot.orthography.Orthography(ortho)
        orthoBase = sorted(set(orthography.base_chars))
        orthoMarks = orthography.base_marks

        # For possible future use
        # orthoNumerals = list(set(ortho.get('numerals', '')))
        # orthoPunctuation = list(set(ortho.get('punctuation', '')))
        # orthoChars = orthoBase + orthoMarks + orthoNumerals + orthoPunctuation

        orthoGlyphNames = [self.glyphInfoForChar_(c).name for c in orthoBase + orthoMarks]

        supportedGlyphNames = []
        unsupportedGlyphNames = []
        for g in orthoGlyphNames:
          if g in glyphset:
            supportedGlyphNames.append(g)
          else:
            unsupportedGlyphNames.append(g)

        supportedChars = [self.charsByGlyphName[g] for g in supportedGlyphNames]
        unsupportedChars = [self.charsByGlyphName[g] for g in unsupportedGlyphNames]

        # Make display version of (un)supportedChars
        self.allMarks += orthoMarks
        def addDottedCircle(c):
          if c in self.allMarks:
            return "◌"+c
          else:
            return c
        unsupportedCharsDisplay = [addDottedCircle(c) for c in unsupportedChars]
        supportedCharsDisplay = [addDottedCircle(c) for c in supportedChars]

        if len(unsupportedChars):
          self.currentScriptUnsupported += 1
        else:
          self.currentScriptSupported += 1

        if (len(unsupportedChars) >= 1 and self.w.showUnsupported.get()) \
        or (len(unsupportedChars) == 0 and self.w.showSupported.get()):
          items.append({
            'ISO': langCode,
            'Language': lang.get('preferred_name', lang['name']),
            'L1 Speakers': langYaml.get('speakers', -1),
            'Ortho. Status': ortho.get('status', ''),
            'Lang. Status': lang.get('status', ''),
            'Missing': charList(unsupportedCharsDisplay),
            'Supported': charList(supportedCharsDisplay),
          })
    items = sorted(items, key=lambda x: len(x['Missing']))

    return items

  def glyphInfoForChar_(self, c):

    '''
    Get glyph info for char, cache results
    '''
    if c not in self.glyphInfoByChar:
      info = Glyphs.glyphInfoForUnicode(ord(c), self.font)
      self.glyphInfoByChar[c] = info
      self.charsByGlyphName[info.name] = c
    return self.glyphInfoByChar[c]

  def getScriptsAndSpeakers(self):

    '''
    Get script names and speaker counts, return as sorted dict
    '''
    scripts = []
    speakers = {}
    for lang in self.hg.values():
      orthos = lang.get('orthographies', [])
      for ortho in orthos:
        if ortho['script'] not in scripts:
          scripts.append(ortho['script'])
          speakers[ortho['script']] = 0
        speakers[ortho['script']] += lang.get('speakers', 0)
    return dict(sorted(speakers.items(), key=lambda x: x[1], reverse=True))

  def tableFrom2dArray_withHeaders_(self, array, columnDescriptions):

    '''
    Convert a 2D array of data fields and a list of column headers into an
    object formatted for vanilla.List2
    '''
    items = []
    for row in array:
      items.append({})
      for i, col in enumerate(row):
        items[-1][columnDescriptions[i]['identifier']] = col
    return items

  def refreshLangs(self, sender):

    '''
    Load/reload languages for the currently selected script
    '''

    if hasattr(self, 'scriptsTable') and len(self.scriptsTable.getSelectedIndexes()):
      self.currentScript = self.scriptsTable.get()[self.scriptsTable.getSelectedIndexes()[0]]['Script']
    else:
      self.currentScript = self.defaultScript

    items = self.getLangsForScript_(self.currentScript)
    self.langsTable.set(items)
    self.langsFormatting()
    self.updateStatusBar()

  def updateStatusBar(self):

    '''
    Write some useful info in the bottom of the window
    '''

    self.selectedChars = []
    for i in self.langsTable.getSelectedIndexes():
      self.selectedChars.extend(self.langsTable.get()[i]['Missing'].split())
    self.selectedChars = set(self.selectedChars)

    m = "{supported}/{total} = {percent}% {script} supported".format(
      script=self.currentScript,
      total=self.scriptsLangCount[self.currentScript],
      unsupported=self.currentScriptUnsupported,
      supported=self.currentScriptSupported,
      percent=self.currentScriptSupported*100//self.scriptsLangCount[self.currentScript],
    )
    langSel = len(self.langsTable.getSelectedIndexes())
    if langSel:
      m += " ({langs} langs, {chars} missing chars selected)".format(
        langs=langSel,
        chars=len(self.selectedChars),
      )
    self.w.statusBar.set(m)

  def langsFormatting(self):
    # TODO
    # langs.Speakers==(no data): grey
    # langs.LangStatus==(no data): grey

    # Spent far too much time trying to figure this out. Next thing to try:
    # https://github.com/robotools/vanilla/issues/91

    # colIdx = self.langsTable.getNSTableView().columnWithIdentifier_('L1 Speakers')
    # col = self.langsTable.getNSTableView().tableColumns()[colIdx]
    # print(col)
    # col.headerCell().setTextColor_(NSColor.placeholderTextColor())
    # col.headerCell().setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(1,0,0,1))
    # col.setHidden_(True)
    # print(NSColor.placeholderTextColor())
    # obj = col.dataCell()
    # print(obj)
    # print(type(obj))
    # for d in sorted(dir(obj)):
    #   print(d)
    pass

  def langSpeakersValue_toCell(self, value):

    '''
    Unknown speaker count has already been set to -1, so display it in the
    cell as "no data"
    '''
    if value == -1:
      return "(no data)"
    else:
      return value

  def langStatusValue_toCell(self, value):

    '''
    Unknown language status is "", so display it as "no data"
    '''
    if value == "":
      return "(no data)"
    else:
      return value

  def missingValue_toCell(self, value):

    '''
    If no chars are missing, display as "complete"
    '''
    if value == "":
      return "(complete)"
    else:
      return value

  def addGlyphsCallback(self, sender):

    '''
    Add missing glyphs from selected languages to the font
    '''

    charset = [g.string for g in self.font.glyphs if g.unicode]
    glyphset = [g.name for g in self.font.glyphs]

    selected = self.langsTable.getSelectedIndexes()
    newGlyphs = []
    for i in selected:
      for char in self.langsTable.get()[i]['Missing'].split():
        newGlyph = GSGlyph(char[-1])

        # Skip if codepoint is present in font
        if newGlyph.string in charset:
          continue
        # Skip if glyph name is present in font
        if newGlyph.name in glyphset:
          continue

        if newGlyph not in newGlyphs:
          newGlyphs.append(newGlyph)

    tab = self.font.newTab()
    for g in newGlyphs:
      self.font.glyphs.append(g)

      # Try to make glyph from components
      for layer in self.font.glyphs[g.name].layers:
        layer.makeComponents()

    tab.text = ''.join([f"/{g.name} " for g in newGlyphs])
    tab.setTitle_("New glyphs added")
    self.refreshLangs(sender)

  def scriptsUpdateMenu(self, sender=None):
    self.scriptsMenu = [
      dict(
        title=f"Look up {getattr(self,'currentScript',self.defaultScript)} on Wikipedia",
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
      language = self.langsTable.getSelectedItems()[0]['Language']
    else:
      language = 'language'

    selectionHasMissingChars = any(
      len(r['Missing']) for r in self.langsTable.getSelectedItems()
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
        title='Supported characters',
        enabled=True,
        items=[
          dict(
            title='Select in Font View',
            callback=self.langsSelectSupportedInFontView,
          ),
          dict(
            title='Open in a new Edit View tab',
            callback=self.langsOpenSupportedInNewTab,
          ),
        ],
      ),
    ]
    self.langsTable.setMenu(self.langsMenu)
    # Auto-enabling is on by default but Vanilla doesn't support it
    self.langsTable._menu.setAutoenablesItems_(False)

  def scriptsCopySelectedRowCallback(self, sender):
    self.copyRows_fromTable_(
      rowIndexes=self.scriptsTable.getSelectedIndexes(),
      table=self.scriptsTable,
    )

  def scriptsCopyAllRowsCallback(self, sender):
    self.copyRows_fromTable_(
      rowIndexes=self.scriptsTable.getArrangedIndexes(),
      table=self.scriptsTable,
    )

  def langsCopySelectedRowsCallback(self, sender):
    self.copyRows_fromTable_(
      rowIndexes=self.langsTable.getSelectedIndexes(),
      table=self.langsTable,
    )

  def langsCopyAllRowsCallback(self, sender):
    self.copyRows_fromTable_(
      rowIndexes=self.langsTable.getArrangedIndexes(),
      table=self.langsTable,
    )

  def copyRows_fromTable_(self, rowIndexes, table):

    '''
    Copy List2 rows to pasteboard in CSV format with tab delimiters
    User can paste into Numbers or other spreadsheet apps
    '''

    text = io.StringIO('')
    writer = csv.writer(text, dialect='excel-tab')

    for i in rowIndexes:
      writer.writerow(table.get()[i].values())

    self.copyTextToPasteboard(text.getvalue())

  def copyTextToPasteboard(self, text):
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.writeObjects_([NSString(text)])

  def getSelectedMissingChars(self, marksRemoveDottedCircles=True):
    missingChars = []
    for row in self.langsTable.getSelectedItems():
      missingChars += row['Missing'].split()

    if marksRemoveDottedCircles:
      for i,c in enumerate(missingChars):
        if len(c) == 2 and c[0] == '◌':
          missingChars[i] = missingChars[i][1]

    return sorted(list(set(missingChars)))

  def getSelectedSupportedChars(self, marksRemoveDottedCircles=True):
    supportedChars = []
    for row in self.langsTable.getSelectedItems():
      supportedChars += row['Supported'].split()

    if marksRemoveDottedCircles:
      for i,c in enumerate(supportedChars):
        if len(c) == 2 and c[0] == '◌':
          supportedChars[i] = supportedChars[i][1]

    return sorted(list(set(supportedChars)))

  def copyMissingSpaceSeparatedCallback(self, sender):
    self.copyTextToPasteboard(
      ' '.join(self.getSelectedMissingChars(marksRemoveDottedCircles=False))
    )

  def copyMissingOnePerLineCallback(self, sender):
    self.copyTextToPasteboard('\n'.join(self.getSelectedMissingChars())+'\n')

  def copyMissingPythonListCallback(self, sender):
    self.copyTextToPasteboard(
      '["'+'", "'.join(self.getSelectedMissingChars())+'"]'
    )

  def copyMissingCodepointsUnicode(self, sender):
    self.copyTextToPasteboard(
      '\n'.join([f"U+{ord(c):04X}" for c in self.getSelectedMissingChars()])
    )

  def copyMissingCodepointsHex(self, sender):
    self.copyTextToPasteboard(
      '\n'.join([f"{ord(c):0X}" for c in self.getSelectedMissingChars()])
    )

  def copyMissingCodepointsDec(self, sender):
    self.copyTextToPasteboard(
      '\n'.join([str(ord(c)) for c in self.getSelectedMissingChars()])
    )

  def langsSelectSupportedInFontView(self, sender):
    supported = self.getSelectedSupportedChars()
    self.font.selection = [self.font.glyphs[self.glyphInfoByChar[c].name] for c in supported]

  def langsOpenSupportedInNewTab(self, sender):
    selectedLangNames = [r['Language'] for r in self.langsTable.getSelectedItems()]
    supported = self.getSelectedSupportedChars()
    tab = self.font.newTab()
    tab.text = ''.join(
      [f"/{self.glyphInfoByChar[c].name} " for c in supported]
    )
    tab.setTitle_(f"Supported for {', '.join(selectedLangNames)}")

  def langsWikipediaCallback(self, sender):
    webbrowser.open(
      'https://en.wikipedia.org/w/index.php?search={language} language'.format(
        language=self.langsTable.getSelectedItems()[0]['Language']
      )
    )

  def scriptsWikipediaCallback(self, sender):
    webbrowser.open(
      'https://en.wikipedia.org/w/index.php?search={script} script'.format(
        script=self.scriptsTable.getSelectedItems()[0]['Script']
      )
    )

  def langsSelectionCallback(self, sender):
    self.updateStatusBar()

  def showUnsupportedCallback(self, sender):
    self.refreshLangs(sender)

  def showSupportedCallback(self, sender):
    self.refreshLangs(sender)

  def windowBecameKey(self, sender):
    self.refreshLangs(sender)

  def openRepoCallback(self, sender):
    webbrowser.open('https://github.com/justinpenner/TalkingLeaves')

  def checkForHyperglotUpdates(self):

    '''
    Hyperglot is updated frequently, with new languages being added often, so
    remind the user whenever updates are available.
    '''

    url = NSURL.URLWithString_("https://pypi.org/pypi/hyperglot/json")
    def callback(data, response, error):
      if data and response and not error:
        metadata = json.loads(data.decode('utf-8'))
        if metadata['info']['version'] != hyperglot.__version__:
          import sys
          pythonVersion = '.'.join([str(x) for x in sys.version_info][:3])
          message = f"Hyperglot {metadata['info']['version']} is now available, but you have {hyperglot.__version__}.\n\nTo update, copy the following command, then paste it into Terminal:\n\npip3 install --python-version={pythonVersion} --only-binary=:all: --target=\"/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages\" --upgrade hyperglot\n\nThen, restart Glyphs."
          Message(
            message,
            title='Update available',
            OKButton='Dismiss',
          )

    dataTask = NSURLSession.sharedSession().dataTaskWithURL_completionHandler_(url, callback)
    dataTask.resume()

class charList(str):

  '''
  A list of chars that acts like a string, but sorts by the list length.
  (This is used for the Missing column)
  '''

  def __new__(self, l):
    self.l = l
    return str.__new__(self, ' '.join(l))

  def __init__(self, l):
    self.l = l
    self.__str__ = ' '.join(l)
  
  def __lt__(self, other):
    return self.listLen() < other.listLen()

  def listLen(self):
    return len(self.l)

class TableCell(EditTextList2Cell):

  def __init__(self, **kwargs):
    self.colors = kwargs.pop('colors')
    super().__init__(**kwargs)

  def set(self, value):
    self.editText.set(value)
    if value == "(no data)":
      self.getNSTextField().setTextColor_(self.colors['placeholder'])
    elif value == "(complete)":
      self.getNSTextField().setTextColor_(self.colors['placeholder'])
    else:
      self.getNSTextField().setTextColor_(self.colors['text'])

if __name__ == '__main__':
  main()
