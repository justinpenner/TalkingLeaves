#MenuTitle: TalkingLeaves
# -*- coding: utf-8 -*-

__doc__='''
Developers: this script (TalkingLeaves.py) can be run directly from within Glyphs. In your Scripts folder, add an alias to the TalkingLeaves parent folder. Then you don't have to restart Glyphs each time you make changes to this file, like you normally do when you're developing a plugin.
'''

from GlyphsApp import *
from vanilla import (
  Window, Group, List2, Button, HelpButton, SplitView, CheckBox
)
import json
from Foundation import NSURL, NSData

# Tell older Glyphs where to find dependencies
if Glyphs.versionNumber < 3.2:
  import sys
  PKGS_PATH = '~/Library/Application Support/Glyphs 3/Scripts/site-packages'
  if PKGS_PATH not in sys.path:
    sys.path.append(PKGS_PATH)

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
  TalkingLeaves()

class TalkingLeaves:

  def __init__(self):

    if not hyperglot:
      Message("Hyperglot module is missing. Follow the installation instructions in README.md.", title='Cannot load TalkingLeaves', OKButton="OK")
      return

    self.font = Glyphs.font
    self.windowSize = (1000, 600)
    self.startGUI()

    self.hg = hyperglot.languages.Languages()
    self.hgYaml = dict(hyperglot.languages.Languages())
    self.scriptsData = self.getScriptsAndSpeakers()
    self.scripts = list(self.scriptsData.keys())
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
        title='Speakers',
        width=100,
      ),
    ]
    self.langsColHeaders = [
      dict(
        title='Language',
        width=160,
      ),
      dict(
        title='Speakers',
        width=100,
        valueToCellConverter=self.langSpeakersValue_ToCell,
      ),
      dict(
        title='Ortho. Status',
        width=94,
      ),
      dict(
        title='Lang. Status',
        width=94,
        valueToCellConverter=self.langStatusValue_ToCell,
      ),
      dict(
        title='Missing',
        valueToCellConverter=self.missingValue_ToCell,
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
      f"Talking Leaves ({(Glyphs.currentDocument.filePath or self.font.familyName).split('/')[-1]} - {self.font.familyName})",
      minSize=(640,180),
    )
    self.scriptsTable = List2(
      (0,0,-0,-0),
      [],
      columnDescriptions=self.scriptsColHeaders,
      allowsMultipleSelection=False,
      enableTypingSensitivity=True,
      selectionCallback=self.loadLangs,
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
    self.w.flex = Group("auto")
    rules = [
      "H:|[top]|",
      "H:|-pad-[openRepo]-[flex(>=pad)]-gap-[showSupported]-gap-[showUnsupported]-gap-[addGlyphs]-pad-|",
      "V:|[top]-pad-[openRepo]-pad-|",
      "V:|[top]-pad-[flex]-pad-|",
      "V:|[top]-pad-[showSupported]-pad-|",
      "V:|[top]-pad-[showUnsupported]-pad-|",
      "V:|[top]-pad-[addGlyphs]-pad-|",
    ]
    metrics = dict(pad=8,gap=8)
    self.w.addAutoPosSizeRules(rules,metrics)

    # Open GUI
    self.w.open()

    # Pane widths don't work when SplitView is in auto layout
    # Divider position has to be set after opening window
    self.w.top.getNSSplitView().setPosition_ofDividerAtIndex_(260,0)


  def fillTables(self):
    scripts = self.list2TableFrom2dArray_Headers_(
      self.scriptsData.items(),
      self.scriptsColHeaders,
    )
    self.scriptsTable.set(scripts)
    self.langsTable.set(self.hgFindLanguagesByScript_(self.defaultScript))

    # Fix some UI details…

    # This triggers selectionCallback, which can't be done at instantiation
    # time, or it will refresh langTable which doesn't exist yet.
    self.scriptsTable._tableView.setAllowsEmptySelection_(False)
    self.scriptsTable.setSelectedIndexes([self.defaultScriptIndex])

    # Tables begin scrolled to 2nd row for some reason
    self.scriptsTable.getNSTableView().scrollRowToVisible_(0)
    self.langsTable.getNSTableView().scrollRowToVisible_(0)


  def hgFindLanguagesByScript_(self, script):
    charset = [g.string for g in self.font.glyphs if g.unicode]

    langCodes = self.hg.keys()

    items = []
    for langCode in langCodes:

      # if langCode == 'fub':
        # print(self.hgYaml[langCode])
        # print(self.hg.get(langCode))
        # ace = self.hg.ace
        # print(dict(getattr(self.hg,langCode)))
        # print(ace)

      langYaml = self.hgYaml[langCode]
      lang = getattr(self.hg,langCode)

      # Skip languages that don't have any orthographies listed
      if 'orthographies' not in lang:
        continue

      orthos = [o for o in lang['orthographies']
        if o['script'] == script
      ]
      for ortho in orthos:
        base = list(set(ortho['base']))
        unsupported = [c for c in base if c not in charset]
        if (len(unsupported)>=1 and self.w.showUnsupported.get()) \
        or (len(unsupported)==0 and self.w.showSupported.get()):
          items.append({
            'Language': lang['name'],
            'Speakers': langYaml.get('speakers',-1),
            'Ortho. Status': ortho.get('status',''),
            'Lang. Status': langYaml.get('status',''),
            'Missing': charList(unsupported),
          })
    items = sorted(items,key=lambda x:len(x['Missing']))

    return items

  def getScriptsAndSpeakers(self):
    '''
    Initialize lists of scripts
    '''
    scripts = []
    speakers = {}
    for lang in self.hg.values():
      orthos = lang.get('orthographies',[])
      for ortho in orthos:
        if ortho['script'] not in scripts:
          # scripts[ortho['script']] = 0
          scripts.append(ortho['script'])
          speakers[ortho['script']] = 0
        speakers[ortho['script']] += lang.get('speakers',0)
    return dict(sorted(speakers.items(),key=lambda x:x[1],reverse=True))

  def list2TableFrom2dArray_Headers_(self, array, columnDescriptions):
    items = []
    for row in array:
      items.append({})
      for i,col in enumerate(row):
        items[-1][columnDescriptions[i]['identifier']] = col
    return items

  def loadLangs(self, sender):
    if hasattr(self,'scriptsTable'):
      script = self.scriptsTable.get()[self.scriptsTable.getSelectedIndexes()[0]]['Script']
    else:
      script = self.defaultScript

    items = self.hgFindLanguagesByScript_(script)
    self.langsTable.set(items)
    self.langsFormatting()

  def langsFormatting(self):
    # TODO
    # langs.Speakers==(no data): grey
    # langs.LangStatus==(no data): grey

    # Spent far too much time trying to figure this out. Next thing to try:
    # https://github.com/robotools/vanilla/issues/91

    # colIdx = self.langsTable.getNSTableView().columnWithIdentifier_('Speakers')
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

  def langSpeakersValue_ToCell(self, value):
    if value == -1:
      return "(no data)"
    else:
      return value

  def langStatusValue_ToCell(self, value):
    if value == "":
      return "(no data)"
    else:
      return value

  def missingValue_ToCell(self, value):
    if value == "":
      return "(complete)"
    else:
      return value

  def addGlyphsCallback(self, sender):
    selected = self.langsTable.getSelectedIndexes()
    newGlyphs = []
    for i in selected:
      for char in self.langsTable.get()[i]['Missing'].split():
        newGlyph = GSGlyph(char)
        if newGlyph not in newGlyphs:
          newGlyphs.append(newGlyph)
    print(newGlyphs)
    tab = self.font.newTab()
    for g in newGlyphs:
      self.font.glyphs.append(g)
    tab.text = ''.join([f"/{g.name} " for g in newGlyphs])
    tab.setTitle_("New glyphs added")

  def langsSelectionCallback(self, sender):
    pass

  def showUnsupportedCallback(self, sender):
    self.loadLangs(sender)

  def showSupportedCallback(self, sender):
    self.loadLangs(sender)

  def refreshLangs(self, sender):
    self.loadLangs(sender)

  def openRepoCallback(self, sender):
    import webbrowser
    webbrowser.open('https://github.com/justinpenner/TalkingLeaves')

  def checkForHyperglotUpdates(self):
    if URLReader == None:
      print("urlreader is missing! Check README.md for instructions to install it. TalkingLeaves will work without it, but it won't be able to notify you when Hyperglot updates are available.")
      return

    url = ('https://api.github.com/repos/rosettatype/hyperglot/releases')
    def callback(url, data, error):
      if url and data and not error:
        releases = json.loads(data.decode('utf-8'))
        if releases[0]['tag_name'] != hyperglot.__version__:
          import sys
          if sys.executable.split('/')[-1] == 'Glyphs 3':
            message = f"Hyperglot {releases[0]['tag_name']} is now available, but you have {hyperglot.__version__}.\n\nTo update, copy the following command, then paste it into Terminal:\n\n~/Library/Application\ Support/Glyphs\ 3/Repositories/GlyphsPythonPlugin/Python.framework/Versions/Current/bin/pip3 install --target=\"/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages\" -U hyperglot"
          else:
            message = f"Hyperglot {releases[0]['tag_name']} is now available, but you have {hyperglot.__version__}.\n\nTo update, copy the following command, then paste it into Terminal:\n\npip install -U hyperglot\n\nHint: make sure Glyphs is running the same Python as your pip command."
          Message(
            message,
            title='Update available',
            OKButton='Dismiss',
          )
    URLReader().fetch(url, callback)

class charList(str):
  '''
  A list of chars that acts like a string, but sorts by the list length.
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