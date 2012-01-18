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

import logging
import sys
import traceback
from buildbot.changes.changes import Change
from twisted.python import log

try:
    import json
    assert json
except ImportError:
    import simplejson as json

def getChanges(request, options=None):
        """
        Reponds only to POST events and starts the build process

        :arguments:
            request
                the http request object
        """
        try:
            payload = json.loads(request.args['payload'][0])
            changes = process_change(payload)
            return changes
        except Exception:
            logging.error("Encountered an exception:")
            for msg in traceback.format_exception(*sys.exc_info()):
                logging.error(msg.strip())

def process_change(payload):
        """
        Consumes the JSON as a python object and actually starts the build.

        :arguments:
            payload
                Python Object that represents the JSON sent by GitHub Service
                Hook.
        """
        changes = []
        project = payload['project']
        revision = payload['revision']
        author = payload.get('author', 'None')
        log.msg( "in process_change" )
        log.msg("Received build request from %s for project %s:%s" %
                (author, project, revision))
        log.msg("New revision: %s" % 'revision'[:8])
        changes.append(Change(author, [], "", revision=revision, project=project))
        return changes
