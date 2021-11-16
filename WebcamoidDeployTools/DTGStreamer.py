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

from . import DTBinary
from . import DTUtils


def copyGStreamerPlugins(globs,
                         targetPlatform,
                         targetArch,
                         dataDir,
                         outputGstPluginsDir,
                         gstPlugins,
                         gstPluginsDir,
                         sysLibDir,
                         stripCmd='strip'):
    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  sysLibDir,
                                  stripCmd)
    gstLibName = ''

    if targetPlatform == 'mac' or targetPlatform == 'windows':
        gstLibName = 'libgstreamer-1.0'
    else:
        gstLibName = 'gstreamer-1.0'

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == gstLibName:
            for root, _, files in os.walk(gstPluginsDir):
                relpath = os.path.relpath(root, gstPluginsDir)

                if relpath != '.' \
                    and gstPlugins != [] \
                    and not (relpath in gstPlugins):
                    continue

                for f in files:
                    sysPluginPath = os.path.join(root, f)

                    if relpath == '.':
                        pluginPath = os.path.join(outputGstPluginsDir, f)
                    else:
                        pluginPath = os.path.join(outputGstPluginsDir,
                                                  relpath,
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
    outputGstPluginsDir = configs.get('GStreamer', 'outputPluginsDir', fallback='plugins').strip()
    outputGstPluginsDir = os.path.join(dataDir, outputGstPluginsDir)
    defaultGstPluginsDir = os.environ['GST_PLUGIN_PATH'] if 'GST_PLUGIN_PATH' in os.environ else ''
    gstPluginsDir = configs.get('GStreamer', 'pluginsDir', fallback=defaultGstPluginsDir).strip()
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        libs.add(lib.strip())

    sysLibDir = list(libs)
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()
    gstPlugins = configs.get('GStreamer', 'plugins', fallback='')

    if gstPlugins == '':
        gstPlugins = []
    else:
        gstPlugins = [plugin.strip() for plugin in gstPlugins.split(',')]

    verbose = configs.get('GStreamer', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)

    print('GStreamer information')
    print()
    print('GStreamer plugins directory: {}'.format(gstPluginsDir))
    print('GStreamer plugins output directory: {}'.format(outputGstPluginsDir))
    print()
    print('Copying required GStreamer plugins')
    print()
    copyGStreamerPlugins(globs,
                         targetPlatform,
                         targetArch,
                         dataDir,
                         outputGstPluginsDir,
                         gstPlugins,
                         gstPluginsDir,
                         sysLibDir,
                         stripCmd)

def postRun(globs, configs, dataDir):
    pass
