import sys
print(sys.argv)

print("Check if required modules are installed…")
import hyperglot, glyphsLib, vanilla, objc

print("Add TalkingLeaves to import paths…")
import sys
import pathlib
pluginRoot = pathlib.Path("../TalkingLeaves.glyphsPlugin/Contents/Resources")
sys.path.insert(0, str(pluginRoot))

from vanilla.test.testTools import executeVanillaTest
from TalkingLeaves import TalkingLeaves


def main():
  print("Wrap TalkingLeaves into a mini application with event loop…")
  executeVanillaTest(TalkingLeaves)
  print("Close application…")

if __name__ == '__main__':
  main()
