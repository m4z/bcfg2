""" Inotify driver for file alteration events """

import os
import stat
import logging
import operator
import pyinotify
from Bcfg2.Server.FileMonitor import Event
from Bcfg2.Server.FileMonitor.Pseudo import Pseudo

logger = logging.getLogger(__name__)

class Inotify(Pseudo, pyinotify.ProcessEvent):
    __priority__ = 1
    mask = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MODIFY
    action_map = {pyinotify.IN_CREATE: 'created',
                  pyinotify.IN_DELETE: 'deleted',
                  pyinotify.IN_MODIFY: 'changed'}

    def __init__(self, ignore=None, debug=False):
        Pseudo.__init__(self, ignore=ignore, debug=debug)
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, self)
        self.notifier.start()

    def fileno(self):
        return self.wm.get_fd()

    def process_default(self, ievent):
        action = ievent.maskname
        for amask, aname in self.action_map.items():
            if ievent.mask & amask:
                action = aname
                break
        # FAM-style file monitors return the full path to the parent
        # directory that is being watched, relative paths to anything
        # contained within the directory
        watch = self.wm.watches[ievent.wd]
        if watch.path == ievent.pathname:
            path = ievent.pathname
        else:
            # relative path
            path = os.path.basename(ievent.pathname)
        evt = Event(ievent.wd, path, action)
        self.events.append(evt)

    def AddMonitor(self, path, obj):
        res = self.wm.add_watch(path, self.mask, quiet=False)
        if not res:
            # if we didn't get a return, but we also didn't get an
            # exception, we're already watching this directory, so we
            # need to find the watch descriptor for it
            for wd, watch in self.wm.watches.items():
                if watch.path == path:
                    wd = watch.wd
        else:
            wd = res[path]

        # inotify doesn't produce initial 'exists' events, so we
        # inherit from Pseudo to produce those
        return Pseudo.AddMonitor(self, path, obj, handleID=wd)

    def shutdown(self):
        self.notifier.stop()
