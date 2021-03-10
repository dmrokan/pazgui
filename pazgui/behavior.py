from pazgui.accessories import new_weakref

"""
Decorators
----------

"""

def when_active(func):
    def wrapper(*args, **kwargs):
        if args[0]._ctx.get_style('active'):
            return func(*args, **kwargs)

    return wrapper

def disable_scroll(func):
    def wrapper(*args, **kwargs):
        args[0]._ctx.set_style('scroll-x', False)
        args[0]._ctx.set_style('scroll-y', False)
        return func(*args, **kwargs)

    return wrapper


"""
Box behaviors
-------------

"""

class PazBehavior(object):
    def __init__(self, ctx, attr={ }):
        self._attributes = { }
        if attr:
            for a in attr:
                self._attributes[a] = attr[a]

        self._ctx = new_weakref(ctx)
        self._activate_key = self._ctx.get_style('activate-key')

    def mood(self, m=None):
        return self._mood

    def attr(self, n, a=None):
        if n in self._attributes:
            if a == None:
                return self._attributes[n]
            else:
                self._attributes[n] = a
                self._ctx.draw_flag('all', 1)
        else:
            return None

    def setup_draw(self):
        pass

    def cleanup_draw(self):
        pass

    def pre_draw_border(self, params):
        pass

    def post_draw_border(self, params):
        pass

    def pre_draw_background(self, params):
        pass

    def post_draw_background(self, params):
        pass

    def pre_draw_text(self, params):
        pass

    def post_draw_text(self, params):
        pass

    def pre_create(self, params=None):
        pass

    def post_create(self, params=None):
        pass

    def pre_resize(self, params=None):
        pass

    def post_resize(self, params=None):
        pass

    def pre_event(self, params):
        ev = params['ev']

        if ev.cmp(self._activate_key):
            self._ctx.activate()
            return True

    @when_active
    def post_event(self, params):
        ev = params['ev']

        if ev.cmp(self._ctx.get_style('scroll-up-key')):
            self._ctx.scroll((0, -1))
            return True
        elif ev.cmp(self._ctx.get_style('scroll-down-key')):
            self._ctx.scroll((0, 1))
            return True
        elif ev.cmp(self._ctx.get_style('deactivate-key')):
            self._ctx.deactivate()
            return True
        elif ev.cmp(self._ctx.get_style('navigate-forwards')):
            self._ctx.activate_sibling()
            return True
        elif ev.cmp(self._ctx.get_style('navigate-backwards')):
            self._ctx.activate_sibling(backwards=True)
            return True


class PazLabeled(PazBehavior):
    def __init__(self, *args, **kwargs):
        """
        Adds a label onto a given position.

        Attributes are:
        text, position

        :arg PazBox ctx: Related ``PazBox`` instance to which behaviour applies.
        :arg dict attr: Behaviour attributes
        """

        if kwargs['attr']:
            attributes = kwargs['attr']
        else:
            attributes = { }
            kwargs['attr'] = attributes

        if 'text' not in attributes:
            attributes['text'] = ''

        if 'draw-on' not in attributes:
            if attributes['text']:
                attributes['draw-on'] = 'border;background'

        super(PazLabeled, self).__init__(*args, **kwargs)

        self._label_area = None

        self._draw_on = [ ]
        draw_on = self.attr('draw-on')

        if draw_on:
            self._draw_on = [ s.strip() for s in self.attr('draw-on').split(';') ]

    def _draw_label(self, params):
        origin = self._ctx.position_helper('origin')
        px, py = self.attr('position')

        startx = origin[0] + px
        starty = origin[1] + py

        endx = startx + len(self.attr('text'))
        endy = starty

        self._label_area = [ startx, starty, endx, endy ]

        x = params.x
        y = params.y

        chr_ind = x - self._label_area[0]

        if chr_ind < 0:
            return

        if x >= self._label_area[0] and x < self._label_area[2] \
            and y == self._label_area[1]:
            self._ctx.draw_xy(x, y, self.attr('text')[chr_ind], 'me')

    def post_draw_background(self, params):
        if 'background' in self._draw_on:
            self._draw_label(params)

    def post_draw_border(self, params):
        if 'border' in self._draw_on:
            self._draw_label(params)

    def post_draw_text(self, params):
        if 'text' in self._draw_on:
            self._draw_label(params)


