each tcp server instance has a timer thread that kills itself after 5min and updates db with remaining time every 30s

client unique key: name

we dont care if the highest bidder is reachable

made following changes to appjar.py:

line 5341:

    def startSubWindow(self, name, title=None, stopfunc=None, modal=False, blocking=False, transient=False, grouped=True):
        self.widgetManager.verify(self.Widgets.SubWindow, name)
        gui.trace("Starting subWindow %s", name)

        if stopfunc is None:
            top = SubWindow(self, self.topLevel, name, title=title, stopFunc = self.confirmHideSubWindow,
                            modal=modal, blocking=blocking, transient=transient, grouped=grouped)
        else:
            top = SubWindow(self, self.topLevel, name, title=title, stopFunc = stopfunc,
                            modal=modal, blocking=blocking, transient=transient, grouped=grouped)