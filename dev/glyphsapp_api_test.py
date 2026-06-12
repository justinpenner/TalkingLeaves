import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path('~/Library/Application Support/Glyphs 3/Scripts/site-packages').expanduser()))
sys.path.insert(0, str(Path('~/Library/Application Support/Glyphs 3/Scripts').expanduser()))
sys.path.insert(0, '/Applications/Glyphs 3.app/Contents/Scripts311')
sys.path.insert(0, str(Path(__file__).resolve().parent))

for p in sys.path:
    print(p)

from GlyphsApp import glyphInfoForUnicode
