from pazgui import gui as pg
from pazgui import behavior as pb


class MainBox(pg.PazBox):
    name = "main"
    style = {
        'rect': (0, 0, 1.0, 1.0),
        'behavior': {
            pb.PazHBox: { }
        },
    }

    def __init__(self, *args, **kwargs):
        if 'contacts' in kwargs:
            self.contacts = list(kwargs['contacts'])
            del kwargs['contacts']
        else:
            self.contacts = [ ]

        if 'username' in kwargs:
            self.username = kwargs['username']
            del kwargs['username']
        else:
            self.username = "Me"

        super(MainBox, self).__init__(*args, **kwargs)

    def children(self):
        class SideBar(pg.PazBox):
            name = "sidebar"
            style = {
                'rect': (0, 0, 1.0, 1.0),
                'stretch-ratio': 0.2,
                'border': True,
                'border-style:active': 'gray',
            }

            def __init__(self, *args, **kwargs):
                super(SideBar, self).__init__(*args, **kwargs)

                i = 0
                for child in self.child('all'):
                    child.set_text('{}'.format(
                        self._parent.contacts[i]
                    ))
                    i += 1

            def children(self):
                HEIGHT = 2
                class Contact(pg.PazBox):
                    class ListBehavior(pb.PazBehavior):
                        def pre_create(self, params=None):
                            sibling_count = self._ctx.sibling_count()
                            rect = list(self._ctx.get_style('rect'))
                            rect[1] = HEIGHT * sibling_count
                            self._ctx.set_style('original-rect', tuple(rect))

                    style = {
                        'rect': (0, 0, 1.0, HEIGHT),
                        'background-style:active': 'on_green',
                        'background-style': 'on_blue',
                        'behavior': {
                            ListBehavior: { },
                            pb.PazButton: { },
                        },
                    }

                    def event(self, ev):
                        if ev.cmp('PRESSED'):
                            ev = pg.PazEvent(
                                'NEW_CHAT', self,
                                '/root/main/main-container/chat-history',
                                data={ 'contact-name': self.get_text() }
                            )
                            self.event_queue(ev)
                            return True

                return [ Contact ] * len(self._parent.contacts)

        class MainContainer(pg.PazBox):
            name = "main-container"
            style = {
                'rect': (0, 0, 1.0, 1.0),
                'stretch-ratio': 0.8,
                'behavior': {
                    pb.PazVBox: { }
                }
            }

            def children(self):
                class ChatHistory(pg.PazBox):
                    text = ""
                    name = "chat-history"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'stretch-ratio': 0.8,
                        'behavior': {
                            pb.PazPanel: {
                                'text': '',
                            }
                        },
                        'border-style:active': 'gray',
                    }

                    def event(self, ev):
                        if ev.cmp('NEW_CHAT'):
                            contact_name = ev.get('contact-name')
                            if contact_name:
                                self.get_behavior(pb.PazPanel).attr('text', contact_name)
                            return True
                        elif ev.cmp('NEW_MESSAGE'):
                            message = ev.get('message')
                            text = self.get_text()
                            self.set_text('{}\nMe: {}'.format(text, message))
                            return True

                class ChatInput(pg.PazBox):
                    class FilteredTextArea(pb.PazTextArea):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, **kwargs)

                            self._filter_key += [ 'KEY_ENTER' ]

                    class SendOnEnterKey(pb.PazBehavior):
                        def pre_event(self, params):
                            if params['ev'].cmp('KEY_ENTER'):
                                ev = pg.PazEvent(
                                    'NEW_MESSAGE', self._ctx,
                                    '/root/main/main-container/chat-history',
                                    data={ 'message': self._ctx.get_text() }
                                )
                                self._ctx.event_queue(ev)
                                self._ctx.clear_text()
                                return True

                    name = "chat-input"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'stretch-ratio': 0.2,
                        'border': True,
                        'border-style:active': 'blue',
                        'behavior': {
                            pb.PazPanel: {
                                'text': self._parent.username,
                            },
                            SendOnEnterKey: { },
                            FilteredTextArea: { },
                        },
                        'border-style:active': 'gray',
                    }

                return [ ChatHistory, ChatInput ]

        return [ SideBar, MainContainer ]


class LoginBox(pg.PazBox):
    name = "login-box"
    style = {
        'rect': (0, 0, 1.0, 1.0),
    }

    def children(self):
        class LoginContainer(pg.PazBox):
            name = "login-container"
            style = {
                'rect': (0.4, 0.4, 0.2, 12),
                'background-style': 'on_white',
                'behavior': {
                    pb.PazVBox: { }
                },
            }

            def children(self):
                class Username(pg.PazBox):
                    name = "username"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'behavior': {
                            pb.PazTextBox: { },
                            pb.PazPanel: {
                                'text': 'Username',
                            },
                        },
                        'border': True,
                        'border-style:active': 'gray',
                        'stretch-ratio': 0.33,
                    }

                class Password(pg.PazBox):
                    name = "password"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'behavior': {
                            pb.PazPasswordBox: { },
                            pb.PazPanel: {
                                'text': 'Password',
                            },
                        },
                        'border': True,
                        'border-style:active': 'gray',
                        'stretch-ratio': 0.33,
                    }

                class Submit(pg.PazBox):
                    name = "submit"
                    text = "Submit"
                    style = {
                        'rect': (0, 0, 1.0, 1.0),
                        'stretch-ratio': 0.33,
                        'behavior': {
                            pb.PazButton: { }
                        },
                        'background-style': 'red',
                        'background-style:active': 'red_on_white',
                        'border': True,
                    }

                    def event(self, ev):
                        if ev.cmp('PRESSED'):
                            login_box = self.follow_path('/root/login-box')
                            username = self.follow_path(
                                '/root/login-box/login-container/username'
                            )

                            root = self.follow_path('/root')
                            main_box = MainBox(
                                self._buffer, root,
                                username = username.get_text().strip(),
                                contacts = [ 'Good', 'Bad', 'Ugly' ],
                            )

                            #root.gui_resize(propagate=False)
                            root.remove_child(root.child(0))

                            root.add_child(main_box)
                            root.gui_resize()

                            main_box.activate()

                return [ Username, Password, Submit ]

        return [ LoginContainer ]


if __name__ == "__main__":
    app = pg.PazGui(LoginBox)#, contacts=[ 'C1', 'C2' ])
    app.run()

