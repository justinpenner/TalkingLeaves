#MenuTitle: TalkingLeaves
# -*- coding: utf-8 -*-

__doc__='''
Developers: this script (TalkingLeaves.py) can be run directly from within
Glyphs. In your Scripts folder, add an alias to the TalkingLeaves parent
folder. Then you don't have to restart Glyphs each time you make changes to
this file, like you normally do when you're developing a plugin.
'''

from GlyphsApp import *
from vanilla import (
  Window, Group, List2, Button, HelpButton, SplitView, CheckBox, TextBox
)
import json
from Foundation import NSURL, NSData
import webbrowser

# Tell older Glyphs where to find dependencies
if Glyphs.versionNumber < 3.2:
  import sys
  from pathlib import Path
  PKGS_PATH = str(Path('~/Library/Application Support/Glyphs 3/Scripts/site-packages').expanduser())
  if PKGS_PATH not in sys.path:
    scriptsPath = str(Path('~/Library/Application Support/Glyphs 3/Scripts').expanduser())
    pos = sys.path.index(scriptsPath)+1
    sys.path.insert(pos,PKGS_PATH)

try:
  import hyperglot
  import hyperglot.languages
  import hyperglot.language
except ModuleNotFoundError:
  hyperglot = None

try:
  from urlreader import URLReader
except ModuleNotFoundError:
  URLReader = None

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
        buttonTitles=[(f'Open in browser',1),('Cancel',0)],
      )
      if answer:
        webbrowser.open('https://github.com/justinpenner/TalkingLeaves#installation')
      return

    self.font = Glyphs.font
    self.windowSize = (1000, 600)
    self.startGUI()

    self.hg = hyperglot.languages.Languages()
    self.hgYaml = dict(hyperglot.languages.Languages())
    self.scriptsData = self.getScriptsAndSpeakers()
    self.scripts = list(self.scriptsData.keys())
    self.scriptsLangCount = {}
    self.defaultScriptIndex = 0
    self.defaultScript = self.scripts[self.defaultScriptIndex]
    self.fillTables()

    self.checkForHyperglotUpdates()

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
      minSize=(640,180),
    )
    self.scriptsTable = List2(
      (0,0,-0,-0),
      [],
      columnDescriptions=self.scriptsColHeaders,
      allowsMultipleSelection=False,
      enableTypingSensitivity=True,
      selectionCallback=self.refreshLangs,
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
      (0,0,-0,-0),
      [],
      columnDescriptions=self.langsColHeaders,
      enableTypingSensitivity=True,
      selectionCallback=self.langsSelectionCallback,
    )
    panes = [
      dict(view=self.scriptsTable,identifier="scripts",canCollapse=False,minSize=MIN_COLUMN_WIDTH),
      dict(view=self.langsTable,identifier="langs",canCollapse=False,minSize=MIN_COLUMN_WIDTH),
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
    metrics = dict(pad=12,gap=16)
    self.w.addAutoPosSizeRules(rules,metrics)

    # Open GUI
    self.w.open()

    # Pane widths don't work when SplitView is in auto layout
    # Divider position has to be set after opening window
    self.w.top.getNSSplitView().setPosition_ofDividerAtIndex_(260,0)

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
    langCodes = self.hg.keys()
    items = []
    self.scriptsLangCount[script] = 0
    self.currentScriptUnsupported = 0
    self.currentScriptSupported = 0

    for langCode in langCodes:

      langYaml = self.hgYaml[langCode]
      lang = getattr(self.hg,langCode)

      # Skip languages that don't have any orthographies listed
      if 'orthographies' not in lang:
        continue

      orthos = [o for o in lang['orthographies']
        if o['script'] == script
      ]

      if len(orthos):
        self.scriptsLangCount[script] += len(orthos)

      for ortho in orthos:
        base = list(set(ortho['base']))
        unsupported = [c for c in base if c not in charset]
        if len(unsupported):
          self.currentScriptUnsupported += 1
        else:
          self.currentScriptSupported += 1

        if (len(unsupported)>=1 and self.w.showUnsupported.get()) \
        or (len(unsupported)==0 and self.w.showSupported.get()):
          items.append({
            'Language': lang.get('preferred_name',lang['name']),
            'L1 Speakers': langYaml.get('speakers',-1),
            'Ortho. Status': ortho.get('status',''),
            'Lang. Status': lang.get('status',''),
            'Missing': charList(unsupported),
          })
    items = sorted(items,key=lambda x:len(x['Missing']))

    return items

  def getScriptsAndSpeakers(self):
    '''
    Get script names and speaker counts, return as sorted dict
    '''
    scripts = []
    speakers = {}
    for lang in self.hg.values():
      orthos = lang.get('orthographies',[])
      for ortho in orthos:
        if ortho['script'] not in scripts:
          scripts.append(ortho['script'])
          speakers[ortho['script']] = 0
        speakers[ortho['script']] += lang.get('speakers',0)
    return dict(sorted(speakers.items(),key=lambda x:x[1],reverse=True))

  def tableFrom2dArray_withHeaders_(self, array, columnDescriptions):
    '''
    Convert a 2D array of data fields and a list of column headers into an
    object formatted for vanilla.List2
    '''
    items = []
    for row in array:
      items.append({})
      for i,col in enumerate(row):
        items[-1][columnDescriptions[i]['identifier']] = col
    return items

  def refreshLangs(self, sender):
    '''
    Load/reload languages for the currently selected script
    '''

    if hasattr(self,'scriptsTable'):
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

    m = "{supported}/{total}={percent}% {script} supported".format(
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
    selected = self.langsTable.getSelectedIndexes()
    newGlyphs = []
    for i in selected:
      for char in self.langsTable.get()[i]['Missing'].split():
        newGlyph = GSGlyph(char)
        if newGlyph not in newGlyphs and char not in charset:
          newGlyphs.append(newGlyph)

    tab = self.font.newTab()
    for g in newGlyphs:
      self.font.glyphs.append(g)
    tab.text = ''.join([f"/{g.name} " for g in newGlyphs])
    tab.setTitle_("New glyphs added")
    self.refreshLangs(sender)

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

    if URLReader == None:
      print("urlreader is missing! Check README.md for instructions to install it. TalkingLeaves will work without it, but it won't be able to notify you when Hyperglot updates are available.")
      return

    url = ('https://pypi.org/pypi/hyperglot/json')
    def callback(url, data, error):
      if url and data and not error:
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
    URLReader().fetch(url, callback)

class charList(str):
  '''
  A list of chars that acts like a string, but sorts by the list length.
  (This is used for the Missing column)
  '''

  def __new__(self, l=[]):
    self.l = l
    return str.__new__(self, ' '.join(l))

  def __init__(self, l=[]):
    self.l = l
    self.__str__ = ' '.join(l)
  
  def __lt__(self, other):
    return self.listLen() < other.listLen()

  def listLen(self):
    return len(self.l)

if __name__ == '__main__':
  main()