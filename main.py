#!/usr/bin/env python
###############################################################
# AniConvert: Batch convert directories of videos using 
# HandBrake. Intended to be used on anime and TV series, 
# where files downloaded as a batch tend to have the same 
# file formats. Can also automatically select a single audio 
# and subtitle track based on language preference.
#
# Copyright (c) 2015 Andrew Sun (@crossbowffs)
# Distributed under the MIT license
###############################################################
from __future__ import print_function
import argparse
import errno
import os
import re
import subprocess
import textwrap

# Use raw_input() in Python 2
try:
    input = raw_input
except NameError:
    pass

try:
    indent_text = textwrap.indent
except AttributeError:
    def indent_text(text, prefix):
        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if line.strip() else line)
        return "".join(prefixed_lines())

###############################################################
# Configuration values, no corresponding command-line args
###############################################################

# Path to the HandBrake CLI binary.
HANDBRAKE_PATH = "/usr/bin/HandBrakeCLI"

# List of video formats to process. Other file formats in the 
# input directory will be ignored.
INPUT_VIDEO_FORMATS = ["mkv", "mp4"]

# The format to convert the videos to.
OUTPUT_VIDEO_FORMAT = "mp4"

# If no output directory is explicitly specified, the output 
# files will be placed in a directory with this value appended 
# to the name of the input directory.
DEFAULT_OUTPUT_SUFFIX = "-converted"

# Define the arguments to pass to HandBrake.
# Do not define any of the following:
#   -i <input>
#   -o <output>
#   -a <audio track>
#   -s <subtitle track>
#   -X <width>
#   -Y <height>
# Obviously, do not define anything that would cause HandBrake 
# to not convert the video file either.
HANDBRAKE_ARGS = """
-E ffaac
-B 160
-6 dpl2
-R Auto
-e x264
-q 20.0
--vfr
--audio-copy-mask aac,ac3,dtshd,dts,mp3
--audio-fallback ffaac
--loose-anamorphic
--modulus 2
--x264-preset medium
--h264-profile high
--h264-level 3.1
--subtitle-burned
"""

###############################################################
# Default values and explanations for command-line args
###############################################################

# A list of preferred audio languages, ordered from most 
# to least preferable. If no audio track is explicitly 
# specified and there is only one audio track in the 
# most preferable language, it will be automatically selected. 
# If more than one track is in the most preferable language, 
# you will be prompted to select one. If no tracks are 
# in the most preferable language, the program will check 
# the second most preferable language, and so on. This value 
# should use the iso639-2 (3 letter) language code format.
# On the command line, specify as "--audio-languages jpn,eng"
AUDIO_LANGUAGES = ["jpn", "eng"]

# This is the same as the preferred audio languages, but 
# for subtitles. On the command line, specify as 
# "--subtitle-languages eng"
SUBTITLE_LANGUAGES = ["eng"]

# What to do when the destination file already exists. Can be 
# one of:
#    "prompt": Ask the user what to do
#    "skip": Skip the file and proceed to the next one
#    "overwrite": Overwrite the destination file
# On the command line, specify as "-w skip"
DUPLICATE_ACTION = "skip"

# The width and height of the output video, in the format 
# "1280x720". A value of "auto" is also accepted, and will 
# preserve the input video dimensions. On the command line, 
# specify as "-d 1280x720" or "-d auto"
OUTPUT_DIMENSIONS = "auto"

# Set this to true to search sub-directories within the input 
# directory. Files will be output in the correspondingly named 
# folder in the destination directory.
RECURSIVE_SEARCH = False

# If this is false, only the first video in each directory 
# will be used to determine the audio and subtitle indices 
# for all files in the directory. This speeds up the 
# conversion process a bit, but will cause incorrect 
# output if the format differs across videos.
CHECK_ALL_FILES = False


class HandBrakeAudioInfo:
    pattern1 = re.compile(r"(\d+), (.+) \(iso639-2: (\S+)\)")
    pattern2 = re.compile(r"(\d+), (.+) \(iso639-2: (\S+)\), (\d+)Hz, (\d+)bps")

    def __init__(self, info_str):
        match = self.pattern1.match(info_str)
        if not match:
            raise ValueError("Unknown audio track info format: " + repr(info_str))

        self.index = int(match.group(1))
        self.description = match.group(2)
        self.language_code = match.group(3)

        match = self.pattern2.match(info_str)
        if match:
            self.sample_rate = int(match.group(4))
            self.bit_rate = int(match.group(5))
        else:
            self.sample_rate = None
            self.bit_rate = None

    def __str__(self):
        format_str = textwrap.dedent("""\
            Description: {description}
            Language code: {language_code}""")

        if self.sample_rate and self.bit_rate:
            format_str += textwrap.dedent("""
                Sample rate: {sample_rate}Hz
                Bit rate: {bit_rate}bps""")

        return format_str.format(**self.__dict__)

    def __repr__(self):
        format_str = "{index}, {description} (iso639-2: {language_code})"
        if self.sample_rate and self.bit_rate:
            format_str += ", {sample_rate}Hz, {bit_rate}bps"
        info_str = format_str.format(**self.__dict__)
        return "HandBrakeAudioInfo(" + repr(info_str) + ")"

    def __hash__(self):
        return hash((
            self.index,
            self.description,
            self.language_code,
            self.sample_rate,
            self.language_code
        ))

    def __eq__(self, other):
        if not isinstance(other, HandBrakeAudioInfo):
            return False
        return (
            self.index == other.index and 
            self.description == other.description and 
            self.language_code == other.language_code and 
            self.sample_rate == other.sample_rate and 
            self.language_code == other.language_code
        )


