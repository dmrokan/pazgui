import sys
import signal
import enum
import time
import re
import copy
import logging
import traceback
import xml.etree.ElementTree as ET
import copy

from blessed import Terminal
import schedule

from pazgui import keycodes as _kc
from pazgui.behavior import (PazBehavior, PazPanel, PazHBox, PazButton, PazAlwaysDraw)
from pazgui.accessories import Bunch, DeepDict, init_logger, logger, StyleDict, new_weakref


class FrameBuffer(object):
    """
    Holds character frame and styling information.
    """

    def __init__(self, term):
        """
        Initialize FrameBuffer.

        :arg term Terminal: :class:``Terminal`` object from ``blessed``.
        """

        self._term = term
        self.height = 0
        self.width = 0
        self._frame = [u' '] * self.height * self.width
        self._style = StyleDict()
        self._tmp_style = StyleDict()
        self.resize()
        self.clear()
        self._flush_stream()

    def _pos1(self, x, y):
        """
        Transform terminal coordinates to buffer index.

        :arg int x: Column position (x axis)
        :arg int y: Row position (y axis)

        :return: Returns index.
        """

        return self.width * y + x

    def _pos2(self, ind):
        """
        Transform buffer index to terminal coordinates.

        :arg int ind: Buffer index.

        :return: Tuple (x, y).
        """

        y = ind // self.width
        x = ind % self.width

        return (x, y)

    def _print_c(self, ind):
        """
        Wrapper function for the print directive.

        :arg int ind: Index in the character buffer.
        """

        c = self._frame[ind]
        self._write_to_stream(u'{}'.format(c))

    def _resized(self):
        """
        Checks if the terminal is resized.

        :return bool: ``True`` if terminal is resized.
        """

        resized = False
        if self.height != self._term.height:
            resized |= True

        if self.width != self._term.width:
            resized |= True

        return resized

    def _write_style(self, x, y):
        """
        Writes style to the point (``x``, ``y``) on the terminal.
        """

        style = self.get_style(x, y)
        if style != None:
            self._write_to_stream(getattr(self._term, 'normal'))
            self._write_to_stream(getattr(self._term, style))

    def _write_to_stream(self, s):
        """
        Print is wrapped in this function because the output stream
        can be something other than stdout.
        """

        self._term.stream.write(s)

    def _flush_stream(self):
        self._term.stream.flush()

    def clear(self):
        """
        Clears the terminal.
        """

        self._write_to_stream(u'{}'.format(self._term.home))

    def resize(self):
        """
        Is called when terminal is resized.
        """

        if self._resized():
            self.clear()
            self.height = self._term.height
            self.width = self._term.width
            self._frame = [u' '] * self.height * self.width

    def set_xy(self, x, y, c):
        """
        Sets the character at terminal position (``x``, ``y``) to ``c``.

        :arg int x: x position on the terminal.
        :arg int y: y position on the terminal.
        :arg chr c: Character to be printed.
        """

        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            logger().warning(
                'x < 0 or y < 0 or x >= self.width or y >= self.height')
            return

        if type(c) == int:
            c = chr(c)

        ind = self._pos1(x, y)
        self._frame[ind] = c

    def set_tmp_style(self, x, y, z, style):
        """
        Temporary styles are planned to use for
        instantaneous style chages. Currently it is only
        used for highlighting cursor.

        :arg int x: Column position.
        :arg int y: Row position.
        :arg str style: Style string
        """

        current_style = self.get_style(x, y, z)
        self._tmp_style[y][x][z] = current_style
        self.set_style(x, y, z, style)

    def rm_tmp_style(self, x, y, z):
        if [y, x, z] in self._tmp_style:
            self._style[y][x][z] = self._tmp_style[y][x][z]
            del self._tmp_style[y][x][z]

    def set_style(self, x, y, z, style):
        """
        Set style of the character at point (``x``, ``y``) and z-index ``z``.
        Style with the largest z-index is printed.

        :arg int x: x position on the terminal.
        :arg int y: y position on the terminal.
        :arg int z: z-index of the style.
        :arg str style: Stype to be printed.
        """

        self._style[y][x] = style

    def get_style(self, x, y, z=None):
        """
        Get style information at terminal position (``x``, ``y``) with z-index
        ``z``. If ``z`` is not given, the style with the larges z-index is
        returned.

        :arg int x: x position on the terminal.
        :arg int y: y position on the terminal.
        :arg int z: z-index of the style.

        :return str: Style string.
        """

        if [y, x] in self._style and type(self._style[y][x]) == str:
            return self._style[y][x]
        else:
            return None

    def update(self):
        """
        Print character buffer and style to the terminal after clearing
        everything.
        """

        self.clear()
        ind = 0
        for y in range(self.height):
            for x in range(self.width):
                ind = self._pos1(x, y)

                self._term.move(x, y)
                self._write_style(x, y)

                self._print_c(ind)

        self._flush_stream()


class PazEvent(object):
    """
    Event object created at the time an event occurs and
    propagated to gui elements.
    """

    def __init__(self, name, source=None, target='all', data=None):
        """
        Constructor

        :arg str name: Event name ('DRAW', 'KEY_XXX', etc.)
        :arg PazBox_or_str object: The source which event originates from
        :arg PazBox_or_str target: The target of the events, event propagation
                                   sinks when it arrives a unique target
	:arg dict data: Extra event data.
        """

        self.name = name
        self.is_char = (len(name) == 1)

        if type(source) == PazBox or type(source) == PazGui:
            self.source = new_weakref(source)
        else:
            self.source = source

        if type(target) == PazBox or type(target) == PazGui:
            self.target = new_weakref(target)
        else:
            self.target = target

        self.data = data

        self._whitespace_keys = {
            'KEY_ENTER': '\n', 'KEY_TAB': '\t',
        }

        self._accepted_text_keys = [
            'KEY_UP', 'KEY_DOWN', 'KEY_RIGHT', 'KEY_LEFT',
            'KEY_BACKSPACE', 'KEY_DELETE'
             ] + list(self._whitespace_keys.keys())

    def __eq__(self, ev):
        """
        Compare two events
        """

        if type(ev) != PazEvent:
            return False
        if self.name == ev.name \
            and self.source == ev.source \
            and self.target == ev.target:
            return True
        else:
            return False

    def get(self, dname):
        if dname in self.data:
            return self.data[dname]
        else:
            return None

    def to_char(self):
        if self.is_char:
            return self.name
        elif self.name in self._whitespace_keys:
            return self._whitespace_keys[self.name]
        else:
            return None

    def cmp(self, ev):
        """
        Compare the name (type) of the event.

        :arg str_or_PazEvent ev: The name to be compared to

        :return bool: ``True`` if same, otherwise ``False``
        """

        if type(ev) == str:
            if ev == self.name:
                return True
            else:
                return False
        elif type(ev) == PazEvent:
            if self.name == ev.name and self.source == ev.source \
                and ev.target == ev.target:
                return True
            else:
                return False
        else:
            return False

    def isprintable(self):
        """
        Check if the event is a printable character by pressing the keyboard.

        :return bool: ``True`` if it is printable.
        """

        if self.is_char and self.name.isprintable():
            return True
        elif self.name in self._accepted_text_keys:
            return True
        else:
            return False

    def is_source(self, source):
        """
        Check if the event source same as the ``source`` provided.

        :arg PazBox_or_str source: Source to be compared to

        :return bool: ``True`` if same, otherwise ``False``
        """

        if type(self.source) == str and type(source) == str:
            if source == self.source:
                return True
            else:
                return False
        elif isinstance(self.source, PazBox) and isinstance(source, PazBox):
            if source == self.source:
                return True
            else:
                return False
        else:
            return False

    def is_target(self, target):
        """
        Check if the event's target same as the ``target`` provided.

        :arg PazBox_or_str target: Target to be compared to

        :return bool: ``True`` if same, otherwise ``False``
        """

        if type(self.target) == str and 'all' == self.target:
            return True

        if type(self.target) == str and type(target) == str:
            if target == self.target:
                return True
            else:
                return False
        elif type(self.target) == str and isinstance(target, PazBox):
            if target.get_path() == self.target:
                return True
            else:
                return False
        elif isinstance(self.target, PazBox) and isinstance(target, PazBox):
            if target == self.target:
                return True
            else:
                return False
        else:
            return False


