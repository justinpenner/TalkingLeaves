# -*- coding: utf-8 -*-

__doc__='''
GlyphsApp plugin wrapper for TalkingLeaves.
'''

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from TalkingLeaves import *

class TalkingLeavesPlugin(GeneralPlugin):

  @objc.python_method
  def settings(self):

    # TalkingLeaves instance
    # Don't instantiate it now (wait until requested) or it would slow down GlyphsApp startup
    self.tl = None

    print("Loading TalkingLeaves plugin…")
    self.name = Glyphs.localize({
      'en': 'Talking Leaves',
      })

    self.keyboardShortcut = 't'
    # Set any combination of NSShiftKeyMask | NSControlKeyMask | NSCommandKeyMask | NSAlternateKeyMask
    self.keyboardShortcutModifier = NSCommandKeyMask | NSAlternateKeyMask

    self.menuItem = NSMenuItem(self.name, self.openWindow_)
    self.menuItem.setKeyEquivalent_(self.keyboardShortcut)
    self.menuItem.setKeyEquivalentModifierMask_(self.keyboardShortcutModifier)

  @objc.python_method
  def start(self):
    Glyphs.menu[WINDOW_MENU].append(self.menuItem)

    if len(Glyphs.documents) == 0:
      self.setMenuItemStatus_(False)

    Glyphs.addCallback(self.documentOpened_,DOCUMENTOPENED)
    Glyphs.addCallback(self.documentClosed_,DOCUMENTDIDCLOSE)

  def documentOpened_(self, sender):
    self.setMenuItemStatus_(True)

  def documentClosed_(self, sender):
    if len(Glyphs.documents) == 0 and self.tl is None:
      self.setMenuItemStatus_(False)

  def setMenuItemStatus_(self, status):
    # self.menuItem.setEnabled_(status)
    # TODO: find out why setEnabled_ doesn't work
    # In the meantime, we can just hide the menu item instead
    self.menuItem.setHidden_(not status)

  def openWindow_(self, sender):
    if self.tl and hasattr(self.tl,'w'):
      self.tl.w.show()
    else:
      self.tl = TalkingLeaves()
      if hasattr(self.tl,'w'):
        self.menuItem.setState_(True)
        self.tl.w.bind("close", self.windowWillClose_)

  def windowWillClose_(self, sender):
    self.menuItem.setState_(False)
    self.tl = None
    if len(Glyphs.documents) == 0:
      self.setMenuItemStatus_(False)

  @objc.python_method
  def __file__(self):
    """Please leave this method unchanged"""
    return __file__