class HandBrakeSubtitleInfo:
    pattern = re.compile(r"(\d+), (.+) \(iso639-2: (\S+)\) \((\S+)\)\((\S+)\)")

    def __init__(self, info_str):
        match = self.pattern.match(info_str)
        if not match:
            raise ValueError("Unknown subtitle track info format: " + repr(info_str))

        self.index = int(match.group(1))
        self.language = match.group(2)
        self.language_code = match.group(3)
        self.format = match.group(4)
        self.source = match.group(5)

    def __str__(self):
        return textwrap.dedent("""\
            Language: {language}
            Language code: {language_code}
            Format: {format}
            Source: {source}""").format(**self.__dict__)

    def __repr__(self):
        format_str = "{index}, {language} (iso639-2: {language_code}) ({format})({source})"
        info_str = format_str.format(**self.__dict__)
        return "HandBrakeSubtitleInfo(" + repr(info_str) + ")"

    def __hash__(self):
        return hash((
            self.index,
            self.language,
            self.language_code,
            self.format,
            self.source
        ))

    def __eq__(self, other):
        if not isinstance(other, HandBrakeSubtitleInfo):
            return False
        return (
            self.index == other.index and 
            self.language == other.language and 
            self.language_code == other.language_code and 
            self.format == other.format and 
            self.source == other.source
        )


def get_videos_in_dir(path, recursive):
    video_extensions = {f.lower() for f in INPUT_VIDEO_FORMATS}
    for (dirpath, subdirnames, filenames) in os.walk(path):
        filtered_files = []
        for filename in filenames:
            extension = os.path.splitext(filename)[1][1:]
            if extension.lower() in video_extensions:
                filtered_files.append(filename)
        if len(filtered_files) > 0:
            yield (dirpath, sorted(filtered_files))
        if not recursive:
            del subdirnames[:]


def get_output_path(base_output_dir, base_input_dir, input_path):
    relpath = os.path.relpath(input_path, base_input_dir)
    temppath = os.path.join(base_output_dir, relpath)
    outpath = os.path.splitext(temppath)[0] + "." + OUTPUT_VIDEO_FORMAT
    return outpath


