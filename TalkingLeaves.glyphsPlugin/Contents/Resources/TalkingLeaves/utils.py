from AppKit import NSPasteboard, NSString, NSURL, NSURLSession, NSColorList
import json, csv, io, webbrowser, pathlib
import GlyphsApp

class SimpleVersion:

  '''
  Simple class for comparing version numbers in 1.1.1 format. This will 
  probably break if the libraries it's used on have a version number that 
  doesn't match the simple 3-number format. Currently only using it on 
  Hyperglot and not expecting them to change version format. Otherwise we'll
  need to add a new dependency to parse PEP 440 version numbers, as there's 
  nothing in Python stdlib that can do it, apparently.
  '''

  def __init__(self, version):
    parts = version.split('.')
    if len(parts) == 3 and all(p.isnumeric() for p in parts):
      self.parts = [int(p) for p in parts]

  def __lt__(self, other):
    for i, p in enumerate(self.parts):
      if p < other.parts[i]:
        return True
      if p > other.parts[i]:
        return False

def bundleResourcesDir(asString=False):
  if asString:
    return str(pathlib.Path(__file__).parent)
  return pathlib.Path(__file__).parent

def parseJson_(text):
  return json.loads(text)

def csvFromRows_(rows):
  text = io.StringIO('')
  writer = csv.writer(text, dialect='excel-tab')
  for row in rows:
    writer.writerow(row)
  return text.getvalue()

def writePasteboardText_(text):
  pasteboard = NSPasteboard.generalPasteboard()
  pasteboard.clearContents()
  pasteboard.writeObjects_([NSString(text)])

def getTextFromURL_successfulThen_(url, successCallback):
  url = NSURL.URLWithString_(url)

  def callback(data=None, response=None, error=None):
    if data and response and not error:
      successCallback(data.decode('utf-8'))

  dataTask = NSURLSession.sharedSession().dataTaskWithURL_completionHandler_(url, callback)
  dataTask.resume()

def getSystemColorByName_(name):
  # List of system colours can be found here:
  # NSColorList.colorListNamed_('System').allKeys()
  return NSColorList.colorListNamed_('System').colorWithKey_(name)

def flatten(lists):
  return [l for ll in lists for l in ll]
