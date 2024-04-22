# 🍃 TalkingLeaves

TalkingLeaves is a [GlyphsApp](https://glyphsapp.com/) plugin to explore the world’s languages and writing systems. It also comes with useful features to show you what languages your font already supports, and which glyphs are needed to support more languages.

![Screenshot of the TalkingLeaves plugin window](screenshot.png)

## What else can it do?

TalkingLeaves can help you understand the range of writing systems and character sets used around the world at a high level, or it can help you find some interesting facts and outliers. Talking Leaves can answer questions like:

* How many languages can a font support with only the 26 basic Latin letters? *(Answer: 103)*
* Which writing system has the smallest population of native speakers? *(Answer: Cherokee)*
* What are some minority scripts that are used by a relatively large number of languages? *(Answer: Geʽez, also known as the Ethiopic script, is a great example of this)*

Those answers, of course, may change and grow as more languages are added to the [Hyperglot](https://github.com/rosettatype/hyperglot/) database, which powers TalkingLeaves.

## What does “Talking Leaves” mean?

“Talking leaves” is a beautiful metaphor for written language – attributed to the famous Cherokee neographer Sequoyah, who was one of the only people in history to invent the first writing system for their own people. The Cherokee syllabary was enormously successful, and within a few decades Cherokee literacy went from zero to nearly 100%, surpassing the literacy rate of the surrounding European settlers. Sequoyah’s work went on to inspire many more indigenous peoples to develop their own writing systems.

## Installation

### Install Python and pip

Install Python via [Python.org](https://www.python.org/), or use a package manager such as [Homebrew](https://brew.sh/) or [MacPorts](https://www.macports.org/). Run `pip3` or `pip` in your Terminal to ensure pip is working.

### Install dependencies

> [!IMPORTANT]
> Replace `3.11.6` with your Python version number from _Glyphs > Preferences > Addons_.

	pip3 install --python-version=3.11.6 --only-binary=:all: --target="/Users/$USER/Library/Application Support/Glyphs 3/Scripts/site-packages" --upgrade hyperglot pyobjc cocoa-vanilla

> [!NOTE]
> * `--python-version` tells pip to find packages for the Python version that you’re using in Glyphs.
> * `--only-binary` disallows source packages and is required when using `--python-version`.
> * `--target` installs the packages in a Glyphs-only location, and keeps them out of your `pip list`.

> [!WARNING]
> If you change to another Python in _Glyphs > Preferences > Addons_, you may need to delete the contents of `~/Library/Application Support/Glyphs 3/Scripts/site-packages` and then install the dependencies again with the new Python version number.

### Install TalkingLeaves plugin

Drag *TalkingLeaves.glyphsPlugin* and drop it onto the Glyphs icon in your dock. Glyphs will ask you to confirm the install, then you can restart Glyphs to begin using TalkingLeaves. Open a font, then open TalkingLeaves via the Window menu or ⌥⌘T.

## Roadmap

* [ ] Make installing dependencies easier for less-technical users.
* [ ] Add information about unencoded/alternate glyphs that may be required for some languages (complex scripts, local forms).
* [ ] Build TalkingLeaves plugins for other font editors, and possibly a web interface (contact me if you’re interested in helping/supporting this!)
* [ ] Add a "more data" toggle for the languages table that shows some additional data fields.
* [ ] Highlight glyphs in the "Missing" column that are composites and are composable from the user's existing glyph set.
* [ ] Add more language data sources, such as shaperglot/gflanguages.
* [ ] Consider other ways of visualizing and navigating through languages, instead of by script, such as by region or by language family.

## Contributing

If you have any ideas, bug reports, or other requests, I would love to hear them! You can file an [issue](https://github.com/justinpenner/TalkingLeaves/issues), or send me an email or a DM. You can find various ways to contact me at [justinpenner.ca](https://justinpenner.ca/).

The database of languages that powers TalkingLeaves comes from Hyperglot, an open-source project by Rosetta Type. If you want to contribute, see [https://github.com/rosettatype/hyperglot/](https://github.com/rosettatype/hyperglot/)

## Related resources

- [Hyperglot](https://hyperglot.rosettatype.com/) web interface to check fonts for language support, and explore Hyperglot’s database of languages and writing systems.
- [Hyperglot @ Github](https://github.com/rosettatype/hyperglot/)
- [Shaperglot](https://github.com/googlefonts/shaperglot/) another tool for checking language support similar to Hyperglot, but was originally initiated with the intent of checking OpenType features for languages that need more than just a minimum character set. Now Hyperglot and Shaperglot both have some ability to check OpenType features.
- [gflanguages](https://github.com/googlefonts/lang/) the language database behind Shaperglot.