class PazCheckbox(PazLabeled):
    def __init__(self, *args, **kwargs):
        self._check_mark = 'x'
        self._check_unmark = ' '
        self._check_format = '[{}]'

        if kwargs['attr']:
            attributes = kwargs['attr']
        else:
            attributes = { }
            kwargs['attr'] = attributes

        if 'check-mark' in attributes:
            self._check_mark = attributes['check-mark']

        if 'check-unmark' in attributes:
            self._check_unmark = attributes['check-unmark']

        if 'position' not in attributes:
            attributes['position'] = (1, 1)

        if 'draw-on' not in attributes:
            attributes['draw-on'] = 'background'

        if 'spacing' not in attributes:
            attributes['spacing'] = 1

        attributes['text'] = self._check_format.format(self._check_unmark)
        if 'checked' in attributes:
            if attributes['checked'] == True:
                attributes['text'] = self._check_format.format(self._check_mark)

        super(PazCheckbox, self).__init__(*args, **kwargs)

    def _toggle(self):
        checked = self.attr('checked')

        mark = None
        if checked:
            mark = self._check_unmark
        else:
            mark = self._check_mark

        self.attr('text', self._check_format.format(mark))
        self.attr('checked', not checked)

    @disable_scroll
    def pre_create(self, params=None):
        margin = self._ctx.get_style('margin')

        checker_len = len(self._check_format.format(self._check_mark))
        left_margin = margin[3] + self.attr('spacing') + checker_len

        self._ctx.set_style(
            'margin', (margin[0], margin[1], margin[2], left_margin)
        )

    @when_active
    def post_event(self, params):
        if params['ev'].cmp(' '):
            self._toggle()
            self._ctx.draw_flag('all', 1)
            return True


class PazPanel(PazLabeled):
    def __init__(self, *args, **kwargs):
        attributes = kwargs['attr']
        attributes['draw-on'] = 'border'
        attributes['position'] = (1, 0)

        super(PazPanel, self).__init__(*args, **kwargs)

    def pre_create(self, params):
        self._ctx.set_style('border', True)


class PazHBox(PazBehavior):
    HORIZONTAL=0
    VERTICAL=1
    def __init__(self, *args, **kwargs):
        if 'attr' in kwargs and 'spacing' in kwargs['attr']:
            self._spacing = kwargs['attr']['spacing']
        else:
            # TODO: Use spacing.
            self._spacing = 0

        super(PazHBox, self).__init__(*args, **kwargs)
        self._next_child_rect_start = None
        self._rect = None
        # Split direction
        self._dir = self.HORIZONTAL

    def post_create(self, params=None):
        """
        The adjustments should be done after creating the ``PazBox``.
        At this point children ``PazBox``es have been created and
        HBox behavior can be adjusted by changing the 'original-rect' of
        children boxes.
        """

        self._rect = self._ctx.get_style('content-rect')
        c_cnt = self._ctx.children_count()

        total_ratio = 0.0
        ratios = [ 0.0 ] * c_cnt
        for i in range(c_cnt):
            ratio = self._ctx.child(i).get_style('stretch-ratio')
            if type(ratio) == float or type(ratio) == int:
                ratios[i] = max(0.0, float(ratio))
                total_ratio += ratios[i]

        if total_ratio == 0.0:
            total_ratio = 1.0

        ratios = [ r / total_ratio for r in ratios ]

        length = self._rect[self._dir+2]

        starts_at = 0
        ends_at = 0
        for i in range(c_cnt):
            child = self._ctx.child(i)
            rect = list(child.get_style('rect'))
            rect[self._dir] = starts_at / length

            clength = int(length * ratios[i])
            clength -= self._spacing if i < c_cnt - 1 else 0

            rect[self._dir+2] = clength / length

            rect[1-self._dir] = 0.0
            rect[1-self._dir+2] = 1.0
            child.set_style(
                'original-rect', tuple(rect)
            )

            starts_at += clength + self._spacing


class PazVBox(PazHBox):
    def __init__(self, *args, **kwargs):
        super(PazVBox, self).__init__(*args, **kwargs)
        self._dir = self.VERTICAL


