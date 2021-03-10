import os
import io
import logging
from collections.abc import MutableMapping
import weakref


LOGGER = 'pazgui-app'


def logger():
    return logging.getLogger(LOGGER)


def init_logger(name, level=logging.INFO):
    logger = logging.getLogger(LOGGER)
    logger.setLevel(level)

    formatter = logging.Formatter((
        '{"unix_time":%(created)s, "time":"%(asctime)s", "module":"%(name)s",'
        ' "line_no":%(lineno)s, "level":"%(levelname)s", "msg":"%(message)s"},'
    ))

    log_filename = os.path.splitext(name)[0] + '.log'
    fh = open(log_filename, 'a')

    ch = logging.StreamHandler(fh)
    ch.setFormatter(formatter)

    ch.setLevel(level)
    logger.addHandler(ch)

    logger.info('Logger started.')


def new_weakref(obj):
    try:
        return weakref.proxy(obj)
    except TypeError:
        return obj


class TestOut(io.StringIO):
    def __init__(self):
        super().__init__()

    def get_frame(self, fsize, tsize):
        val = self.getvalue()

        frame = ''
        ind = 0
        for i in range(fsize[1]):
            frame += val[ind:ind+fsize[0]] + '\n'
            ind += tsize[0]

        return frame

    def write_frame(self, fh, fsize, tsize):
        val = self.getvalue()

        frame = ''
        ind = 0
        for i in range(fsize[1]):
            fh.write(val[ind:ind+fsize[0]] + '\n')
            ind += tsize[0]


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class DeepDict(MutableMapping):
    """
    A dictionary class that creates sub dictionaries
    automatically.
    """

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        """
        If a key does not exists in the tree.
        It creates a new branch with the key.
        """

        if key not in self.store:
            self.store[key] = DeepDict()

        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __contains__(self, key_list):
        if type(key_list) != list:
            key_list = [ key_list ]

        key = key_list.pop(0)
        if key in self.store:
            if type(self.store[key]) == DeepDict and len(key_list) > 0:
                return key_list in self.store[key]
            else:
                return True
        else:
            return False


class StyleDict(DeepDict):
    def __init__(self, *args, parent=None, **kwargs):
        if type(parent) == DeepDict and parent.depth == 3:
            return list()

        super(StyleDict, self).__init__(*args, **kwargs)

        self.parent = parent
        if type(self.parent) == StyleDict:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    def __getitem__(self, key):
        """
        If a key does not exists in the tree.
        It creates a new branch with the key.
        """

        if key not in self.store:
            self.store[key] = StyleDict(parent=self)

        return self.store[key]

    def clear_lte(self, key):
        if type(key) == int:
            del_keys = [ ]
            for _key in self.store:
                if _key <= key:
                    del_keys.append(_key)
                else:
                    # Return if a key larger than provided exists
                    break

            for _key in del_keys:
                del self.store[_key]

