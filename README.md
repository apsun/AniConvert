# AniConvert

Yet another batch file converter for [HandBrake](https://handbrake.fr/)

## Features

- Convert an entire folder of videos with just one command
- Recursive video searching: perfect for TV shows with multiple seasons
- Automatically choose an audio and subtitle track based on your language preferences
- Smart "destination file already exists" handling - no more accidental overwriting
- No annoying dependencies - everything is in one portable script

## Requirements

- [HandBrake (command-line version)](https://handbrake.fr/downloads2.php)
- [Python](https://www.python.org/downloads/) 2.7 or above (Python 3 is supported)
- A folder full of videos to convert!

## Example usage

- Convert a folder of videos (default settings): `aniconvert.py path/to/folder`
- Also look in subdirectories: `aniconvert.py -r ...`
- Automatically select Japanese audio and English subtitles: `aniconvert.py -a jpn -s eng ...`
- Skip files that have already been converted: `aniconvert.py -w skip ...`
- Any combination of the above, and more!

## License

Distributed under the [MIT License](http://opensource.org/licenses/MIT).

## FAQ

### Why is this better than the official HandBrake GUI?

The official HandBrake app requires that you apply your audio and subtitle 
preferences to each video file individually, which is annoying if you have 
a folder of videos that you know are in the same format. This script aims to 
solve that problem, while also providing extra automation such as language 
priority for your audio and subtitle tracks.

### How do I pronounce the name?

"AnyConvert". The "Ani" is also short for "anime", which is what the script 
was designed for. Of course, it also works great with just about any TV series, 
from Game of Thrones to My Little Pony, as long as all your video files have the 
same track layout.

### Why are my subtitles burned into the video?

Again, this script was written with anime in mind, where subtitles tend to 
be highly stylized. HandBrake does not handle these subtitles well, and the 
only way to maintain their styling is to burn them into the video.

### I get this error: `AssertionError: Track count mismatch`

This commonly occurs if your copy of HandBrakeCLI is dynamically linked 
to FFmpeg instead of Libav, and your video contains ASS format subtitles. 
If possible, use a pre-built copy of HandBrakeCLI downloaded from the 
[official site](https://handbrake.fr/downloads2.php). For other operating 
systems, you will have to compile HandBrakeCLI yourself.