def try_create_directory(path, permissions=0o644):
    try:
        os.makedirs(path, permissions)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def try_delete_file(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def run_handbrake_scan(input_path):
    output = subprocess.check_output([
        HANDBRAKE_PATH, 
        "-i", input_path, 
        "--scan"
    ], stderr=subprocess.STDOUT)
    return output.decode("utf-8")


def parse_track_info(lines, start_index, cls):
    prefix = "    + "
    prefix_len = len(prefix)
    tracks = []
    i = start_index + 1
    while lines[i].startswith(prefix):
        info_str = lines[i][prefix_len:]
        info = cls(info_str)
        tracks.append(info)
        i += 1
    return (i, tracks)


def parse_handbrake_scan_output(output):
    lines = output.splitlines()
    audio_tracks = None
    subtitle_tracks = None
    i = 0
    while i < len(lines):
        if lines[i] == "  + audio tracks:":
            i, audio_tracks = parse_track_info(lines, i, HandBrakeAudioInfo)
        if lines[i] == "  + subtitle tracks:":
            i, subtitle_tracks = parse_track_info(lines, i, HandBrakeSubtitleInfo)
        i += 1
    return (audio_tracks, subtitle_tracks)


def get_track_info(input_path):
    scan_output = run_handbrake_scan(input_path)
    return parse_handbrake_scan_output(scan_output)


def filter_tracks_by_language(track_list, preferred_languages):
    for language in preferred_languages:
        language = language.lower()
        tracks = [t for t in track_list if t.language_code.lower() == language]
        if len(tracks) >= 1:
            return tracks
    return track_list


def print_audio_track_header(track_list):
    for track in track_list:
        print("Audio track #{0}:".format(track.index))
        print(indent_text(str(track), "    "))


def print_subtitle_track_header(track_list):
    for track in track_list:
        print("Subtitle track #{0}:".format(track.index))
        print(indent_text(str(track), "    "))


def prompt_select_track(track_list, header_printer):
    header_printer(track_list)
    while True:
        print("Choose a track #: ", end="")
        input_str = input()
        try:
            track_index = int(input_str)
        except ValueError:
            print("Enter a valid number!")
            continue
        try:
            return get_track_by_index(track_list, track_index)
        except IndexError:
            print("Enter a valid index!")
            continue


def prompt_overwrite_file(filename):
    print("The following file already exists: " + filename)
    while True:
        print("Do you want to overwrite it? (y/n): ", end="")
        input_str = input().lower()
        if input_str == "y":
            return True
        elif input_str == "n":
            return False
        else:
            print("Enter either 'y' or 'n'!")


def select_best_track(track_list, preferred_languages, header_printer):
    filtered_tracks = filter_tracks_by_language(track_list, preferred_languages)
    if len(filtered_tracks) == 1:
        return filtered_tracks[0]
    else:
        return prompt_select_track(filtered_tracks, header_printer)


def get_track_by_index(track_list, track_index):
    for track in track_list:
        if track.index == track_index:
            return track
    raise IndexError("Invalid track index: " + str(track_index))


def check_video_files(file_list):
    # TODO: Do something here
    pass


def run_handbrake(arg_list):
    subprocess.check_call([HANDBRAKE_PATH] + arg_list)
    # TODO: Error checking and whatnot


def get_handbrake_args(input_path, output_path, audio_index, subtitle_index, video_dimensions):
    args = HANDBRAKE_ARGS.replace("\n", " ").strip().split()
    args += ["-i", input_path]
    args += ["-o", output_path]
    args += ["-a", str(audio_index)]
    args += ["-s", str(subtitle_index)]
    if video_dimensions != "auto":
        args += ["-w", str(video_dimensions[0])]
        args += ["-l", str(video_dimensions[1])]
    return args


def parse_output_dimensions(value):
    if value == "auto":
        return value
    match = re.match("^(\d+)x(\d+)$", value)
    if not match:
        raise argparse.ArgumentTypeError(value + " is not a valid video dimension value")
    width = int(match.group(1))
    height = int(match.group(2))
    return (width, height)


def parse_duplicate_action(value):
    if value not in {"prompt", "skip", "overwrite"}:
        raise argparse.ArgumentTypeError(value + " is not a valid duplicate action")
    return value


def parse_language_arg(value):
    language_list = value.split(",")
    for language in language_list:
        if len(language) != 3 or not language.isalpha():
            raise argparse.ArgumentTypeError(language + " is not a valid iso639-2 code")
        # TODO: Maybe add some real validation here?
    return language_list


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("-o", "--output-dir")
    parser.add_argument("-w", "--duplicate-action", type=parse_duplicate_action, default=DUPLICATE_ACTION)
    parser.add_argument("-d", "--output-dimensions", type=parse_output_dimensions, default=OUTPUT_DIMENSIONS)
    parser.add_argument("-r", "--recursive-search", action="store_true", default=RECURSIVE_SEARCH)
    parser.add_argument("-c", "--check-all-files", action="store_true", default=CHECK_ALL_FILES)
    parser.add_argument("-A", "--audio-languages", type=parse_language_arg, default=AUDIO_LANGUAGES)
    parser.add_argument("-S", "--subtitle-languages", type=parse_language_arg, default=SUBTITLE_LANGUAGES)
    parser.add_argument("-a", "--audio-index", type=int)
    parser.add_argument("-s", "--subtitle-index", type=int)
    args = parser.parse_args()

    args.input_dir = os.path.abspath(args.input_dir)
    if not args.output_dir:
        args.output_dir = args.input_dir + DEFAULT_OUTPUT_SUFFIX

    for subdir, filenames in get_videos_in_dir(args.input_dir, args.recursive_search):
        if args.check_all_files:
            check_video_files()

        audio_tracks, subtitle_tracks = get_track_info(os.path.join(subdir, filenames[0]))

        if args.audio_index is not None:
            audio_track = get_track_by_index(audio_tracks, args.audio_index)
        else:
            audio_track = select_best_track(audio_tracks, 
                args.audio_languages, print_audio_track_header)

        if args.subtitle_index is not None:
            subtitle_track = get_track_by_index(subtitle_tracks, args.subtitle_index)
        else:
            subtitle_track = select_best_track(subtitle_tracks, 
                args.subtitle_languages, print_subtitle_track_header)

        for filename in filenames:
            file_path = os.path.join(subdir, filename)
            output_path = get_output_path(args.output_dir, args.input_dir, file_path)

            if os.path.exists(output_path):
                if args.duplicate_action == "skip":
                    continue
                elif args.duplicate_action == "prompt" and not prompt_overwrite_file(filename):
                    continue

            try_create_directory(os.path.dirname(output_path))

            handbrake_args = get_handbrake_args(
                file_path, output_path, 
                audio_track.index, subtitle_track.index, 
                args.output_dimensions)

            try:
                run_handbrake(handbrake_args)
            except:
                try_delete_file(output_path)
                raise


if __name__ == "__main__":
    main()