class PazBox(object):
    """
    Main GUI object.
    """

    class PazText(object):
        """
        Rich text object.
        """

        def __init__(self, ctx, text="", config={ }):
            """
            Constructor

            :arg PazBox ctx: The parent ``PazBox`` of the text object.
            :arg str text: Raw text with style info to be parsed.
            :arg dict config: Text properties.
            """

            #: Reference to the GUI element contains text.
            self._ctx = ctx
            #: Holds parsed text in which styling info is removed.
            self._text = ''
            #: Holds original text with style info.
            self._raw_text = ''
            self._style_map = dict()

            # Default configuration
            self._config = {
                'tab-length': 4,
                'cursor': None,
            }

            for cfg in config:
                self._config[cfg] = config[cfg]

            if 'style' not in self._config:
                if 'background-style' in self._ctx.style:
                    self._config['style'] = self._ctx.style['background-style']
                else:
                    self._config['style'] = 'normal'

            if 'style:active' not in self._config:
                if 'background-style:active' in self._ctx.style:
                    self._config['style:active'] = self._ctx.style['background-style:active']
                else:
                    self._config['style:active'] = 'normal'

            # Rows of text are created after parsing.
            self._rows = list()
            self._row_length = -1
            # Bidirection mapping of the characters in parsed text.
            # It is used to get index of character from terminal position
            # and vice versa.
            self._pos_bimap = dict()
            # Text cursor position.
            self._cursor_pos = -1

            self._ws_re = re.compile(r'\s+')

            if self._config['cursor']:
                # A space is added to print cursor at the
                # end of text.
                self.set(text + ' ')
            else:
                self.set(text)

        def _pos_bimapper(self, map_in, map_out=None):
            """
            Transform the text index to row column index and vice versa.

            :arg int_or_tuple map_in: Key which can be an index or
                                      (``x``, ``y``) coordinate.
            :arg int_or_tuple map_out: Value which is similar to ``map_in``.
            :return int_or_tuple: Returns ``None`` if ``map_out`` is not None.
                                  Returns the value in ``self._pos_bimap`` which
                                  corresponds to the key ``map_in``.
            """

            if map_out != None:
                if (type(map_in) == int and type(map_out) == tuple \
                    and len(map_out) == 2) \
                    or (type(map_out) == int and type(map_in) == tuple \
                    and len(map_in) == 2):
                    self._pos_bimap[map_in] = map_out
                    self._pos_bimap[map_out] = map_in
                else:
                    raise RuntimeError('Invalid argument is given'
                        ' to _pos_bimapper.')

                return None
            elif map_in in self._pos_bimap:
                return self._pos_bimap[map_in]
            else:
                return None

        def _update_rows(self):
            """
            Convert text string into rows which will be
            printed in the corresponding ``PazBox``.
            """

            self._rows.clear()
            rect = list(self._ctx.get_style('rect'))
            margin = self._ctx.get_margin()
            (w, h) = (
                rect[2] - margin[1] - margin[3],
                rect[3] - margin[0] - margin[2])

            self._row_length = w

            lines = self._text.split('\n')

            text_ind = 0
            for line in lines:
                self._pos_bimapper(text_ind, (0, len(self._rows)))
                row = ''

                words = line.split(' ')
                word_count = len(words)

                i = 0
                while i < word_count:
                    word = words[i] + (' ' if i < word_count - 1 else '')

                    lr = len(row)
                    lw = len(word)

                    remaining_cols = self._row_length - lr

                    if lw <= remaining_cols:
                        # If there is enough space in the row
                        row += word
                        text_ind += lw
                        i += 1
                    elif lr == 0:
                        # If there is not enough space in the row and
                        # row is empty.
                        row += word[:self._row_length]
                        text_ind += self._row_length
                        self._rows.append(row)
                        self._pos_bimapper(text_ind, (0, len(self._rows)))
                        row = ''
                        words[i] = word[self._row_length:-1]
                    else:
                        self._rows.append(row)
                        self._pos_bimapper(text_ind, (0, len(self._rows)))
                        row = ''

                text_ind += 1

                self._rows.append(row)

        def _invert_style(self, style):
            if type(style) == str and style == 'normal':
                return 'black_on_white'
            elif type(style) == list and len(style) == 0:
                return 'black_on_white'
            else:
                if type(style) == str:
                    style_list = style.split('_')
                else:
                    style_list = style

                style_list = list(reversed(style_list))

                try:
                    on_ind = style_list.index('on')
                    bg_color_ind = on_ind + 1
                    fg_color_ind = on_ind - 1

                    tmp_color = style_list[bg_color_ind]
                    style_list[bg_color_ind] = style_list[fg_color_ind]
                    style_list[fg_color_ind] = tmp_color
                except ValueError:
                    style_list[0] = 'on_' + style_list[0]
                except IndexError:
                    # TODO: Log this error.
                    pass

                return '_'.join(list(reversed(style_list)))

        def _set_cursor(self, pos=-1):
            if self._config['cursor'] == None:
                return self._raw_text

            if pos > -1:
                self._cursor_pos = pos

            if self._cursor_pos == -1:
                self._cursor_pos = len(self._raw_text) - 1

            return (self._raw_text[:self._cursor_pos]
                + '<t s="{}">'.format(self._config['cursor'])
                + self._raw_text[self._cursor_pos]
                + '</t>'
                + self._raw_text[self._cursor_pos+1:])

        def set(self, text=''):
            """
            Set ``self._raw_text`` and parse the style information
            if ``PazText`` object is a rich text object.

            :arg str text: Raw text string.
            """

            self._raw_text = text
            self._cursor_pos = min(self._cursor_pos, len(self._raw_text) - 1)

        def get(self, raw=True):
            """
            Returns ``_raw_text`` or parsed text.

            :arg bool raw: Returns ``_raw_text`` if it is ``True``.

            :return str: Text string.
            """

            if raw:
                # Replace placeholder by the corresponding character.
                # See `PazTextArea.pre_event
                return self._raw_text.replace('\x01', '<') \
                    .replace('\x02', '>').replace('\x03', '&')
            else:
                return self._text

        def rows(self, row_ind=None):
            if row_ind == None:
                return self._rows
            else:
                return self._rows[row_ind]

        def get_text_style(self, col, row, inverted=False):
            """
            Get style of the character at position (col, row).

            :arg col int: Column index.
            :arg row int: Row index.

            :return str: Style string.
            """

            style = 'normal'

            for i in range(row, -1, -1):
                # Check backwards until it finds a style
                text_ind = self._pos_bimapper((0, i))
                if text_ind == None:
                    continue

                if i == row:
                    col_start = col
                else:
                    # Else start from the end of previous row
                    col_start = len(self._rows[i]) - 1

                for j in range(col_start, -1, -1):
                    text_ind2 = text_ind + j

                    if text_ind2 in self._style_map:
                        if 'invert' in self._style_map[text_ind2]:
                            while 'invert' in self._style_map[text_ind2]:
                                self._style_map[text_ind2].remove('invert')

                            inverted = True

                        style = '_'.join(self._style_map[text_ind2])

            if not style:
                style = 'normal'

            if not inverted:
                return style
            else:
                return self._invert_style(style)

        def modify_by_cursor(self, mod, overwrite=False, move=None):
            self.modify(mod, self._cursor_pos, overwrite, move)

        def modify(self, mod, pos, overwrite=False, move=None):
            """
            Modify the text at given position by appending,
            mergin or overwriting.

            NOTE: Rich text modification is not supported yet.

            :arg str mod: String to be added.
            :arg int_or_tuple pos: Position of the place to be modified
                                   in terms of string index (int) or screen
                                   position (``x``, ``y``) <=> (col, row).
            :arg bool overwrite: If True overwrite starting from `pos` else
                                 append text to `pos`.
            """

            if type(mod) == str:
                if not overwrite:
                    self._raw_text = self._raw_text[:pos] + mod \
                        + self._raw_text[pos:]
                else:
                    l1 = len(mod)
                    self._raw_text = self._raw_text[:pos] + mod \
                        + self._raw_text[pos+len(mod):]

                if move == None:
                    self.move_cursor((1, 0))
                else:
                    self.move_cursor(move)
            elif type(mod) == int:
                self._raw_text = self._raw_text[:pos+mod] \
                    + self._raw_text[pos+mod+1:]

                self.move_cursor((mod, 0))
            else:
                pass

            if not self._raw_text.endswith(' '):
                self._raw_text += ' '

        def parse(self):
            """
            Parse formatted rich text and extract styling information.
            """

            if not self._raw_text:
                self._rows = []
                return

            def parse_recursion(el, text_len, style_stack):
                style = el.get('s')
                if style and len(style) > 0:
                    style_stack.append(style)
                else:
                    style_stack.append(style_stack[-1])

                self._style_map[text_len] = \
                    [ s for s in style_stack if s != 'normal' ]
                text = el.text if el.text else ''
                text_len += len(text)

                style_stack_size = len(style_stack)
                for child in el:
                    new_text = parse_recursion(child, text_len, style_stack)
                    text_len += len(new_text)
                    text += new_text
                    del style_stack[style_stack_size:]

                del style_stack[-1]
                self._style_map[text_len] = \
                    [ s for s in style_stack if s != 'normal' ]
                new_text = el.tail if el.tail else ''
                text += new_text

                return text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

            # Replace tabs and place holder (see `PazTextArea.pre_event`) characters
            tmp_raw_text = self._set_cursor(self._cursor_pos)     \
                .replace('\t', self._config['tab-length'] * ' ')  \
                .replace('\x01', '&lt;').replace('\x02', '&gt;')  \
                .replace('\x03', '&amp;')

            if self._ctx.get_style('active'):
                text_style = self._config['style:active']
            else:
                text_style = self._config['style']

            tree = ET.fromstring(
                '<t s="{}">'.format(text_style) + tmp_raw_text + '</t>'
            )
            self._text = parse_recursion(tree, 0, [  ])

            self._update_rows()

        def move_cursor(self, delta):
            """
            Move cursor by delta points.

            :arg tuple delta: Position change in (``x``, ``y``) coordinates
            :return tuple: New cursor position
            """

            if delta[1] == 0:
                self._cursor_pos = max(0, min(
                    len(self._raw_text) - 1,
                    self._cursor_pos + delta[0]
                ))


    INF = float('inf')
    name = ""
    style = { }
    text = ""
    def __init__(self, buff, par=None):
        """
        Constructor.

        :arg gui.FrameBuffer buff: Reference to frame buffer object.
        :arg gui.PazBox par: Reference to parent box
        """

        self._buffer = buff
        self.scheduler = schedule
        self._children_list = []
        self._parent = new_weakref(par) if par else None

        # Default ``PazBox`` style
        self._style = {
            'z-index': -self.INF,
            'visible': True,
            'border': False,
            'border-style': 'normal',
            'border-style:active': '',
            'rect': (0, 0, 1, 1),
             # margin: (top, right, bottom, left)
            'margin': (0, 0, 0, 0),
            'active': False,
            'scroll-pos': (0, 0),
            'scroll-x': True,
            'scroll-y': True,
            'background': u' ',
            'background-style': 'normal',
            'background:active': '',
            'background-style:active': '',
            'text': {
                'cursor': None,
                # If text style is not provided ``PazText`` uses
                # background style.
                # 'style': 'normal',
            },
            'tab-index': -1,
            'activate-key': None,
            'deactivate-key': 'KEY_ESCAPE',
            'scroll-up-key': 'KEY_PGUP',
            'scroll-down-key': 'KEY_PGDOWN',
            'navigate-forwards': 'KEY_DOWN',
            'navigate-backwards': 'KEY_UP',
            # **
            'original-rect': None,
            'original-margin': None,
        }

        self._clip = None
        self._origin = None
        # Everything must be drawn initially.
        self._draw_flags = { 'all': 1 }

        if self._parent:
            self._path = self._parent.get_path()
        else:
            self._path = ''
        self._path += '/' + self.name

        self._behavior = [ PazBehavior(self) ]
        self._create()

    def _create(self):
        """
        First section of this function iterates through `PazBehavior`
        based classes in the style dictionary and creates instances of
        them. Then, it appends those instances into `self._behavior`
        list. By this way, different type of behaivour can be possesed
        by a base `PazBox` object. This is the method to extend `PazBox`
        class to give it different attributes: textarea attribute,
        button attribute etc.

        TODO: Complete this comment.
        Second section...
        """

        # 1)
        #
        # Styles should be initialized first since
        # behaviors are defined in styles.

        for sty in self.style:
            self._style[sty] = self.style[sty]

        self._init_styles()

        behavior = self.get_style('behavior')

        if type(behavior) == dict:
            for bhv in behavior:
                # Create an instance of `PazBehavior` class.
                bhv_instance = bhv(self, attr=behavior[bhv])
                # Append to the behavior list.
                self._behavior.append(bhv_instance)

        # 2)
        #
        # This is the first behavior call in `PazBox` object.
        self._run_behavior('pre_create')
        # **
        # PazText object
        self._text = self._text = \
            self.PazText(self, self.text, self.get_style('text'))

        # It must be resized here after `_init_styles` is called.
        self.resize()
        #
        self._children()
        self.schedule()
        # **
        self._run_behavior('post_create')

    def _init_styles(self):
        s = self._style
        for sty in s:
            if sty == 'rect':
                # Before style info, 'rect', will be modified, it is saved
                # to 'original-rect'.
                self.set_style('original-rect', s[sty])
            elif  sty == 'margin':
                self.set_style('original-margin', s[sty])
            elif  sty == 'active':
                if s[sty]:
                    self.activate()
            elif  sty == 'z-index':
                zindex = s[sty]
                if zindex == -self.INF:
                    if self._parent != None:
                        pzindex = self._parent.get_style(sty)
                        # 'z-index' is parents 'z-index' plus 1, if it is
                        # not defined in the style.
                        self.set_style(sty, pzindex + 1)
            elif  sty == 'tab-index':
                root = self.follow_path('/root')
                root.set_tab_index(self, s[sty])
            elif  sty == 'background-style' or sty == 'border-style':
                # Background and border color
                active_sty = sty + ':active'
                try:
                    style = s[active_sty]
                except KeyError:
                    style = ''

                if not style:
                    self.set_style(active_sty, self.get_style(sty))
            elif  sty == 'background':
                # Background character
                active_sty = sty + ':active'

                try:
                    style = s[active_sty]
                except KeyError:
                    style = ''

                if not style:
                    self.set_style(active_sty, self.get_style(sty))

    def _resize(self, box=None):
        """
        Recursive resize is used when terminal window is resized.

        :arg PazBox box: The `PazBox` that will be resized.
        """

        if box == None:
            box = self

        # Resize `box`.
        box.resize()

        for child in box.child('all'):
            self._resize(child)

    def _run_behavior(self, fcn_name, params=None):
        ret = False
        for bhv in self._behavior:
            if hasattr(bhv, fcn_name):
                 ret |= getattr(bhv, fcn_name)(params) or False

        return ret

    def _children(self):
        child_classes = self.children()

        if child_classes == None:
            return

        children = []
        for cls in child_classes:
            instance = cls(self._buffer, par=self)
            self.add_child(instance)

        return children

    def _draw_xy(self, x, y, val):
        self._buffer.set_xy(x, y, val)

    def _visible_area(self):
        """
        Calculates the visible area of a ``PazBox`` in screen coordinates.

        :return tuple: A rectangle (``x1``, ``y1``, ``x2``, ``y2``) defined by
                       upper left (``x1``, ``y1``) and lower right
                       (``x2``, ``y2``) corners.
        """

        clip = self.position_helper('clip')

        # Calculate visible area bounds.
        area = list(clip.area)
        # Get the character will be printed as background.
        margin = self.get_margin(add_border=False)

        area[0] += max(0, margin[3] - clip.clipped[0])
        area[1] += max(0, margin[0] - clip.clipped[1])

        area[2] -= max(0, margin[1] - clip.clipped[2])
        area[3] -= max(0, margin[2] - clip.clipped[3])

        if self.get_style('border'):
            if clip.clipped[0] == 0:
                area[0] += 1
            if clip.clipped[1] == 0:
                area[1] += 1
            if clip.clipped[2] == 0:
                area[2] -= 1
            if clip.clipped[3] == 0:
                area[3] -= 1

        return tuple(area)

    def _drawable_area(self):
        """
        Calculates the drawable area of a ``PazBox`` in screen coordinates.
        The difference between drawable and visible are is that drawable area
        also includes the invisible parts on the screen.

        :return tuple: A rectangle (``x1``, ``y1``, ``x2``, ``y2``) defined by
                       upper left (``x1``, ``y1``) and lower right
                       (``x2``, ``y2``) corners.
        """

        clip = self.position_helper('clip')

        # Calculate visible area bounds.
        area = list(clip.area)
        # Get the character will be printed as background.
        margin = self.get_margin(add_border=True)
        sx, sy = self.get_style('scroll-pos')

        area[0] += margin[3] - clip.clipped[0] - sx
        area[1] += margin[0] - clip.clipped[1] - sy

        area[2] -= margin[1] - clip.clipped[2]
        area[3] -= margin[2] - clip.clipped[3]

        return tuple(area)

    def _draw_text(self):
        """
        Draw text inside the box.
        """

        crect = self.get_style('content-rect')
        if crect[2] < 1:
            return

        self._text.parse()

        drawable_area = self._drawable_area()
        visible_area = self._visible_area()

        rows = self._text.rows()
        _y = 0
        for row in rows:
            # TODO: Remove this assertion.
            if len(row) > crect[2]:
                assert False

            _x = 0
            for c in row:
                x = drawable_area[0] + _x
                y = drawable_area[1] + _y

                if x >= visible_area[0] and x < visible_area[2] \
                    and y >= visible_area[1] and y < visible_area[3]:
                    self.draw_xy(x, y, c, 'text')
                    self._draw_text_style(_x, _y, x, y)

                _x += 1
            _y += 1

    def _draw_text_style(self, col, row, x, y):
        style = self._text.get_text_style(col, row)
        if style != None:
            self.draw_style(x, y, style)

    def _draw_border(self):
        """
        Draws border around the box if it is defined in the box style.
        """

        # Return if there is no border style.
        if self.get_style('border') == False:
            return

        # Get the rectangle in which the `PazBox` lays in local coordinates.
        rect = self.get_style('rect')
        # Get how many characters the rectangle clipped from all sides.
        clip = self.position_helper('clip')

        xb = (0, rect[2] - 1)
        yb = (0, rect[3] - 1)
        for x in range(rect[2]):
            # Do not print the clipped parts
            if x < clip.clipped[0] or x >= rect[2] - clip.clipped[2]:
                continue

            for y in range(rect[3]):
                # Do not print the clipped parts
                if y < clip.clipped[1] or y >= rect[3] - clip.clipped[3]:
                    continue

                # Transform it into global coordinates
                _x = clip.area[0] + x - clip.clipped[0]
                _y = clip.area[1] + y - clip.clipped[1]

                drawn = True
                # Upper left corner
                if x == xb[0] and y == yb[0]:
                    self.draw_xy(_x, _y, _kc.ULCORNER, 'border')
                # Lower left corner
                elif x == xb[0] and y == yb[1]:
                    self.draw_xy(_x, _y, _kc.LLCORNER, 'border')
                # Upper right corner
                elif x == xb[1] and y == yb[0]:
                    self.draw_xy(_x, _y, _kc.URCORNER, 'border')
                # Lower right corner
                elif x == xb[1] and y == yb[1]:
                    self.draw_xy(_x, _y, _kc.LRCORNER, 'border')
                # Left and right sides
                elif (x == xb[0] or x == xb[1]) and y != yb[0] and y != yb[1]:
                    self.draw_xy(_x, _y, _kc.VLINE, 'border')
                # Top and bottom sides
                elif (y == yb[0] or y == yb[1]) and x != xb[0] and x != xb[1]:
                    self.draw_xy(_x, _y, _kc.HLINE, 'border')
                else:
                    drawn = False

                if drawn == True:
                    self.draw_style(_x, _y, self.get_style('border-style'))

    def _draw_background(self):
        """
        Draws background of the `PazBox` object. Background is defined
        as a character and style information.
        """

        clip = self.position_helper('clip')
        # Get visible area of the box.
        # Area is a rectangle given by (x1, y1, x2, y2)
        area = list(clip.area)
        # Get the character will be printed as background.
        c = self.get_style('background')

        # If the box has border, then the background area is
        # shrinked for 1 character from all sides.
        if self.get_style('border') == True:
            if clip.clipped[0] == 0:
                area[0] += 1
            if clip.clipped[1] == 0:
                area[1] += 1
            if clip.clipped[2] == 0:
                area[2] -= 1
            if clip.clipped[3] == 0:
                area[3] -= 1

        # Get background style.
        bg_style = self.get_style('background-style')

        # Iterate through box area and print bg character and style.
        for y in range(area[1], area[3]):
            for x in range(area[0], area[2]):
                self.draw_xy(x, y, c, 'background')
                self.draw_style(x, y, bg_style)

    def _setup_draw(self):
        for bhv in self._behavior:
            bhv.setup_draw()

        self._recalculate_position_helpers()

    def _cleanup_draw(self):
        for flag in self._draw_flags:
            self._draw_flags[flag] = 0

        for bhv in self._behavior:
            bhv.cleanup_draw()

    def _event(self, ev):
        if not ev.is_target(self):
            return False

        ret = self._run_behavior('pre_event', { 'ev': ev }) or False
        # **
        ret |= self.event(ev) or False
        # **
        ret |= self._run_behavior('post_event', { 'ev': ev }) or False

        return ret

    def _recalculate_position_helpers(self):
        self._origin = self.to_global(0, 0) or self._clip
        self._clip = self.clip() or self._clip

    @staticmethod
    def _scheduled(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            # First item in `args` list is a reference to
            # the ``PazBox`` instance where the event is scheduled.
            _self = args[0]
            # Create an event and propagate.
            ev = PazEvent('SCHEDULED', _self, target='/root')
            _self.event_queue(ev)

        return wrapper

    def child(self, index):
        if type(index) == str and index == 'all':
            return self._children_list
        elif index < 0 or index >= self.children_count():
            return None

        return self._children_list[index]

    def parent(self):
        return self._parent

    def get_path(self):
        return self._path

    def follow_path(self, path):
        root = self
        while root._parent != None:
            root = root._parent

        names = [ n for n in path.split('/') if n ]
        if len(names) == 1:
            if names[0] == 'root':
                # The case when path='/root'
                return root
            else:
                return None

        for name in names[1:]:
            if len(name) == 0:
                continue

            children = root.child('all')
            found = False
            for child in children:
                if name == child.name:
                    root = child
                    found = True
                    break

            if found == False:
                # A ``PazBox`` with given path does not exist.
                return None

        return root

    def children_count(self):
        return len(self._children_list)

    def sibling_count(self):
        return len(self._parent.child('all'))

    def get_behavior(self, cls):
        for bhv in self._behavior:
            if isinstance(bhv, cls):
                return bhv

        return None

    def resize(self):
        """
        Adjust size of the box according to *rect* in *style* data.

        Calculates content rectangle with respect to its parent object.
        """

        self._run_behavior('pre_resize')
        # **
        orect = self.get_style('original-rect')

        if self._parent != None:
            parent_content_rect = self._parent.get_style('content-rect')
        else:
            parent_content_rect = (0, 0, 0, 0)

        rect_tmp = [ 0 ] * 4
        for i in range(len(orect)):
            v = orect[i]
            parent_content_rect_i = parent_content_rect[(i % 2) + 2]
            if type(v) == float:
                # Calculate size in characters when size is given as ratio.
                v = max(0.0, v)
                u = round(parent_content_rect_i * v)
            else:
                u = v

            rect_tmp[i] = u

        align_x = self.get_style('align-x')
        align_y = self.get_style('align-y')

        if align_x == 'right':
            rect_tmp[0] = parent_content_rect[2] - rect_tmp[0] - rect_tmp[2]

        if align_y == 'bottom':
            rect_tmp[1] = parent_content_rect[3] - rect_tmp[1] - rect_tmp[3]

        rect = tuple(rect_tmp)
        self.set_style('rect', rect)

        margin = self.get_margin()

        content_rect = (
            rect[0] + margin[3], rect[1] + margin[0],
            rect[2] - margin[1] - margin[3],
            rect[3] - margin[2] - margin[0]
        )
        self._style['content-rect'] = content_rect

        # Recalculate clip area and global position
        # after resize to save computation time.
        self._recalculate_position_helpers()

        # Everything must be redrawn.
        self.draw_flag('all', 1)
        # **
        self._run_behavior('post_resize')

    def to_global(self, x, y):
        """
        Translate local position in a box to global terminal
        coordinates.

        :arg int x: Position in horizontal direction
        :arg int y: Position in vertical direction
        :arg bool margin: Default value is False. If True, adds box margin.

        :return tuple: Global (`x`,`y`) coordinates.
        """

        rect = self.get_style('rect')
        if self._parent != None:
            pscroll = self._parent.get_style('scroll-pos')
            pmargin = self._parent.get_margin()
        else:
            pscroll = (0, 0)
            pmargin = (0, 0, 0, 0)

        x += rect[0] - pscroll[0] + pmargin[3]
        y += rect[1] - pscroll[1] + pmargin[0]


        if self._parent != None:
            (gx, gy) = self._parent.to_global(x, y)
        else:
            (gx, gy) = (x, y)

        return (gx, gy)

    def add_child(self, children):
        if not children.name:
            children.name = 'child:{}'.format(self.children_count())

        self._children_list.append(children)

    def remove_child(self, child):
        if type(child) == int:
            child = self._children_list[child]

        try:
            for gran in child.child('all'):
                child.remove_child(gran)

            root = self.follow_path('/root')
            root.remove_tab_index(child)

            self._children_list.remove(child)
        except ValueError:
            # TODO: Add handler.
            pass

        self.draw_flag('all', 1, propagate=True)

    _dynamic_styles = [ 'background', 'background-style', 'border-style' ]
    def get_style(self, name):
        """
        Styles are kept in a dictionary with a tree form. A sub-style
        can be reached by providing a name given as
        '<style name>.<sub-style name>.<...'.

        For example, one can check text style by ``name='text.style'``.

        :arg str name: Name of the style
        :return str: Style string
        """

        style_path = name.split('.')

        if not style_path:
            return None

        style = self._style

        i = 0
        while i < len(style_path) - 1:
            style = style[style_path[i]]

            i += 1

        name = style_path[-1]
        if self._style['active'] and name in self._dynamic_styles:
            # Return active version if the ``PazBox`` is active.
            name += ':active'

        if name in style:
            return style[name]
        else:
            return None

    def set_style(self, name, value):
        style_path = name.split('.')

        if not style_path:
            return

        style = self._style

        i = 0
        while i < len(style_path) - 1:
            style = style[style_path[i]]

            i += 1

        name = style_path[-1]

        style[name] = value

    def get_margin(self, add_border=True):
        total_margin = self.get_style('margin')

        if add_border == True:
            border = self.get_style('border')
            if border == True:
                total_margin = tuple([val + 1 for val in total_margin])

        return total_margin

    def modify_text(self, mod, pos=None, overwrite=False, move=None):
        """
        Modify the text at given position by appending,
        mergin or overwriting.

        Actual implementation is in :meth:``self.PazText.modify``.
        """

        if pos == None:
            self._text.modify_by_cursor(mod, overwrite, move)
        else:
            self._text.modify(mod, pos, overwrite, move)

        self.draw_flag('background', 1)
        self.draw_flag('text', 1)

    def set_text(self, text):
        self._text.set(text)

        self.draw_flag('background', 1)
        self.draw_flag('text', 1)

    def get_text(self, raw=True):
        return self._text.get(raw)

    def clear_text(self):
        # Always keep a space to print cursor.
        self.set_text(' ')

        self.draw_flag('background', 1)
        self.draw_flag('text', 1)

    def move_text_cursor(self, delta):
        self._text.move_cursor(delta)

        self.draw_flag('text', 1)
        self.draw_flag('background', 1)

    def buffer(self):
        return self._buffer

    def scroll(self, count):
        scroll_pos = list(self.get_style('scroll-pos'))

        if self.get_style('scroll-x'):
            scroll_pos[0] += count[0]
        if self.get_style('scroll-y'):
            scroll_pos[1] += count[1]

        self.set_style('scroll-pos',
            tuple(scroll_pos)
        )

        self.draw_flag('all', 1, propagate=True)

    def draw_style(self, x, y, style):
        """
        Add drawing style to for the character at (`x`, `y`)
        into the frame buffer.

        :arg int x: `x` position
        :arg int y: `y` position
        :arg str style: Style information
        """

        z = self.get_style('z-index')
        self._buffer.set_style(x, y, z, style)

    def draw_xy(self, x, y, val, w='', params=None):
        """
        Draw character in `val` to the point (`x`, `y`) on the terminal.

        :arg int x: `x` position
        :arg int y: `y` position
        :arg chr val: Character to be printed
        :arg str w: Indicates from which drawing function it is called
        :arg dict params: Extra parameters for the behavior function
        """

        self._run_behavior(
            'pre_draw_' + w, Bunch(x=x, y=y, val=val, extra=params)
        )
        # **
        self._draw_xy(x, y, val)
        # **
        self._run_behavior(
            'post_draw_' + w, Bunch(x=x, y=y, val=val, extra=params)
        )

    def position_helper(self, pos_type='origin'):
        """
        In order to make screen refreshing faster, important global
        positions on the terminal is saved to these variables. They
        will only change when screen is resized, after scrolling or
        adding/removing boxes etc.

        :arg str pos_type: The name of the important position.
        :return tuple: A tuple (`x`, `y`) representing the coordinates
                       on the terminal screen.
        """

        pos = None
        if pos_type == 'origin':
            return self._origin
        elif pos_type == 'clip':
            return self._clip
        else:
            return None

    def draw_flag(self, f, v=None, propagate=False):
        """
        Set draw flags to trigger draw action for gui parts
        in the next turn.

        :arg str f: Flag name which can be
            'background', 'border', 'text', 'all'.
        :arg int v: Setting it to `1` triggers draw action in the next turn.
        """

        if v == None:
            if self._draw_flags['all'] > 0:
                return self._draw_flags['all']
            elif f in self._draw_flags:
                return self._draw_flags[f]
            else:
                return 0
        elif type(v) == int:
            self._draw_flags[f] = v

            if v > 0:
                ev = PazEvent('DRAW', source=self, target='/root')
                self.event_queue(ev)

            if propagate and (f == 'all' or f == 'background'):
                for child in self.child('all'):
                    child.draw_flag('all', 1, propagate)

            return 0
        else:
            return 0

    def event_queue(self, ev):
        # Get the root GUI element which is an instance of ``PazGui``.
        root = self.follow_path('/root')
        root.event_queue(ev)

    def exit(self):
        """
        Recursively find the root ``PazGui`` instance
        and call its exit function.
        """

        self._parent.exit()

    def clipped_pos(self):
        """
        Returns visible rectangle of the box in global (screen) coordinates.

        :return tuple: Returns tuple of 4 which holds start
                       and end points of rectangle
        """

        clip_rect = self.clip()
        if clip_rect == None:
            return (-1, -1, -1, -1)

        pos = self.to_global(0, 0)
        rect = self.get_style('rect')

        c = self.get_style('background')

        xstart = pos[0] + clip_rect[0]
        xend = xstart + clip_rect[2] - clip_rect[0]

        ystart = pos[1] + clip_rect[1]
        yend = ystart + clip_rect[3] - clip_rect[1]

        return (xstart, ystart, xend, yend)

    def clip(self, add_margin=False):
        """
        Calculate intersection of box rect and parent box rect.

        :arg bool add_margin: Calculate clipped area by considering
                              margin if `add_margin` is `True`.
        :return tuple: Returns 4 tuple reprsents the intersection
        """

        rect = self.get_style('rect')

        if add_margin == True:
            margin = self.get_margin()
        else:
            margin = (0, 0, 0, 0)

        if self._parent == None:
            origin = (rect[0] + margin[3], rect[1] + margin[0])

            size = (
                rect[2] - margin[3] - margin[1],
                rect[3] - margin[2] - margin[0])

            area = (
                origin[0], origin[1],
                origin[0] + size[0], origin[1] + size[1])

            clipped = (0, 0, 0, 0)

            return Bunch(area=area, clipped=clipped)
        else:
            pclip = self._parent.clip(True)
            if not pclip:
                # This means the parent is not in the visible area.
                # Return last clip area when it is outside of screen
                return None

            parea = pclip.area
            pscroll = self._parent.get_style('scroll-pos')

        gorigin = list(self.position_helper('origin'))

        gend = [
            gorigin[0] + rect[2] - margin[1],
            gorigin[1] + rect[3] - margin[2]
        ]

        gorigin[0] += margin[3]
        gorigin[1] += margin[0]

        if gend[0] < parea[0] or gend[1] < parea[1] \
            or gorigin[0] > parea[2] or gorigin[1] > parea[3]:
                # Return last clip area when it is outside of screen
                return None

        dx1 = abs(min(gorigin[0] - parea[0], 0))
        dy1 = abs(min(gorigin[1] - parea[1], 0))
        dx2 = abs(max(gend[0] - parea[2], 0))
        dy2 = abs(max(gend[1] - parea[3], 0))

        # area is defined as a rectangle (x1, y1, x2, y2)
        # Coordinates of top left corner is (x1, y1)
        # and right bottom corner is (x2, y2)
        area = (
            max(gorigin[0], parea[0]), max(gorigin[1], parea[1]),
            min(gend[0], parea[2]), min(gend[1], parea[3])
        )

        clipped = (dx1, dy1, dx2, dy2)

        return Bunch(area=area, clipped=clipped)

    def draw(self):
        """
        Main draw function
        """

        self._setup_draw()
        # **
        if self.get_style('visible'):
            if self.draw_flag('border') > 0:
                self._draw_border()

            if self.draw_flag('background') > 0:
                self._draw_background()

            if self.draw_flag('text') > 0:
                self._draw_text()

        # **
        self._cleanup_draw()

    def deactivate(self):
        """
        Deactivates self and declares that self should be redrawn.
        """

        root = self.follow_path('/root')
        root.deactivate(self)

    def activate(self, box=None):
        """
        Activates box and declares it to main :class:`PazGui` object recursively.
        It is used without an argument.

        :arg PazGui box: Not used. It is only used for recursion.
        """

        root = self.follow_path('/root')
        root.activate(self)

    def activate_sibling(self, backwards=False):
        if self._parent == None:
            return

        siblings = self._parent.child('all')
        s_cnt = len(siblings)

        dir = 1 if not backwards else -1

        try:
            ind = siblings.index(self)
            ind = (ind + dir) % s_cnt

            sibling = self._parent.child(ind)

            if sibling != self:
                sibling.activate()
        except ValueError:
            # TODO: Catch error.
            pass

    def hide(self):
        self.set_style('visible', False)
        self.draw_flag('all', 1)
        self.event_queue(PazEvent('HIDE'), source=self, target=self)

    def show(self):
        self.set_style('visible', True)
        self.draw_flag('all', 1)
        self.event_queue(PazEvent('SHOW'), source=self, target=self)

    def propagate_event(self, ev):
        """
        When an event is received propagated it to all ``PazBox`` instances

        :arg PazEvent ev: An event object
        :return bool: Returns ``True`` is event handled by this instance
        """

        if self._event(ev):
            return True

        for child in self.child('all'):
            if child.propagate_event(ev):
                return True

        return False

    def new_event(self, name, source=None, target=None, queue=False):
        if source == None:
            source = self
        if target == None:
            target = self

        ev = PazEvent(name, source=source, target=target)

        if queue:
            self.event_queue(ev)

        return ev

    def new_messagebox(self, message, title, buttons, active_button=0):
        root = self.follow_path('/root')
        root.new_messagebox(message, title, buttons, active_button)

    def close_messagebox(self):
        root = self.follow_path('/root')
        root.close_messagebox()

    def children(self):
        pass

    def schedule(self):
        pass

    def event(self, ev):
        pass


class PazMessageBox(PazBox):
    name = 'messagebox'

    def __init__(self, *args, **kwargs):
        if 'buttons' in kwargs:
            self.buttons = list(kwargs['buttons'])
            del kwargs['buttons']
        else:
            self.buttons = [ 'OK', 'CANCEL' ]

        if 'active_button' in kwargs:
            self.active_button = kwargs['active_button']
            del kwargs['active_button']
        else:
            self.active_button = 0

        if 'title' in kwargs:
            self._title = kwargs['title']
            del kwargs['title']
        else:
            self._title = 'Message box'

        if 'message' in kwargs:
            self.text = kwargs['message']
            del kwargs['message']
        else:
            self.text = ''

        self.style = {
            'rect': (0.1, 0.3, 0.8, 0.4),
            'border': True,
            'behavior': {
                PazPanel: {
                    'text': self._title,
                },
                PazAlwaysDraw: { 'propagate': True },
            },
            'z-index': float('inf'),
        }

        super(PazMessageBox, self).__init__(*args, **kwargs)

        i = 0
        for child in self.child(0).child('all'):
            child.set_text(self.buttons[i])
            i += 1

    def activate(self):
        self.child(0).child(self.active_button).activate()

    def children(self):
        class HBox(PazBox):
            name = "buttons"
            style = {
                'rect': (0, 0, 30, 7),
                'behavior': {
                    PazHBox: { },
                },
                'align-x': 'right',
                'align-y': 'bottom',
            }

            def children(self):
                class Button(PazBox):
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'border': True,
                        'border-style': 'green',
                        'border-style:active': 'red',
                        'behavior': {
                            PazButton: { },
                        },
                        'stretch-ratio': 1 / len(self._parent.buttons),
                    }

                    def event(self, ev):
                        if ev.cmp('PRESSED'):
                            ev = PazEvent('MESSAGEBOX', data=self.get_text())
                            self.event_queue(ev)
                            self.close_messagebox()
                            return True

                return [ Button ] * len(self._parent.buttons)

            def event(self, ev):
                pass

        return [ HBox ]

    def event(self, ev):
        pass


