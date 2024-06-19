import yaml
import pandas as pd
import utils


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
    frame = self.scripts.filter(['name','speakers']).sort_values('speakers', ascending=False)
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

  def langsAsTable(self, scriptName, font, showIncomplete, showComplete):
    scriptId = self.scripts[self.scripts['name'] == scriptName].reset_index().at[0, 'id']
    frame = self.langs[self.langs['scriptId'] == scriptId]
    frame = frame.filter(['name', 'speakers', 'ortho_status', 'lang_status', 'chars'])

    # Keep only chars that are missing from the font
    for y in frame.index:
      frame.at[y, 'chars'] = CharList([c for c in frame.at[y, 'chars'] if c not in font.glyphs])

    # Optionally hide langs with incomplete/complete char sets
    self.completeLangs = frame[frame['chars'] == '']
    self.incompleteLangs = frame[frame['chars'] != '']
    if showIncomplete == False:
      frame = self.completeLangs
    if showComplete == False:
      frame = self.incompleteLangs

    return self.tableFromFrame(frame)


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

    with open(utils.bundleResourcesDir() / "hyperglot-script-names.yaml") as f:
      self._scriptNames = yaml.load(f, Loader=yaml.Loader)

    hg = hyperglot.languages.Languages()
    for iso in hg.keys():
      lang = hyperglot.language.Language(iso)
      for orthoData in lang.get('orthographies', []):
        ortho = hyperglot.orthography.Orthography(orthoData)

        scriptId = self._scriptNameToIso(ortho.script)
        langId = f"{iso}_{scriptId}"
        self.langs[langId] = dict(
          id=langId,
          iso=iso,
          name=lang.get_name(),
          # script=ortho.script,
          scriptId=self._scriptNameToIso(ortho.script),
          lang_status=lang.get('status', ''),
          ortho_status=ortho.get('status', ''),
          speakers=hg[iso].get('speakers', -1),
          chars=sorted(set(ortho.base_chars)) + sorted(set(ortho.base_marks)),
        )

        if scriptId not in self.scripts:
          self.scripts[scriptId] = dict(
            id=scriptId,
            name=ortho.script,
            speakers=lang.get('speakers', 0),
          )
        elif self.langs[langId]['ortho_status'] == 'primary':
          self.scripts[scriptId]['speakers'] += lang.get('speakers', 0)

  def _scriptNameToIso(self, name):
    if name not in self._scriptNames:
      return name
    return self._scriptNames[name]['iso_15924']


class CharList(str):

  '''
  A list of chars that acts like a string, but sorts by the list length.
  (This is used for the Missing column)
  '''

  def __new__(self, l):
    return str.__new__(self, ''.join(l))
  
  def __lt__(self, other):
    return len(self) < len(other)

  def __str__(self):
    return ' '.join(self)
