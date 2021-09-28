#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2020  Gonzalo Exequiel Pedone
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

from . import DTBinary
from . import DTUtils


def copyVlcPlugins(globs,
                   targetPlatform,
                   targetArch,
                   dataDir,
                   outputVlcPluginsDir,
                   vlcPluginsDir,
                   sysLibDir,
                   stripCmd='strip'):
    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  sysLibDir,
                                  stripCmd)

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == 'vlc':
            for root, _, files in os.walk(vlcPluginsDir):
                for f in files:
                    sysPluginPath = os.path.join(root, f)
                    pluginPath = os.path.join(outputVlcPluginsDir,
                                              os.path.relpath(root,
                                                              vlcPluginsDir),
                                              f)

                    if not os.path.exists(sysPluginPath):
                        continue

                    print('    {} -> {}'.format(sysPluginPath, pluginPath))
                    DTUtils.copy(sysPluginPath, pluginPath)
                    globs['dependencies'].add(sysPluginPath)

            break

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    outputVlcPluginsDir = configs.get('Vlc', 'outputPluginsDir', fallback='plugins').strip()
    outputVlcPluginsDir = os.path.join(dataDir, outputVlcPluginsDir)
    defaultVlcPluginsDir = os.environ['VLC_PLUGIN_PATH'] if 'VLC_PLUGIN_PATH' in os.environ else ''
    vlcPluginsDir = configs.get('Vlc', 'pluginsDir', fallback=defaultVlcPluginsDir).strip()
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetPlatform)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        libs.add(lib.strip())

    sysLibDir = list(libs)
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()

    print('VLC information')
    print()
    print('VLC plugins directory: {}'.format(vlcPluginsDir))
    print('VLC plugins output directory: {}'.format(outputVlcPluginsDir))
    print()
    print('Copying required VLC plugins')
    print()
    copyVlcPlugins(globs,
                   targetPlatform,
                   targetArch,
                   dataDir,
                   outputVlcPluginsDir,
                   vlcPluginsDir,
                   sysLibDir,
                   stripCmd)
    print()

def postRun(globs, configs, dataDir):
    pass
