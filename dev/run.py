import sys
if len(sys.argv) < 2:
  print("No Glyphs document specified. Loading default test document…")

print("Add GlyphsPython site-packages folder to import paths…")
import sys
import pathlib
glyphs_scripts_dir = pathlib.Path("~/Library/Application Support/Glyphs 3/Scripts").expanduser()
sys.path.insert(0, str(glyphs_scripts_dir))
glyphs_pkg_dir = pathlib.Path("~/Library/Application Support/Glyphs 3/Scripts/site-packages").expanduser()
sys.path.insert(0, str(glyphs_pkg_dir))

print("Check if required modules are installed…")
import hyperglot, glyphsLib, vanilla, objc

print("Add TalkingLeaves to import paths…")
plugin_root = pathlib.Path("../TalkingLeaves.glyphsPlugin/Contents/Resources")
sys.path.insert(0, str(plugin_root))

from vanilla.test.testTools import executeVanillaTest
from TalkingLeaves import TalkingLeaves


def main():
  print("Wrap TalkingLeaves into a mini application with event loop…")
  executeVanillaTest(TalkingLeaves)
  print("Close application…")

if __name__ == '__main__':
  main()
