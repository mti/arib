# vim: set ts=2 expandtab:
# -*- coding: utf-8 -*-
"""
Module: ass.py
Desc: Advanced SubStation Alpha subtitle file formatter
Author: John O'Neil
Email: oneil.john@gmail.com
DATE: Thursday, March 6th 2014

This module provides a formatter class that can be used
to turn arib package subtitle objects into a .ass 
file.
  
"""

from . import code_set
from . import control_characters
import codecs
import re
from .arib_exceptions import FileOpenError


class Pos(object):
    """Screen position in pixels"""

    def __init__(self, x, y):
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y


class Dialog(object):
    """text and dialog"""

    def __init__(self, s, x=None, y=None):
        self._s = s
        self._x = x
        self._y = y

    def __iadd__(self, other):
        self._s += other
        return self

    def __len__(self):
        return len(self._s)


class Size(object):
    """Screen width, height of an area in pixels"""

    def __init__(self, w, h):
        self._w = w
        self._h = h

    @property
    def width(self):
        return self._w

    @property
    def height(self):
        return self._h


class TextSize(object):
    SMALL = 1
    MEDIUM = 2
    NORMAL = 3


class ClosedCaptionArea(object):
    def __init__(self):
        # these values represent horizontal mode ('7')
        # TODO: make these configurable via CSI
        self._UL = Pos(170, 30)
        self._Dimensions = Size(620, 480)
        self._CharacterDim = Size(36, 36)
        self._char_spacing = 4
        self._line_spacing = 24

    @property
    def UL(self):
        return self._UL

    @property
    def Dimensions(self):
        return self._Dimensions

    def RowCol2ScreenPos(self, row, col, size=TextSize.NORMAL):
        # Issue #27: Horizontal text alignment incorrect
        # Without documentation justification I'm now assuming that currently set font size
        # affects the final text position as follows:
        # Normal Text: calculate position normally
        # Medium Text: characters are half width, so position horizontally is doubled
        # Small Text: characters are half width AND height, so row and column are both doubled.

        # for .ass files we specify the UL corner of text but row values from ARIB are
        # the LL. So we adjust for this by adding one row before adjusting for text size.
        r = row + 1
        c = col
        w = self._CharacterDim.width + self._char_spacing
        h = self._CharacterDim.height + self._line_spacing
        if size == TextSize.SMALL:
            h = h / float(2)

        if size == TextSize.SMALL or size == TextSize.MEDIUM:
            w = w / float(2)

        return Pos(self.UL.x + c * w, self.UL.y + r * h)


class ASSFile(object):
    """Wrapper for a single open utf-8 encoded .ass subtitle file"""

    def __init__(self, filepath, width=960, height=540):
        try:
            self._f = codecs.open(filepath, "w", encoding="utf8")
            self.write_header(width, height, filepath)
            self.write_styles()
            self.write_event_header()
        except:
            raise FileOpenError("Could not open file " + filepath + " for writing.")

    def __del__(self):
        try:
            if self._f:
                self._f.close()
        except AttributeError:
            pass

    def write(self, line):
        """Write indicated string to file. usually a line of dialog."""
        self._f.write(line)

    def write_header(self, width, height, title):
        header = """[Script Info]
; *****************************************************************************
; File generated via arib-ts2ass
; https://github.com/johnoneil/arib
; *****************************************************************************
Title: Japanese Closed Caption Subtitlies
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
Video Aspect Ratio: 0
Video Zoom: 1
Video Position: 0
Last Style Storage: Default
Video File: {title}


""".format(
            width=width, height=height, title=title
        )
        self._f.write(header)

    def write_styles(self):
        styles = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: normal,MS UI Gothic,37,&H00FFFFFF,&H000000FF,&H00000000,&H88000000,0,0,0,0,100,100,0,0,1,2,2,1,10,10,10,0
Style: medium,MS UI Gothic,37,&H00FFFFFF,&H000000FF,&H00000000,&H88000000,0,0,0,0,50,100,0,0,1,2,2,1,10,10,10,0
Style: small,MS UI Gothic,18,&H00FFFFFF,&H000000FF,&H00000000,&H88000000,0,0,0,0,100,100,0,0,1,2,2,1,10,10,10,0