class PazButton(PazBehavior):
    def __init__(self, *args, **kwargs):
        if kwargs['attr']:
            attributes = kwargs['attr']
        else:
            attributes = { }
            kwargs['attr'] = attributes

        if 'key' not in attributes:
            attributes['key'] = 'KEY_ENTER'

        super(PazButton, self).__init__(*args, **kwargs)

        self._key = self.attr('key')

    @disable_scroll
    def post_create(self, params):
        self._ctx.set_style('scroll-x', False)
        self._ctx.set_style('scroll-y', False)

    @when_active
    def post_event(self, params):
        if params['ev'].cmp(self._key):
            ev = self._ctx.new_event('PRESSED', self._ctx, self._ctx, queue=True)
            return True


class PazTextArea(PazBehavior):
    def __init__(self, *args, **kwargs):
        super(PazTextArea, self).__init__(*args, **kwargs)

        self._filter_key = [ ]

    @disable_scroll
    def pre_create(self, params):
        self._ctx.set_style('text', { 'cursor': 'invert' })

    @when_active
    def pre_event(self, params):
        ev = params['ev']

        if ev.isprintable() and ev.name not in self._filter_key:
            if ev.cmp('KEY_DOWN'):
                self._ctx.move_text_cursor((0, 1))
            elif ev.cmp('KEY_LEFT'):
                self._ctx.move_text_cursor((-1, 0))
            elif ev.cmp('KEY_RIGHT'):
                self._ctx.move_text_cursor((1, 0))
            elif ev.cmp('KEY_UP'):
                self._ctx.move_text_cursor((0, -1))
            elif ev.cmp('KEY_BACKSPACE'):
                # '-1' means delete the char just before the cursor.
                self._ctx.modify_text(-1, pos=None, overwrite=True)
            elif ev.cmp('KEY_DELETE'):
                # '0' means delete the char under cursor.
                self._ctx.modify_text(0, pos=None, overwrite=True)
            elif ev.cmp('<'):
                # Add a nonprintable character as place order.
                self._ctx.modify_text('\x01')
            elif ev.cmp('>'):
                # Add a nonprintable character as place order.
                self._ctx.modify_text('\x02')
            elif ev.cmp('&'):
                # Add a nonprintable character as place order.
                self._ctx.modify_text('\x03')
            else:
                self._ctx.modify_text(ev.to_char())

            return True


class PazTextBox(PazTextArea):
    def __init__(self, *args, **kwargs):
        super(PazTextBox, self).__init__(*args, **kwargs)

        self._filter_key = [ 'KEY_ENTER' ]


class PazPasswordBox(PazTextBox):
    def __init__(self, *args, **kwargs):
        super(PazPasswordBox, self).__init__(*args, **kwargs)

        self._filter_key = [ ' ', 'KEY_ENTER', 'KEY_TAB' ]

    def post_draw_text(self, params):
        x = params.x
        y = params.y
        c = params.val

        if c != ' ':
            self._ctx.draw_xy(x, y, '*', 'me')


class PazProgressBar(PazBehavior):
    def __init__(self, *args, **kwargs):
        attributes = kwargs['attr']

        if 'fraction' in attributes:
            self._fraction = attributes['fraction']
        else:
            self._fraction = 0.0

        if 'style' in attributes:
            self._style = attributes['style']
        else:
            self._style = 'black_on_white'

        if 'symbol' in attributes:
            self._symbol = attributes['symbol']
        else:
            self._symbol = ' '

        super(PazProgressBar, self).__init__(*args, **kwargs)

    @disable_scroll
    def pre_create(self, params):
        rect = list(self._ctx.get_style('rect'))
        border = self._ctx.get_style('border')
        margin = self._ctx.get_style('margin')

        # Height of the content rectangle must be one.
        rect[3] = margin[0] + margin[2] + int(border) * 2 + 1

        self._ctx.set_style('rect', tuple(rect))

    def post_event(self, params):
        ev = params['ev']

        if ev.cmp('PROGRESSBAR'):
            self._fraction = min(1.0,
                max(
                    0.0, self._fraction + ev.get('increment')
                )
            )

            w = self._ctx.get_style('content-rect')[2]
            text = '<t s="{}">{}</t>'.format(
                self._style, self._symbol * round(self._fraction * w)
            )
            self._ctx.set_text(text)

            return True


class PazAlwaysDraw(PazBehavior):
    def __init__(self, *args, **kwargs):
        if 'attr' in kwargs and 'propagate' in kwargs['attr']:
            self._propagate = kwargs['attr']['propagate']
        else:
            self._propagate = False

        super(PazAlwaysDraw, self).__init__(*args, **kwargs)

    def cleanup_draw(self):
        self._ctx.draw_flag('all', 1, propagate=self._propagate)

