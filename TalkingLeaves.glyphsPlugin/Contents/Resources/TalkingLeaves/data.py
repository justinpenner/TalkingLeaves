import time
import pandas as pd
from GlyphsApp import Glyphs


class Data:

  '''
  Collection of languages and scripts.
  '''

  def __init__(self):
    self.loadFromSource(DataSourceHyperglot)

  def __repr__(self):
    text = "Languages: \n"
    for lang in self.values():
      text += f"  {lang}\n"
    return text

  def loadFromSource(self, dataSource):
    ds = dataSource()
    self.langs = pd.DataFrame(ds.langs.values())
    self.scripts = pd.DataFrame(ds.scripts.values())

  def scriptsAsDict(self):
    frame = self.scripts.filter(['name', 'speakers']).sort_values('speakers', ascending=False)
    table = frame.values.tolist()
    return dict(table)

  def tableFromFrame(self, frame):
    '''
    Convert a 2D array of data fields and a list of column headers into an
    object formatted for vanilla.List2
    '''
    items = frame.to_dict('index')
    return list(items.values())

  def scriptsAsTable(self):
    return self.tableFromFrame(
      self.scripts.filter(['name', 'speakers']).sort_values('speakers', ascending=False)
    )

  def langsAsTable(self, scriptName, font, showIncomplete, showComplete, progressCallback=None):
    scriptId = self.scripts[self.scripts['name'] == scriptName].reset_index().at[0, 'id']
    frame = self.langs[self.langs['scriptId'] == scriptId]
    frame = frame.filter(['name', 'speakers', 'ortho_status', 'lang_status', 'chars'])

    charset = {g.string for g in font.glyphs if g.unicode}
    glyphNames = {g.name for g in font.glyphs}
    missingCache = {}
    uniqueChars = list(dict.fromkeys(c for chars in frame['chars'] for c in chars))
    totalChars = len(uniqueChars)
    processedChars = 0
    lastProgressUpdate = 0

    self.updateProgress_(progressCallback, 'Scanning characters', 0, totalChars)

    # Resolve each unique character once per script
    for c in uniqueChars:
      self.charMissingFromFont_(c, font, charset, glyphNames, missingCache)
      processedChars += 1
      if (
        progressCallback and (
        processedChars == totalChars or
        processedChars == 1 or
        time.perf_counter() - lastProgressUpdate >= 0.03
        )
      ):
        progressCallback('Scanning characters', processedChars, totalChars)
        lastProgressUpdate = time.perf_counter()

    # Keep only chars that are missing from the font
    for y in frame.index:
      frame.at[y, 'chars'] = CharList([
        c for c in frame.at[y, 'chars']
        if missingCache[c]
      ])

    # Optionally hide langs with incomplete/complete char sets
    self.updateProgress_(progressCallback, 'Filtering languages', 0, 2)
    self.completeLangs = frame[frame['chars'] == '']
    self.incompleteLangs = frame[frame['chars'] != '']
    self.updateProgress_(progressCallback, 'Filtering languages', 1, 2)
    if not showIncomplete:
      frame = self.completeLangs
    if not showComplete:
      frame = self.incompleteLangs
    self.updateProgress_(progressCallback, 'Filtering languages', 2, 2)

    self.updateProgress_(progressCallback, 'Sorting languages', 0, 1)
    frame = frame.sort_values('chars')
    self.updateProgress_(progressCallback, 'Sorting languages', 1, 1)

    self.updateProgress_(progressCallback, 'Preparing rows', 0, 1)
    rows = self.tableFromFrame(frame)
    self.updateProgress_(progressCallback, 'Preparing rows', 1, 1)
    return rows

  def charMissingFromFont_(self, char, font, charset, glyphNames, missingCache):
    if char in missingCache:
      return missingCache[char]

    if char in charset:
      missingCache[char] = False
      return False

    glyphInfo = Glyphs.glyphInfoForUnicode(ord(char), font)
    missing = glyphInfo is None or glyphInfo.name not in glyphNames
    missingCache[char] = missing
    return missing

  def updateProgress_(self, progressCallback, phase, completedUnits, totalUnits):
    if progressCallback:
      progressCallback(phase, completedUnits, totalUnits)


class DataSource:

  def __init__(self):
    self.scripts = {}
    self.langs = {}
    self.load()


class DataSourceHyperglot(DataSource):

  def load(self):
    import hyperglot
    import hyperglot.languages
    import hyperglot.language
    import hyperglot.orthography
    from hyperglot.loader import load_scripts_data

    self._scriptNames = load_scripts_data()

    hg = hyperglot.languages.Languages()
    for iso in hg.keys():
      lang = hyperglot.language.Language(iso)
      for i, orthoData in enumerate(lang.get('orthographies', [])):
        ortho = hyperglot.orthography.Orthography(orthoData)

        scriptId = self._scriptNameToIso(ortho.script)

        langId = f"{iso}_{i}_{scriptId}"

        # Hyperglot's Language class uses dict for raw data
        # and attributes for cleaned data.

        # We need raw data in some cases, i.e. to distinguish between 0 and
        # None for speakers, so the user can see whether speakers is explicitly
        # zero, or there's no data. Similarly, status defaults to 'living'
        # if undefined, but we will take a slightly different approach by
        # assuming 'living' only if speakers is > 0.

        if lang['speakers'] in (None, 'unknown'):
          speakers = -1
          scriptSpeakers = 0
        else:
          speakers = lang['speakers']
          scriptSpeakers = speakers

        self.langs[langId] = dict(
          id=langId,
          iso=iso,
          name=lang.get_name(),
          scriptId=self._scriptNameToIso(ortho.script),
          lang_status='' if lang['status'] is None and speakers <= 0 else lang.status,
          ortho_status='' if ortho['status'] is None else ortho.status,
          speakers=speakers if ortho['status'] == 'primary' else 0,
          chars=sorted(set(ortho.base_chars)) + sorted(set(ortho.base_marks)),
        )

        if scriptId not in self.scripts:
          self.scripts[scriptId] = dict(
            id=scriptId,
            name=ortho.script,
            speakers=scriptSpeakers if ortho['status'] == 'primary' else 0,
          )
        elif self.langs[langId]['ortho_status'] == 'primary':
          self.scripts[scriptId]['speakers'] += scriptSpeakers

  def _scriptNameToIso(self, name):
    if name not in self._scriptNames:
      return name
    return self._scriptNames[name]['iso_15924']


class CharList(str):

  '''
  A list of chars that acts like a string, but sorts by the list length.
  (This is used for the Missing column)
  '''

  def __new__(self, li):
    return str.__new__(self, ''.join(li))

  def __lt__(self, other):
    return len(self) < len(other)

  def __str__(self):
    return ' '.join(self)
