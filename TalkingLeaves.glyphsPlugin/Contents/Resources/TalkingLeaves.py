#MenuTitle: TalkingLeaves
# -*- coding: utf-8 -*-

__doc__='''
TalkingLeaves is a tool for exploring languages that your font doesn't support yet.
This script (TalkingLeaves.py) can also be run directly from within Glyphs, if you put it in one of your Scripts folders.
'''

from GlyphsApp import *
from vanilla import (
  Window, Group, List2, Button, PopUpButton, SplitView, CheckBox
)
import json
from Foundation import NSURL, NSData
from AppKit import NSTextAlignmentRight, NSColor

if Glyphs.versionNumber < 3.2:
  import sys
  PKGS_PATH = '~/Library/Application Support/Glyphs 3/Scripts/site-packages'
  if PKGS_PATH not in sys.path:
    sys.path.append(PKGS_PATH)
import hyperglot, hyperglot.languages

MIN_COLUMN_WIDTH = 20

def main():

  Glyphs.clearLog()
  print("Running as script…")
  TalkingLeaves()

class TalkingLeaves:

  def __init__(self):

    self.font = Glyphs.font

    self.hg = hyperglot.languages.Languages()

    self._hgFindScriptsAndSpeakers()

    self.defaultScriptIndex = 0
    self.defaultScript = self.scripts[self.defaultScriptIndex]

    self.w = Window(
      (1000,600),
      f"Talking Leaves ({(Glyphs.currentDocument.filePath or self.font.familyName).split('/')[-1]} - {self.font.familyName})",
      minSize=(640,180),
    )

    scripts, scriptsHeaders = self.list2TableFrom2dArray_Headers_(
      self.speakersByScriptDesc.items(),
      ['Script','Speakers'],
      [100]
    )
    self.scriptsTable = List2(
      (0,0,-0,-0),
      scripts,
      columnDescriptions=scriptsHeaders,
      allowsMultipleSelection=False,
      # allowsEmptySelection=False,
      enableTypingSensitivity=True,
      selectionCallback=self._loadLangs,
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

    langsColHeaders = [
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
    for colHeader in langsColHeaders:
      colHeader['maxWidth'] = self.w.getPosSize()[2]
      colHeader['minWidth'] = MIN_COLUMN_WIDTH
      colHeader['sortable'] = True
      colHeader['identifier'] = colHeader['title']

    # langs = self.hgFindLanguagesByScript_(self.defaultScript)
    self.langsTable = List2(
      (0,0,-0,-0),
      self.hgFindLanguagesByScript_(self.defaultScript),
      columnDescriptions=langsColHeaders,
      enableTypingSensitivity=True,
    )
    self.langsTable.getNSScrollView().setHasHorizontalScroller_(0)

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
    self.w.flex = Group("auto")

    rules = [
      "H:|[top]|",
      "H:|-[flex(>=pad)]-gap-[showSupported]-gap-[showUnsupported]-gap-[addGlyphs]-pad-|",
      "V:|[top]-pad-[flex]-pad-|",
      "V:|[top]-pad-[showSupported]-pad-|",
      "V:|[top]-pad-[showUnsupported]-pad-|",
      "V:|[top]-pad-[addGlyphs]-pad-|",
    ]
    metrics = dict(pad=8,gap=8)
    self.w.addAutoPosSizeRules(rules,metrics)

    self.w.open()

    # Pane widths don't work when SplitView is in auto layout
    # Divider position has to be set after opening window
    self.w.top.getNSSplitView().setPosition_ofDividerAtIndex_(260,0)

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

      # Skip languages that don't have any orthographies listed
      if 'orthographies' not in self.hg[langCode]:
        continue

      orthos = [o for o in self.hg[langCode]['orthographies']
        if o['script'] == script
      ]
      for ortho in orthos:
        base = list(set(ortho['base']))
        unsupported = [c for c in base if c not in charset]
        if (len(unsupported)>=1 and self.w.showUnsupported.get()) \
        or (len(unsupported)==0 and self.w.showSupported.get()):
          items.append({
            'Language': self.hg[langCode]['name'],
            'Speakers': self.hg[langCode].get('speakers',-1),
            'Ortho. Status': ortho.get('status',''),
            'Lang. Status': self.hg[langCode].get('status',''),
            'Missing': charList(unsupported),
          })
    items = sorted(items,key=lambda x:len(x['Missing']))

    return items

  def _hgFindScriptsAndSpeakers(self):
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

    self.scripts = scripts
    self.speakersByScriptDesc = dict(sorted(speakers.items(),key=lambda x:x[1],reverse=True))

  def list2TableFrom2dArray_Headers_(self, array, headers, headerWidths=[], minWidthDefault=MIN_COLUMN_WIDTH):

    columnDescriptions = [
      dict(identifier=h,title=h)
      for h in headers
    ]
    for i,width in enumerate(headerWidths):
      columnDescriptions[i]['width'] = width

    for columnDescription in columnDescriptions:
      columnDescription['minWidth'] = minWidthDefault

    items = []
    for row in array:
      items.append({})
      for i,col in enumerate(row):
        items[-1][headers[i]] = col

    return items, columnDescriptions

  def _loadLangs(self, sender):
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
    self._loadLangs(sender)

  def showSupportedCallback(self, sender):
    self._loadLangs(sender)

  def refreshLangs(self, sender):
    self._loadLangs(sender)

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

def checkForHyperglotUpdates():
  url = NSURL.URLWithString_('https://api.github.com/repos/rosettatype/hyperglot/releases')
  r = NSData.dataWithContentsOfURL_(url)

  releases = json.loads(r.decode('utf-8'))

  if releases[0]['tag_name'] != hyperglot.__version__:
    raise Exception('Please upgrade Hyperglot, then restart Glyphs.\npython3.10 -m pip install --upgrade --target="/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages" hyperglot')

if __name__ == '__main__':
  main()