class PazGui(PazBox):
    """
    Main GUI class. It inheriths :class:`.PazBox`.
    Holds the main loop. Checks inputs and events, redraws screen.
    """

    def __init__(self, box_cls, config={ }, stream=None, **kwargs):
        """
        Initialize PazGui.

        :arg PazBox box_cls: Root PazBox class to be instanced.
        :arg dict config: Holds gui configuration.
        :arg str name: Name of the application.
        :arg io.StringIO stream: A stream object to redirect framebuffer output
            to a file or an other sink.
        """

        # Default configuration
        self._config = {
            'key-timeout': 0.01,
            'loop-wait': 0.01,
        }
        for n in config:
            self._config[n] = config[n]

        if 'log' not in self._config:
            self._config['log'] = __file__

        init_logger(self._config['log'])

        if stream == None:
            self._term = Terminal()
        else:
            self._term = Terminal(stream=stream)

        self._event_queue = [ ]
        self._active_box = None
        self._captured_sys_signals = [
            signal.SIGWINCH, # When window is resized.
        ]
        self._set_sys_signals()

        self._tab_indices = { }
        self._max_tab_index = -1

        self.name = 'root'

        self._frame_buffer = FrameBuffer(self._term)
        super(PazGui, self).__init__(buff=self._frame_buffer, par=None)

        self._behavior = [ ]

        self.set_style('z-index', 0)

        self._z_buffer = { }
        self._max_z_index = self.get_style('z-index')
        self._min_z_index = self._max_z_index

        self._terminate = False
        self.width = self._term.width
        self.height = self._term.height

        self.messagebox = None

        # Resize gui according to terminal size.
        self.gui_resize(propagate=False)

        # Root ``PazBox`` in the tree
        box = box_cls(self._frame_buffer, self, **kwargs)
        self.add_child(box)

        # Resize all boxes initially.
        self.gui_resize()

        box.activate()

    def _set_sys_signals(self):
        for sig in self._captured_sys_signals:
            signal.signal(sig, self._sys_signal_handler)

    def _sys_signal_handler(self, signum, frame):
        pending_signals = signal.sigpending()
        # If new signal is already in pending signals
        # ignore the new one.
        if signum in pending_signals:
            return

        self.event_queue(
            PazEvent(signal.Signals(signum).name, source='SYS', target=self)
        )

    def _kbd_input(self):
        inp = self._term.inkey(timeout=self._config['key-timeout'])
        if not inp:
            ev = None
        elif inp.is_sequence:
            ev = PazEvent(inp.name, source='KBD')
        else:
            ev = PazEvent(str(inp), source='KBD')

        if ev:
            self.event_queue(ev)

    def _process_events(self):
        update = False
        ev = self.event_queue()

        while ev != None:
            # ``update`` is ``True`` when a ``PazBox`` handles the event.
            update |= self.propagate_event(ev) or False
            ev = self.event_queue()

        return update

    def _process_inputs(self):
        self._kbd_input()

    def _loop_cleanup(self):
        pass

    def _event(self, ev):
        ret = self._gui_event(ev) or False

        if ret:
            return True

        if not ev.is_target(self):
            return False

        ret |= self._run_behavior('pre_event', { 'ev': ev }) or False
        if ret: return True
        #
        ret |= self.event(ev) or False
        if ret: return True
        #
        ret |= self._run_behavior('post_event', { 'ev': ev }) or False
        if ret: return True

        return ret

    def _gui_event(self, ev):
        if ev.cmp('SIGWINCH'):
            self._frame_buffer.resize()
            self.gui_resize()
            return True
        elif ev.cmp(_kc.CTRL('C')):
            print('Exiting!')
            self.exit()
            return True
        elif ev.cmp('KEY_TAB'):
            self.activate_next()
            return True
        elif ev.cmp('KEY_BTAB'):
            self.activate_next(backwards=True)
            return True
        elif ev.cmp('QUIT'):
            return self.on_quit(ev)

    def _event_queue_has(self, ev):
        for event in self._event_queue:
            if event.cmp(ev):
                return True

        return False

    def _fill_z_buffer(self, box=None):
        if box == None:
            box = self

        z_index = box.get_style('z-index')

        for child in box.child('all'):
            cz_index = child.get_style('z-index')

            if cz_index < z_index:
                # If child has a smaller z-index, then dont draw it.
                continue

            if z_index not in self._z_buffer:
                self._z_buffer[z_index] = [ ]

            self._z_buffer[z_index].append(child)

            if z_index > self._max_z_index:
                self._max_z_index = z_index
            elif z_index < self._min_z_index:
                self._min_z_index = z_index

            self._fill_z_buffer(child)

    def get_config(self, name):
        if name in self._config:
            return self._config[name]
        else:
            return None

    def set_tab_index(self, box, ind):
        """
        User can activate GUI elements according to their ``tab-index``.
        In order to find the next GUI element that will be actived,
        they are placed in a dictionary in which tab indices are
        keys and corresponding ``PazBox``es are values.

        :arg PazBox box: The ``PazBox`` instance to be added as a value
        :arg int ind: The key for the ``PazBox``
        """

        if self == box:
            return

        if ind > -1:
            self._tab_indices[ind] = new_weakref(box)
            if ind > self._max_tab_index:
                self._max_tab_index = ind
        else:
            self._max_tab_index += 1
            self._tab_indices[self._max_tab_index] = new_weakref(box)
            box.set_style('tab-index', self._max_tab_index)

    def remove_tab_index(self, box):
        if self == box:
            return

        index = None
        for _index, _box in self._tab_indices.items():
            if _box == box:
                index = _index
                break

        if index != None:
            del self._tab_indices[index]

    def activate_next(self, backwards=False):
        """
        Activates the first ``PazBox`` with the tab index one larger than
        current active box.
        """

        if self._active_box:
            active_tab_index = self._active_box.get_style('tab-index')
        else:
            active_tab_index = 0

        sorted_indices = sorted(self._tab_indices.keys(), reverse=backwards)
        tab_indices_count = len(sorted_indices)

        tab_index = -1
        try:
            ind = sorted_indices.index(active_tab_index)
            if ind + 1 < tab_indices_count:
                tab_index = sorted_indices[ind+1]
            else:
                tab_index = sorted_indices[0]
        except ValueError:
            for i in range(tab_indices_count):
                tab_index = sorted_indices[i]
                if not backwards and tab_index > active_tab_index:
                    break
                elif backwards and tab_index < active_tab_index:
                    break

        try:
            if tab_index > -1 and tab_index != active_tab_index:
                self._tab_indices[tab_index].activate()
            else:
                self._tab_indices[sorted_indices[0]].activate()
        except ReferenceError:
            # For the case when a box is removed.
            if self.children_count() > 0:
                self.child(0).activate()

    def gui_resize(self, propagate=True):
        """
        Resize everything on terminal size change.
        """

        self.set_style('rect', (0, 0, self._term.width, self._term.height))
        self.set_style('original-rect', self.get_style('rect'))
        self.set_style('original-margin', self.get_style('margin'))

        if propagate:
            self._resize()
        else:
            self.resize()

    def event_queue(self, ev=None):
        if type(ev) == PazEvent and not self._event_queue_has(ev):
            self._event_queue.append(ev)
        elif ev == None:
            if len(self._event_queue) > 0:
                return self._event_queue.pop(0)
            else:
                return None

    def exit(self):
        self._terminate = True

    def run(self):
        with self._term.fullscreen(), self._term.location(x=0, y=0),\
             self._term.raw(), self._term.keypad(),\
             self._term.hidden_cursor():

            try:
                # Inital draw and print to screen
                self.draw()
                self.clear()
                self.update()

                while not self._terminate:
                    # Read keyboard input.
                    self._process_inputs()
                    # Run scheduled events.
                    self.scheduler.run_pending()
                    # If ``update`` is ``True`` a ``PazBox`` handled the event
                    # then screen must be refreshed.
                    updated = self._process_events()

                    if updated:
                        # Fill the frame buffer.
                        self.draw()
                        # Print the frame buffer.
                        # TODO: Update when all draw events are done.
                        self.update()
                    else:
                        time.sleep(self._config['loop-wait'])

                    self._loop_cleanup()

            except Exception as e:
                # Catch all exceptions and log traceback.
                logger().error(traceback.format_exc())

            self._gui_event(PazEvent('QUIT', self, self))

    def clear(self):
        self._frame_buffer.clear()

    def update(self):
        self._frame_buffer.update()

    def draw(self, box=None):
        """
        Draws all ``PazBox``s in the tree recursively.

        :arg PazBox box: ``PazBox`` instance to be drawn
        """

        self._z_buffer.clear()
        # Order boxes according to their z-index
        self._fill_z_buffer()

        z_vals = list(self._z_buffer.keys())
        z_vals.sort()
        for z in z_vals:
            for box in self._z_buffer[z]:
                if box == self:
                    continue

                box.draw()

    def deactivate(self, box):
        if self._active_box != box:
            return

        box.set_style('active', False)
        box.draw_flag('all', 1, propagate=True)

        self._active_box = None

        # Place a 'DEACTIVATE' event into the event queue.
        self.event_queue(PazEvent('DEACTIVATE', source=box, target=box))

    def activate(self, box=None):
        """
        Changes active box after deactivating current active box.

        :arg PazBox box: PazBox that is activated.
        """

        if self._active_box == box:
            return

        if self._active_box != None:
            self._active_box.deactivate()

        box.set_style('active', True)
        box.draw_flag('all', 1, propagate=True)

        self._active_box = new_weakref(box)

        # Place an 'ACTIVATE' event into the event queue.
        self.event_queue(PazEvent('ACTIVATE', source=box, target=box))

    def propagate_event(self, ev):
        """
        When an event is received propagated it to all ``PazBox`` instances

        :arg PazEvent ev: An event object
        :return bool: Returns ``True`` is event handled by this instance
        """

        if self._active_box:
            # Check the events of active box first.
            if self._active_box.propagate_event(ev):
                return True

        for child in self.child('all'):
            if child.propagate_event(ev):
                return True

        if self._event(ev):
            return True

        return False

    def on_quit(self, ev):
        self._frame_buffer.clear()

    def new_messagebox(self, message, title, buttons, active_button=0):
        if self.messagebox:
            self.remove_child(self.messagebox)

        box = PazMessageBox(
            self._frame_buffer, par=self, message=message,
            title=title, buttons=buttons, active_button=active_button
        )

        self.add_child(box)
        box.activate()

        self.gui_resize()

        self.messagebox = new_weakref(box)

    def close_messagebox(self):
        if self.messagebox:
            self.messagebox.deactivate()
            self.remove_child(self.messagebox)

