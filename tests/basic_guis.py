import os

from pazgui import gui as pg
from pazgui import behavior as pb


global gtest_can_quit
gtest_can_quit = True


def auto_quit():
    global gtest_can_quit
    gtest_can_quit = True


class TestBehavior(pb.PazBehavior):
    def __init__(self, *args, **kwargs):
        super(TestBehavior, self).__init__(*args, **kwargs)

    def cleanup_draw(self, params=None):
        if self._ctx.test_can_quit:
            self._ctx.exit()


class TestBox(pg.PazBox):
    global gtest_can_quit
    test_can_quit = gtest_can_quit

    def exit(self):
        self._parent.exit()


"""************************** Box with background ***************************"""


class PazBox01WithBackground1(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
    }


class PazBox01WithBackground2(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'O',
                'rect': (1, 1, 9, 9),
            }

        return [ InnerBox1 ]


class PazBox01WithBackground3(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'margin': (1, 1, 1, 2),
        'behavior': { TestBehavior: None },
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'Z',
                'rect': (1, 1, 9, 9),
            }

        return [ InnerBox1 ]


"""********************* Box with background and border *********************"""


class PazBox02WithBackgroundandBorder1(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox02WithBackgroundandBorder2(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'O',
                'rect': (1, 1, 9, 9),
                'border': True,
            }

        return [ InnerBox1 ]


class PazBox02WithBackgroundandBorder2_1(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'O',
                'rect': (1, 1, 6, 6),
                'border': True,
            }

        return [ InnerBox1 ]


class PazBox02WithBackgroundandBorder3(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'margin': (1, 1, 1, 2),
        'behavior': { TestBehavior: None },
        'border': True,
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'Z',
                'rect': (1, 1, 9, 9),
                'border': True,
            }

        return [ InnerBox1 ]


class PazBox02WithBackgroundandBorder3_1(TestBox):
    style = {
        'background': 'X',
        'rect': (0, 0, 9, 9),
        'margin': (1, 1, 1, 2),
        'behavior': { TestBehavior: None },
        'border': True,
    }

    def children(self):
        class InnerBox1(pg.PazBox):
            style = {
                'background': 'Z',
                'rect': (1, 1, 3, 4),
                'border': True,
            }

        return [ InnerBox1 ]


"""************************ Box with text and above *************************"""


class PazBox03WithTextAndAbove1(TestBox):
    text = "te tse <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove2(TestBox):
    text = "tes tse <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove3(TestBox):
    text = "tes tse\n <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove4(TestBox):
    text = "tes\ttse <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove5(TestBox):
    text = "tes\ttse<t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove6(TestBox):
    text = "tes\ttffflse <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox03WithTextAndAbove7(TestBox):
    text = "\ntes\ttse <t>teeest</t>"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'behavior': { TestBehavior: None },
        'border': True,
    }


"""*************************** Drawing sizing tests *************************"""


class PazBox04DrawingSizing01(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing02(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (1, 0, 0, 0),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing03(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (1, 0, 0, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing04(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (1, 0, 0, -1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing05(TestBox):
    text = " test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (1, 1, 0, 0),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing06(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'scroll-pos': (0, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing07(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'scroll-pos': (1, 0),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing08(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'scroll-pos': (1, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing09(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'scroll-pos': (-1, -1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing10(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'scroll-pos': (-3, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing11(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (2, 0, 0, 0),
        'scroll-pos': (0, 2),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing12(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (1, 0, 0, 1),
        'scroll-pos': (1, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing13(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (-1, 0, 0, -1),
        'scroll-pos': (-1, -1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing14(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 7, 7),
        'margin': (-1, 0, 0, -1),
        'scroll-pos': (-1, 1),
        'behavior': { TestBehavior: None },
        'border': True,
    }


class PazBox04DrawingSizing15(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': { TestBehavior: None },
        'border': True,
    }

    def children(self):
        class InnerPazBox(TestBox):
            text = "abc abc"
            style = {
                'background': '*',
                'rect': (0, 0, 6, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': False,
            }

        return [ InnerPazBox ]


class PazBox04DrawingSizing16(TestBox):
    text = "test test"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': { TestBehavior: None },
        'border': False,
    }

    def children(self):
        class InnerPazBox(TestBox):
            text = "abc abc"
            style = {
                'background': 'o',
                'rect': (2, 2, 6, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': False,
            }

        return [ InnerPazBox ]


class PazBox04DrawingSizing17(TestBox):
    text = "\n\n\n\ntest test"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': { TestBehavior: None },
        'border': False,
    }

    def children(self):
        class InnerPazBox(TestBox):
            text = "abc abc"
            style = {
                'background': 'o',
                'rect': (-2, -1, 6, 6),
                'margin': (0, 0, 0, 2),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': False,
            }

        return [ InnerPazBox ]


class PazBox04DrawingSizing18(TestBox):
    text = "     test      test"
    style = {
        'background': 'x',
        'rect': (0, 0, 9, 9),
        'margin': (2, 0, 0, 0),
        'scroll-pos': (0, 1),
        'behavior': { TestBehavior: None },
        'border': False,
    }

    def children(self):
        class InnerPazBox(TestBox):
            text = "abc abc"
            style = {
                'rect': (0, 0, 6, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': False,
            }

        return [ InnerPazBox ]


"""******************************* H/VBox tests *****************************"""


class PazBox05HVBox01(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 12, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': {
            TestBehavior: None,
            pb.PazHBox: { },
        },
        'border': False,
    }

    def children(self):
        class InnerPazBox1(TestBox):
            text = "abc abc"
            style = {
                'rect': (0, 1, 6, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': True,
                'stretch-ratio': 0.5,
            }

        return [ InnerPazBox1, InnerPazBox1 ]


class PazBox05HVBox02(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 12, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': {
            TestBehavior: None,
            pb.PazVBox: { },
        },
        'border': False,
    }

    def children(self):
        class InnerPazBox1(TestBox):
            text = "abc abc"
            style = {
                'rect': (0, 0, 6, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': { TestBehavior: None },
                'border': True,
                'stretch-ratio': 0.5,
            }

        return [ InnerPazBox1, InnerPazBox1 ]


class PazBox05HVBox03(TestBox):
    style = {
        'background': 'x',
        'rect': (0, 0, 12, 9),
        'margin': (0, 0, 0, 0),
        'scroll-pos': (0, 0),
        'behavior': {
            TestBehavior: None,
            pb.PazVBox: { },
        },
        'border': False,
    }

    def children(self):
        class InnerPazBox1(TestBox):
            style = {
                'rect': (0, 0, 1.0, 6),
                'margin': (0, 0, 0, 0),
                'scroll-pos': (0, 0),
                'behavior': {
                    TestBehavior: None,
                    pb.PazHBox: { },
                },
                'border': True,
                'stretch-ratio': 0.5,
            }

            def children(self):
                class InnerInnerPazBox1(TestBox):
                    text = "abc \n\t12"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'background': 'o',
                        'stretch-ratio': 0.6,
                    }

                class InnerInnerPazBox2(TestBox):
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'background': '*',
                        'stretch-ratio': 0.4,
                    }

                return [ InnerInnerPazBox1, InnerInnerPazBox2 ]

        return [ InnerPazBox1 ] * 2

