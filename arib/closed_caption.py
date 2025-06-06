# -*- coding: utf-8 -*-
# vim: set ts=2 expandtab:
"""
Module: closed_caption.py
Desc: ARIB data group container
Author: John O'Neil
Email: oneil.john@gmail.com
DATE: Thursday, March 6th 2014

represents closed caption specific data within
an ARIB data group

"""

from . import read
from .decoder import Decoder
from . import code_set

DEBUG = False
DRCS_DEBUG = False


def set_DRCS_debug(v):
    global DRCS_DEBUG
    DRCS_DEBUG = v


class CaptionStatementData(object):
    """Represents a closed caption text wrapper
    Detailed in table 9-10 in ARIB STD b-24 PG 176
    """

    def __init__(self, f):
        """
        :param bytes: array of bytes payload
        """
        self._TMD = read.ucb(f) >> 6
        if self._TMD == 0x1 or self._TMD == 0x2:
            # 36 bit STM time, followed by 4 bit reserved data
            # followed by 24 bit data_unit_loop_length.
            # We'll read all that as a single 64 bit value and break it up
            d = read.ulb(f)
            self.STM = d >> 28
            self._data_unit_loop_length = d & 0xFFFFFFFF
            if DEBUG:
                print("CaptionStatementData: STM (time) " + str(self.STM))
                print(
                    "CaptionStatementData: data unit loop length: "
                    + str(self._data_unit_loop_length)
                )
        else:
            self.STM = 0
            self._data_unit_loop_length = read.ui3b(f)
        if DEBUG:
            print(
                "Caption statement: data unit loop length: "
                + str(self._data_unit_loop_length)
            )
        bytes_read = 0
        self._data_units = []
        while bytes_read < self._data_unit_loop_length:
            self._data_units.append(DataUnit(f))
            bytes_read += self._data_units[-1].size()

    def load_caption_statement_data(self, data):
        """Load class contents from caption statement data payload"""
        pass


def next_data_unit(caption_statement_data):
    current = 0
    while current < len(caption_statement_data._data_units):
        yield caption_statement_data._data_units[current]
        current += 1


class StatementBody(object):
    """Statement body (caption text) in Data Unit"""

    ID = 0x20

    def __init__(self, f, data_unit):
        self._unit_separator = data_unit._unit_separator
        self._data_unit_type = data_unit._data_unit_type
        if self._data_unit_type != 0x20:
            if DEBUG:
                print("this is not caption data")
            raise ValueError
        self._data_unit_size = data_unit._data_unit_size
        # self._payload = f.read(self._data_unit_size)
        self._payload = StatementBody.parse_contents(f, self._data_unit_size)
        # print str(self._payload)

    def payload(self):
        return self._payload

    @staticmethod
    def Type():
        return StatementBody.ID

    @staticmethod
    def parse_contents(f, bytes_to_read):
        """
        Do complex reading of caption data from binary file.
        Return a list of statements and characters
        """
        if DEBUG:
            print(
                "going to read {bytes} bytes in binary file caption statement.".format(
                    bytes=bytes_to_read
                )
            )
        statements = []
        bytes_read = 0
        # TODO: Check to see if decoder state is carred between packet processing
        # currently recreating the decoder (and therefore resetting its state)
        # on every packet paylod processing. This may be incorrect
        decoder = Decoder()
        line = ""
        while bytes_read < bytes_to_read:
            statement = decoder.decode(f)
            if statement:
                bytes_read += len(statement)
                statements.append(statement)
            # if isinstance(statement, code_set.Kanji) or isinstance(statement, code_set.Alphanumeric) \
            #  or isinstance(statement, code_set.Hiragana) or isinstance(statement, code_set.Katakana):
            #  if DEBUG:
            #    print statement #just dump to stdout for now
        #    line += str(statement)
        # if len(line)>0:
        #  print '{l}\n'.format(l=line)
        return statements


