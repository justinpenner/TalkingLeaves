from Foundation import NSPasteboard, NSString, NSURL, NSURLSession, NSColorList
import json, csv, io, webbrowser
import GlyphsApp

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