#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2021  Gonzalo Exequiel Pedone
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Web-Site: http://github.com/webcamoid/DeployTools/

import os
import subprocess
import sys

from . import DTUtils
from . import DTBinary


def qmakeQuery(var=''):
    try:
        args = ['qmake', '-query']

        if var != '':
            args += [var]

        process = subprocess.Popen(args, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        return stdout.strip().decode(sys.getdefaultencoding())
    except:
        pass

    return ''

def preRun(globs, configs, dataDir):
    defaultOutputQtPluginsDir = configs.get('Qt5', 'outputQtPluginsDir', fallback='plugins').strip()
    defaultOutputQtPluginsDir = os.path.join(dataDir, defaultOutputQtPluginsDir)
    outputQtPluginsDir = configs.get('Qt5KF5', 'outputQtPluginsDir', fallback=defaultOutputQtPluginsDir).strip()
    outputQtPluginsDir = os.path.join(dataDir, outputQtPluginsDir)
    defaultQtPluginsDir = qmakeQuery('QT_INSTALL_PLUGINS')
    qtPluginsDir = configs.get('Qt5KF5', 'qtPluginsDir', fallback=defaultQtPluginsDir).strip()
    kf5Plugins = ''

    if qtPluginsDir != '':
        kf5Plugins = os.path.join(qtPluginsDir,'kf5')

    outKF5Plugins = os.path.join(outputQtPluginsDir,'kf5')

    print('Qt information')
    print()
    print('Qt5 KF5 plugins directory: {}'.format(kf5Plugins))
    print('Qt5 KF5 plugins output directory: {}'.format(outKF5Plugins))
    print()

    if os.path.exists(kf5Plugins):
        print('Copying Qt5 KF5 plugins')
        print()
        DTUtils.copy(kf5Plugins, outKF5Plugins)

        if not 'environment' in globs:
            globs['environment'] = set()

        globs['environment'].add(('QT_PLUGIN_PATH',
                                  '"${ROOTDIR}/' + os.path.relpath(outputQtPluginsDir, dataDir) + '"',
                                  'Set Qt plugins search path',
                                  False))
    else:
        print('KF5 plugins not found')

def postRun(globs, configs, dataDir):
    pass
