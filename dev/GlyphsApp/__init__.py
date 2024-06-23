# (Fake)GlyphsApp

from glyphsLib import GSFont
import xml.etree.ElementTree as etree

DOCUMENTOPENED = "GSDocumentWasOpenedNotification"
DOCUMENTDIDCLOSE = "GSDocumentDidCloseNotification"
WINDOW_MENU = "WINDOW_MENU"


class cfg:
  glyphsFile = "test.glyphs"
  import sys
  if len(sys.argv) >= 2:
    glyphsFile = sys.argv[1]

class GSApplication:
  def __init__(self):
    self.lang = "en"
    self.versionNumber = 3.2
    self.menu = {WINDOW_MENU: []}
    self.documents = [0]
    self.font = None
    self.devMode = True
    self.glyphData = self._loadGlyphData()

  def _loadGlyphData(self):
    path = "/Applications/Glyphs 3.app/Contents/Frameworks/GlyphsCore.framework/Versions/A/Resources/GlyphData.xml"
    data = etree.parse(path)
    root = data.getroot()
    return root

  def glyphInfoForUnicode(self, code, font=None):
    codeStr = f"{code:04X}"
    for glyph in self.glyphData:
      if "unicode" in glyph.attrib and glyph.attrib["unicode"] == codeStr:
        return GSGlyphInfo(code, dict(glyph.attrib))
    return GSGlyphInfo(code, {"unicode": codeStr})

  def localize(self, strings):
    return strings[self.lang]

  def addCallback(self, callback, eventName):
    pass

Glyphs = GSApplication()

class GSDocument:
  def __init__(self, font, filePath):
    self.font = font
    self.filePath = filePath

class GSGlyph:
  def __init__(self, char):
    self.string = char
    self.name = Glyphs.glyphInfoForUnicode(ord(char))
    self.layers = []

class GSGlyphInfo:
  def __init__(self, code, attrib):
    self.name = attrib.get("name", "")
    self.attrib = attrib

def Message(message, title='Alert', OKButton=None):
  print(title)
  print(message)

Glyphs.font = GSFont(cfg.glyphsFile)
Glyphs.font.filepath = cfg.glyphsFile
Glyphs.currentDocument = GSDocument(Glyphs.font, Glyphs.font.filepath)
Glyphs.font.parent = Glyphs.currentDocument
