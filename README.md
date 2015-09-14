# AniConvert

Yet another batch file converter for [HandBrake](https://handbrake.fr/)

## Features

- Convert an entire folder of videos with just one command
- Recursive video searching: perfect for TV shows with multiple seasons
- Automatically choose an audio and subtitle track based on your language preferences
- Smart "destination file already exists" handling - no more accidental overwriting
- No annoying dependencies, everything is in one portable script
- Works on Windows, Mac OS X, and Linux

## Requirements

- [HandBrake (command-line version)](https://handbrake.fr/downloads2.php)
- [Python](https://www.python.org/downloads/) 2.7 or above (Python 3 is supported)
- A folder full of videos to convert!

## Example usage

- Convert a folder of videos using default settings: `aniconvert.py path/to/folder`
- Also look in subdirectories: `aniconvert.py -r ...`
- Automatically select Japanese audio and English subtitles: `aniconvert.py -a jpn -s eng ...`
- Skip files that have already been converted: `aniconvert.py -w skip ...`
- Any combination of the above, and more! See the source code for full documentation.

## License

Distributed under the [MIT License](http://opensource.org/licenses/MIT).

## FAQ

### How do I pronounce the name?

"AnyConvert". The "Ani" is also short for "anime", which is what this script
was designed for. Of course, it also works great with just about any show
series, from Game of Thrones to My Little Pony.

### How does it work? Is FFmpeg/Libav required?

All of this script's information comes from parsing the output that
HandBrake produces. If HandBrake works, this script will too. No external
libraries are used by the script itself, but may be required by HandBrake.

### Why would I need this?

If you are watching your videos on a powerful computer, you probably don't.
However, if you are using an older device, or want to save some disk space,
then converting your videos using HandBrake is a good idea. Your videos will
be smaller (200-300MB for a typical episode of anime at 720p), and you will
be able to utilize H.264 hardware acceleration on devices that support it.

### How is this better than the official HandBrake GUI?

The official HandBrake app requires that you apply your audio and subtitle
preferences to each video file individually, which is annoying if you have
a folder of videos that you know are in the same format. This script aims to
solve that problem, while also providing extra automation such as language
priority for your audio and subtitle tracks.

### Why are my subtitles burned into the video?

Again, this script was written with anime in mind, where subtitles tend to
be highly stylized. HandBrake does not handle these subtitles well, and the
only way to maintain their styling is to burn them into the video. Read
[the HandBrake wiki](https://trac.handbrake.fr/wiki/Subtitles#wikipage)
for more details.

### Why do I get the error `AssertionError: Track count mismatch`?

This commonly occurs if your copy of HandBrakeCLI is linked against FFmpeg
instead of Libav, and your video contains ASS format subtitles. If possible,
use a pre-built copy of HandBrakeCLI downloaded from the
[official site](https://handbrake.fr/downloads2.php). For other operating
systems, you will have to compile HandBrakeCLI yourself.

For a more in-depth explanation, FFmpeg uses distinct constants to represent
SSA (`AV_CODEC_ID_SSA`) and ASS (`AV_CODEC_ID_ASS`), while Libav only uses
one constant for both, `AV_CODEC_ID_SSA`. HandBrake in turn only checks for
`AV_CODEC_ID_SSA`. Thus, if your file contains ASS format subtitles, FFmpeg
will return `AV_CODEC_ID_ASS`, which HandBrake will ignore, causing this error.