class DRCSFont(object):
    """A single character in DRCS
    Called a 'font' to agree with Table D-1 in ARIB b-24 spec page 141
    """

    # in order to provide SOME kind of info when we encounter a DRCS, i have
    # a small hash table mapping to known (encountered) values.
    # There seems to be at least two new DRCS characters in every .ts file I
    # examine, so this is very limited.
    character_hashes = {
        -3174437220813644284: "♬",
        3626218632846089044: "[ｽﾋﾟｰｶｰ]",  # u"\U0001F50A", # unicode 'speaker with 3 sound U+1f50A
        -7036522249175460012: "[ｽﾋﾟｰｶｰ]",  # u"\U0001F508", # unicode "SPEAKER U+1F508
        7569189553178784666: "[ﾊﾟｿｺﾝ]",  # u"\U0001F4BB", #unicode personal computer U+1F4BB
        -7054764751876937278: "[ﾃﾚﾋﾞ]",  # u"\U0001F4FA", # unicode TV U+1f4fa
        7675785349947576464: "[携帯]",  # u"\U0001F4F1", # unicode cellphone U+1F4F1
        -8588766517861681222: "｟",
        -137322149189423910: "｠",
        -8884896295922033014: "⟪",
        -5876459750587952470: "⟫",
        2149867084803144864: "[ﾃﾚﾋﾞ]",  # u"\U0001F4FA", # unicode TV U+1f4fa
        -6623079553638809300: "[ﾏｲｸ]",
        -3827305093498498888: "𝔹",  # custom Conan 'meitantei badge". yes. really.
        -775118510460996568: "｟",
        -4397084408988046416: "｠",
        -6328951014288157962: "[ﾊﾟｿｺﾝ]",
        1113567731799993878: "①",
        6707059547002745896: "[ﾗｼﾞｵ]",
        6692026985814559272: "[携帯]",
    }

    # first is  combiled font id + font number four bits each
    def __init__(self, f):
        b = read.ucb(f)
        self._font_id = (b & 0xF0) >> 8
        self._mode = b & 0x0F
        if self._mode == 0 or self._mode == 0x1:
            self._depth = read.ucb(f)
            self._width = read.ucb(f)
            self._height = read.ucb(f)
            self._pixels = []

            # assuming 4 pixels per byte. How is this tied to depth above? (typical depth = 2)
            for i in range(int((self._width * self._height) / 4)):
                self._pixels.append(read.ucb(f))

            tmp_str = str(self._pixels)
            self._hash = hash(tmp_str)

            if DRCS_DEBUG:
                print(("DRCS character font id: {id}".format(id=self._font_id)))
                print(("DRCS character hash: {h}".format(h=self._hash)))

            if self._hash in DRCSFont.character_hashes:
                self._character = DRCSFont.character_hashes[self._hash]
            else:
                self._character = "�"

        else:
            raise ValueError("DRCSFont mode not supported.")
        if DRCS_DEBUG:
            print(("DRCS character: font: {font}".format(font=self._font_id)))
            px = ""
            i = 0
            for h in range(self._height / 2):
                for w in range(self._width / 4):
                    # px += str(self._pixels[i]) + " "
                    p = self._pixels[h * self._width / 2 + w]
                    if p == 0:
                        px += " "
                    elif p == 0xFF:
                        px += "█"
                    elif p == 0x0F:
                        px += "▐"
                    elif p == 0xF0:
                        px += "▌"
                    else:
                        px += "╳"
                    i = i + 1
                px += "\n"
            print(px)


class DRCSCharacter(object):
    """DRCS character parsed by DRCS2ByteCharacter class"""

    def __init__(self, f):
        """
        :param f: file descriptor we're reading from
        """
        self._character_code = read.usb(f)
        self._number_of_font = read.ucb(f)
        self._fonts = []
        for i in range(self._number_of_font):
            self._fonts.append(DRCSFont(f))


class DRCS1ByteCharacter(object):
    """DRCS data structure
    Describes custom character data delivered at runtime in the TS stream
    """

    ID = 0x30

    def __init__(self, f, data_unit):
        self._unit_separator = data_unit._unit_separator
        self._data_unit_type = data_unit._data_unit_type
        if self._data_unit_type is not DRCS1ByteCharacter.ID:
            if DEBUG:
                print("this is not a DRCS character")
            raise ValueError
        self._data_unit_size = data_unit._data_unit_size
        self._characters = []
        self._number_of_code = read.ucb(f)
        for i in range(self._number_of_code):
            self._characters.append(DRCSCharacter(f))

    def payload(self):
        return self._payload

    @staticmethod
    def Type():
        return DRCS1ByteCharacter.ID


class DataUnit(object):
    """Data Unit structure as defined in ARIB B-24 Table 9-12 pg 157"""

    def __init__(self, f):
        self._unit_separator = read.ucb(f)
        if self._unit_separator != 0x1F:
            if DEBUG:
                print("Unit separator not found at start of data unit.")
            raise ValueError
        self._data_unit_type = read.ucb(f)
        if DEBUG:
            print("data unit type: " + str(self._data_unit_type))
        self._data_unit_size = read.ui3b(f)
        if DEBUG:
            print("DataUnit size found to be: " + str(self._data_unit_size))
        # self._payload = f.read(self._data_unit_size)
        self._payload = self.load_unit(f)

    def payload(self):
        return self._payload

    def size(self):
        """return size of inflated data unit in bytes"""
        return self._data_unit_size + 5

    def load_unit(self, f):
        if self._data_unit_type == StatementBody.ID:
            return StatementBody(f, self)
        elif self._data_unit_type == DRCS1ByteCharacter.ID:
            # DRCS character data unit
            return DRCS1ByteCharacter(f, self)
        else:
            read.buffer(f, self._data_unit_size)


