# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import time

from zope.interface import implements
from twisted.python import log
from twisted.internet import defer
from twisted.application import service

from buildbot import interfaces, util

class ChangeManager(service.MultiService):

    """This is the master-side service which receives file change
    notifications from a VCS. It keeps a log of these changes, enough to
    provide for the HTML waterfall display, and to tell
    temporarily-disconnected bots what they missed while they were
    offline.

    Change notifications come from two different kinds of sources. The first
    is a PB service (servicename='changemaster', perspectivename='change'),
    which provides a remote method called 'addChange', which should be
    called with a dict that has keys 'filename' and 'comments'.

    The second is a list of objects derived from the 
    L{buildbot.changes.base.ChangeSource} class. These are added with 
    .addSource(), which also sets the .changemaster attribute in the source 
    to point at the ChangeMaster. When the application begins, these will 
    be started with .start() . At shutdown time, they will be terminated 
    with .stop() . They must be persistable. They are expected to call 
    self.changemaster.addChange() with Change objects.

    There are several different variants of the second type of source:

      - L{buildbot.changes.mail.MaildirSource} watches a maildir for CVS
        commit mail. It uses DNotify if available, or polls every 10
        seconds if not.  It parses incoming mail to determine what files
        were changed.

    """

    implements(interfaces.IEventSource)

    changeHorizon = None
    lastPruneChanges = None
    name = "changemanager"

    def __init__(self):
        service.MultiService.__init__(self)
        self._cache = util.LRUCache()
        self.lastPruneChanges = 0
        self.changeHorizon = 0

    def addSource(self, source):
        assert interfaces.IChangeSource.providedBy(source)
        assert service.IService.providedBy(source)
        source.setServiceParent(self)

    def removeSource(self, source):
        assert source in self
        return defer.maybeDeferred(source.disownServiceParent)

    def addChange(self, change):
        """Deliver a file change event. The event should be a Change object.
        This method will timestamp the object as it is received."""
        msg = ("adding change, who %s, %d files, rev=%s, branch=%s, repository=%s, "
                "comments %s, category %s, project %s" % (change.who, len(change.files),
                                              change.revision, change.branch, change.repository,
                                              change.comments, change.category, change.project))
        log.msg(msg.encode('utf-8', 'replace'))

        # this sets change.number, if it wasn't already set (by the
        # migration-from-pickle code). It also fires a notification which
        # wakes up the Schedulers.
        self.parent.addChange(change)

        self.pruneChanges(change.number)

    def pruneChanges(self, last_added_changeid):
        # this is an expensive operation, so only do it once per second, in case
        # addChanges is called frequently
        if not self.changeHorizon or self.lastPruneChanges > time.time() - 1:
            return
        self.lastPruneChanges = time.time()

        ids = self.parent.db.getChangeIdsLessThanIdNow(last_added_changeid - self.changeHorizon + 1)
        for changeid in ids:
            log.msg("removing change with id %s" % changeid)
            self.parent.db.removeChangeNow(changeid)

    # IEventSource methods

    def eventGenerator(self, branches=[], categories=[], committers=[], minTime=0):
        return self.parent.db.changeEventGenerator(branches, categories,
                                                   committers, minTime)

    def getChangeNumberedNow(self, changeid, t=None):
        return self.parent.db.getChangeNumberedNow(changeid, t)
    def getChangeByNumber(self, changeid):
        return self.parent.db.getChangeByNumber(changeid)
    def getChangesGreaterThan(self, last_changeid, t=None):
        return self.parent.db.getChangesGreaterThan(last_changeid, t)
    def getChangesByNumber(self, changeids):
        return self.parent.db.getChangesByNumber(changeids)
    def getLatestChangeNumberNow(self, branch=None, t=None):
        return self.parent.db.getLatestChangeNumberNow(branch=branch, t=t)
