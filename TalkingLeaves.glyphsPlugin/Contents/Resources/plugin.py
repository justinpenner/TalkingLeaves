# -*- coding: utf-8 -*-

__doc__ = '''
GlyphsApp plugin wrapper for TalkingLeaves.
'''

import objc
from AppKit import NSMenuItem, NSCommandKeyMask, NSAlternateKeyMask
from GlyphsApp import Glyphs, DOCUMENTOPENED, DOCUMENTDIDCLOSE, WINDOW_MENU
from GlyphsApp.plugins import GeneralPlugin


class TalkingLeavesPlugin(GeneralPlugin):

  @objc.python_method
  def settings(self):

    # TalkingLeaves instance
    # Don't instantiate it now (wait until requested) or it would slow down GlyphsApp startup
    self.tl = None

    self.name = Glyphs.localize({
      'en': 'Talking Leaves',
    })

    keyboardShortcut = 't'
    # Set any combination of NSShiftKeyMask | NSControlKeyMask | NSCommandKeyMask | NSAlternateKeyMask
    keyboardShortcutModifier = NSCommandKeyMask | NSAlternateKeyMask

    self.menuItem = NSMenuItem(self.name)
    self.menuItem.setAction_(self.openWindow_)
    self.menuItem.setTarget_(self)
    self.menuItem.setKeyEquivalent_(keyboardShortcut)
    self.menuItem.setKeyEquivalentModifierMask_(keyboardShortcutModifier)

  @objc.python_method
  def start(self):
    Glyphs.menu[WINDOW_MENU].append(self.menuItem)

  def validateMenuItem_(self, menuItem):  # this will be called just before the menu is opened. So we don't need to keep track if the state
    return len(Glyphs.documents) > 0

  def openWindow_(self, sender):
    if self.tl and hasattr(self.tl, 'w'):
      self.tl.w.show()
    else:
      from TalkingLeaves import TalkingLeaves
      self.tl = TalkingLeaves()
      if hasattr(self.tl, 'w'):
        self.menuItem.setState_(True)
        self.tl.w.bind("close", self.windowWillClose_)

  def windowWillClose_(self, sender):
    self.menuItem.setState_(False)
    self.tl = None

  @objc.python_method
  def __file__(self):
    """Please leave this method unchanged"""
    return __file__