class Language(object):
    def __init__(self, f):
        d = read.ucb(f)
        self._language_tag = d >> 5
        if DEBUG:
            print(("caption management language tag: " + str(self._language_tag)))
        self._DMF = d & 0x7
        if self._DMF == 0b1100 or self._DMF == 0b1101 or self._DMF == 0b1110:
            self._DC = read.ucb(f)
        else:
            self._DC = 0

        if DEBUG:
            print(("caption managment DC: " + str(self._DC)))

        self._language_code = ""
        self._language_code += str(chr(read.ucb(f)))
        self._language_code += str(chr(read.ucb(f)))
        self._language_code += str(chr(read.ucb(f)))
        if DEBUG:
            print(("caption managment language code: " + str(self._language_code)))

        formats = read.ucb(f)
        self._format = formats >> 4
        if DEBUG:
            print(("caption management format: " + str(self._format)))

        self._rollup_mode = formats & 0x3
        if DEBUG:
            print(("caption management rollup mode: " + str(self._rollup_mode)))


class CaptionManagementData(object):
    """
    Describes caption managment data as per Arib b24 std
    table 9-3 on p173
    """

    # Time control (TMD) values as pert table 9-4
    TIME_CONTROL_FREE = 0b0
    TIME_CONTROL_REALTIME = 0b1
    TIME_CONTROL_OFFSET = 0b10
    TIME_CONTROL_RESERVED = 0b11

    # Display mode (DMF) masks per table 9-5
    DISPLAY_MODE_DISPLAY_MASK = 0b0000
    DISPLAY_MODE_NOT_DISPLAYED_MASK = 0b0100
    DISPLAY_MODE_SELECTABLE_MASK = 0b1000
    DISPLAY_MODE_AUTOMATIC_SELECTABLE_MASK = 0b1100
    DISPLAY_MODE_AUTOMATIC_RECORDING_MASK = 0b0000
    DISPLAY_MODE_NOT_DISPLAYED_AUTO_MASK = 0b0001
    DISPLAY_MODE_SELECTABLE_RECORDING_MASK = 0b0010

    # rollup as per table 9-9 p176
    NO_ROLLUP = 0b00
    ROLLUP = 0b01

    @staticmethod
    def display_format(format):
        """Caption managment format code to string
        After Arib b24 std table9-7 p175
        """
        if format == 0x0:
            return "Horizontal writing in standard density:"
        if format == 0x1:
            return "Vertical writing in standard density:"
        if format == 0x2:
            return "Horizontal writing in high density:"
        if format == 0x3:
            return "Vertical writing in high density:"
        if format == 0x4:
            return "Horizontal writing of Western language:"
        if format == 0x6:
            return "Horizontal writing in 1920x1080:"
        if format == 0x7:
            return "Vertical writing in 1920x1080:"
        if format == 0x8:
            return "Horizontal writing in 960x540:"
        if format == 0x9:
            return "Vertical writing in 960x540:"
        if format == 0xA:
            return "Horizontal writing in 1280x720:"
        if format == 0xB:
            return "Vertical writing in 1280x720:"
        if format == 0xC:
            return "Horizontal writing in 720x480:"
        if format == 0xD:
            return "Vertical writing in 720x480:"
        else:
            return "invalid caption managment format value."

    def num_languages(self):
        return len(self._languages)

    def language_code(self, language):
        return self._languages[language]._language_code

    def __init__(self, f):
        """"""
        self.TMD = read.ucb(f) >> 6
        if self.TMD == 0b10:
            _t = read.uib(f)
            _ub = read.uic(f) >> 4
            self._OTM = _t | (_ub << 32)
            if DEBUG:
                print("Caption management OTM: " + str(self._OTM))

        self._num_languages = read.ucb(f)
        self._languages = []
        for lang in range(self._num_languages):
            self._languages.append(Language(f))

        self._data_unit_loop_length = read.ui3b(f)
        if DEBUG:
            print(
                "Caption managmentdata : data unit loop length: "
                + str(self._data_unit_loop_length)
            )
        bytes_read = 0
        self._data_units = []
        while bytes_read < self._data_unit_loop_length:
            self._data_units.append(DataUnit(f))
            bytes_read += self._data_units[-1].size()
