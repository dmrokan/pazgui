import os
import pytest
import inspect

import zlib

from pazgui import gui as pg
from pazgui import accessories as acc
from tests import basic_guis


def test_txt_output():
    script_filename = __file__
    output_filename = os.path.splitext(script_filename)[0] + '.txt'

    basic_guis.auto_quit()

    hashes = [
        # Starts with PazBox01WithBackground1
        2145333437, 561189371,   2899945982, 108913868,   655346476,
        # Starts with PazBox02WithBackgroundandBorder2_1
        1799185332, 2067708840,  2814749925, 4058853178,  206461469,
        # Starts with PazBox03WithTextAndAbove3
        3125118064, 195328683,   3785169909, 1307881039,  2859426941,
        # Starts with PazBox04DrawingSizing01
        1423885718, 1603296384,  1508511093, 173744682,   2163566388,
        # Starts with PazBox04DrawingSizing06
        2355229980, 1460067754,  845186742,  353265445,   2370478509,
        # Starts with PazBox04DrawingSizing11
        1423885718, 3127350991,  4268370625, 1423885718,  4046093855,
        # Starts with PazBox04DrawingSizing16
        3461946662, 1378706449,  3147652785, 499930921,   1129154302,
        # Starts with PazBox05HVBox03
        1335604955,
    ]

    k = 0
    with open(output_filename, 'w') as fh:
        for name, obj in inspect.getmembers(basic_guis):
            if inspect.isclass(obj) and name.startswith('PazBox'):
                fh.write('* PazBox name: {}\n\n'.format(name))

                stream = acc.TestOut()

                gui = pg.PazGui(obj, stream=stream)
                gui.run()

                size = (gui.width, gui.height)
                frame_size = (min(30, gui.width), min(20, gui.height))
                frame = stream.get_frame(frame_size, size)

                print(frame)

                frame_hash = zlib.crc32(frame.encode('utf-8'))

                assert frame_hash == hashes[k]
                k += 1