"""
        self._f.write(styles)

    def write_event_header(self):
        event_header = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        self._f.write(event_header)


def asstime(seconds):
    """format floating point seconds elapsed time to 0:02:14.53"""
    hrs = int(seconds / 3600)
    seconds -= 3600 * hrs
    mins = int(seconds / 60)
    seconds -= 60 * mins
    return "{h:d}:{m:02d}:{s:02.2f}".format(h=hrs, m=mins, s=seconds)


def kanji(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += str(k)
    # print unicode(k)


def alphanumeric(formatter, a, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += str(a)
    # print unicode(a)


def hiragana(formatter, h, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += str(h)
    # print unicode(h)


def katakana(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += str(k)
    # print unicode(k)


def medium(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += "{\\rmedium}" + formatter._current_color
    formatter._current_style = "medium"
    formatter._current_textsize = TextSize.MEDIUM


def normal(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += "{\\rnormal}" + formatter._current_color
    formatter._current_style = "normal"
    formatter._current_textsize = TextSize.NORMAL


def small(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += "{\\rsmall}" + formatter._current_color
    formatter._current_style = "small"
    formatter._current_textsize = TextSize.SMALL


def space(formatter, k, timestamp):
    formatter.open_file()
    formatter._current_lines[-1] += " "


def drcs(formatter, c, timestamp):
    formatter._current_lines[-1] += "�"


def black(formatter, k, timestamp):
    formatter.open_file()
    # {\c&H000000&} \c&H<bb><gg><rr>& {\c&Hffffff&}
    formatter._current_lines[-1] += "{\c&H000000&}"
    formatter._current_color = "{\c&H000000&}"


def red(formatter, k, timestamp):
    # {\c&H0000ff&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&H0000ff&}"
    formatter._current_color = "{\c&H0000ff&}"


def green(formatter, k, timestamp):
    # {\c&H00ff00&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&H00ff00&}"
    formatter._current_color = "{\c&H00ff00&}"


def yellow(formatter, k, timestamp):
    # {\c&H00ffff&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&H00ffff&}"
    formatter._current_color = "{\c&H00ffff&}"


def blue(formatter, k, timestamp):
    # {\c&Hff0000&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&Hff0000&}"
    formatter._current_color = "{\c&Hff0000&}"


def magenta(formatter, k, timestamp):
    # {\c&Hff00ff&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&Hff00ff&}"
    formatter._current_color = "{\c&Hff00ff&}"


def cyan(formatter, k, timestamp):
    # {\c&Hffff00&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&Hffff00&}"
    formatter._current_color = "{\c&Hffff00&}"


def white(formatter, k, timestamp):
    # {\c&Hffffff&}
    formatter.open_file()
    formatter._current_lines[-1] += "{\c&Hffffff&}"
    formatter._current_color = "{\c&Hffffff&}"


def position_set(formatter, p, timestamp):
    """Active Position set coordinates are given in character row, column
    So we have to calculate pixel coordinates (and then sale them)
    """
    pos = formatter._CCArea.RowCol2ScreenPos(p.row, p.col, formatter._current_textsize)
    line = "{{\\r{style}}}{color}{{\pos({x},{y})}}".format(
        color=formatter._current_color, style=formatter._current_style, x=pos.x, y=pos.y
    )
    formatter._current_lines.append(Dialog(line))


a_regex = r'<CS:"(?P<x>\d{1,4});(?P<y>\d{1,4}) a">'


def control_character(formatter, csi, timestamp):
    """This will be the most difficult to format, since the same class here
    can represent so many different commands.
    e.g:
    <CS:"7 S"><CS:"170;30 _"><CS:"620;480 V"><CS:"36;36 W"><CS:"4 X"><CS:"24 Y"><Small Text><CS:"170;389 a">
    """
    cmd = str(csi)
    a_match = re.search(a_regex, cmd)
    if a_match:
        # APS Control Sequences (absolute positioning of text as <CS: 170;389 a> above
        # indicate the LOWER LEFT HAND CORNER of text position.
        x = a_match.group("x")
        y = a_match.group("y")
        formatter._current_lines.append(
            Dialog(
                "{{\\r{style}}}{color}{{\\pos({x},{y})}}{{\\an1}}".format(
                    color=formatter._current_color,
                    style=formatter._current_style,
                    x=x,
                    y=y,
                )
            )
        )
        return


pos_regex = r"({\\pos\(\d{1,4},\d{1,4}\)})"


def clear_screen(formatter, cs, timestamp):
    if timestamp - formatter._elapsed_time_s > formatter._tmax:
        end_time = asstime(formatter._elapsed_time_s + formatter._tmax)
    else:
        end_time = asstime(timestamp)
    start_time = asstime(formatter._elapsed_time_s)

    if (
        len(formatter._current_lines[0]) or len(formatter._current_lines)
    ) and start_time != end_time:
        for l in reversed(formatter._current_lines):
            if not len(l):
                continue

            line = "Dialogue: 0,{start_time},{end_time},normal,,0000,0000,0000,,{line}\\N\n".format(
                start_time=start_time, end_time=end_time, line=l._s
            )
            # TODO: add option to dump to stdout
            # print line.encode('utf-8')
            if formatter._ass_file:
                formatter._ass_file.write(line)
            formatter._current_lines = [Dialog("")]

    formatter._elapsed_time_s = timestamp
    formatter._current_textsize = TextSize.NORMAL
    formatter._current_color = "{\c&Hffffff&}"


class ASSFormatter(object):
    """
    Format ARIB objects to dialog of the sort below:
    Dialogue: 0,0:02:24.54,0:02:30.55,small,,0000,0000,0000,,{\pos(500,900)}ゴッド\\N
    Dialogue: 0,0:02:24.54,0:02:30.55,small,,0000,0000,0000,,{\pos(780,900)}ほかく\\N
    Dialogue: 0,0:02:24.54,0:02:30.55,normal,,0000,0000,0000,,{\pos(420,1020)}ＧＯＤの捕獲を目指す・\\N
    """

    DISPLAYED_CC_STATEMENTS = {
        code_set.Kanji: kanji,
        code_set.Alphanumeric: alphanumeric,
        code_set.Hiragana: hiragana,
        code_set.Katakana: katakana,
        control_characters.APS: position_set,  # {\pos(<X>,<Y>)}
        control_characters.MSZ: medium,  # {\rmedium}
        control_characters.NSZ: normal,  # {\rnormal}
        control_characters.SP: space,  # ' '
        control_characters.SSZ: small,  # {\rsmall}
        control_characters.CS: clear_screen,
        control_characters.CSI: control_character,  # {\pos(<X>,<Y>)}
        # control_characters.COL,
        control_characters.BKF: black,  # {\c&H000000&} \c&H<bb><gg><rr>&
        control_characters.RDF: red,  # {\c&H0000ff&}
        control_characters.GRF: green,  # {\c&H00ff00&}
        control_characters.YLF: yellow,  # {\c&H00ffff&}
        control_characters.BLF: blue,  # {\c&Hff0000&}
        control_characters.MGF: magenta,  # {\c&Hff00ff&}
        control_characters.CNF: cyan,  # {\c&Hffff00&}
        control_characters.WHF: white,  # {\c&Hffffff&}
        # largely unhandled DRCS just replaces them with unicode unknown character square
        code_set.DRCS0: drcs,
        code_set.DRCS1: drcs,
        code_set.DRCS2: drcs,
        code_set.DRCS3: drcs,
        code_set.DRCS4: drcs,
        code_set.DRCS5: drcs,
        code_set.DRCS6: drcs,
        code_set.DRCS7: drcs,
        code_set.DRCS8: drcs,
        code_set.DRCS9: drcs,
        code_set.DRCS10: drcs,
        code_set.DRCS11: drcs,
        code_set.DRCS12: drcs,
        code_set.DRCS13: drcs,
        code_set.DRCS14: drcs,
        code_set.DRCS15: drcs,
    }

    def __init__(
        self,
        default_color="white",
        tmax=5,
        width=960,
        height=540,
        video_filename="output.ass",
        verbose=False,
    ):
        """
        :param width: width of target screen in pixels
        :param height: height of target screen in pixels
        :param format_callback: callback method of form <None>callback(string) that
        can be used to dump strings to file upon each subsequent "clear screen" command.
        """
        self._color = default_color
        self._tmax = tmax
        self._CCArea = ClosedCaptionArea()
        self._pos = Pos(0, 0)
        self._elapsed_time_s = 0.0
        self._ass_file = None
        self._current_lines = [Dialog("")]
        self._current_style = "normal"
        self._current_color = "{\c&Hffffff&}"
        self._current_textsize = TextSize.NORMAL
        self._filename = video_filename
        self._width = width
        self._height = height
        self._height = height
        self._verbose = verbose

    def open_file(self):
        if not self._ass_file:
            if self._verbose:
                print("Found nonempty ARIB closed caption data in file.")
                print(("Writing .ass file: " + self._filename))
            self._ass_file = ASSFile(self._filename)

    def file_written(self):
        return self._ass_file is not None

    def format(self, captions, timestamp):
        """Format ARIB closed caption info tinto text for an .ASS file"""
        # TODO: Show progress in some way
        # print('File elapsed time seconds: {s}'.format(s=timestamp))
        # line = u'{t}: {l}\n'.format(t=timestamp, l=u''.join([unicode(s) for s in captions if type(s) in ASSFormatter.DISPLAYED_CC_STATEMENTS]))

        for c in captions:
            if type(c) in ASSFormatter.DISPLAYED_CC_STATEMENTS:
                # invoke the handler for this object type
                ASSFormatter.DISPLAYED_CC_STATEMENTS[type(c)](self, c, timestamp)
            else:
                # TODO: Warning of unhandled characters
                pass
                # print str(type(c))
