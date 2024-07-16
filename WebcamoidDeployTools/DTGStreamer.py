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


def pkgconf():
    pkgConfig = DTUtils.whereBin('pkg-config')

    if pkgConfig == '':
        pkgConfig = DTUtils.whereBin('pkgconf')

    return pkgConfig

def pkgconfVariable(package, var):
    pkgConfig = pkgconf()

    if pkgConfig == '':
        return ''

    process = subprocess.Popen([pkgConfig, package, '--variable={}'.format(var)], # nosec
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    stdout, _ = process.communicate()

    if process.returncode != 0:
        return ''

    return stdout.decode(sys.getdefaultencoding()).strip()

def dependsOnGStreammer(configs,
                        targetPlatform,
                        targetArch,
                        debug,
                        dataDir,
                        sysLibDir):
    solver = DTBinary.BinaryTools(configs,
                                  DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
                                  sysLibDir)
    gstLibName = ''

    if targetPlatform == 'mac':
        gstLibName = 'libgstreamer-1.0.0'
    elif targetPlatform == 'windows':
        gstLibName = 'libgstreamer-1.0-0'
    else:
        gstLibName = 'gstreamer-1.0'

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == gstLibName:
            return True

    return False

def copyGStreamerPlugins(globs,
                         outputGstPluginsDir,
                         gstPlugins,
                         gstPluginsDir):
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

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    outputGstPluginsDir = configs.get('GStreamer', 'outputPluginsDir', fallback='plugins').strip()
    outputGstPluginsDir = os.path.join(dataDir, outputGstPluginsDir)
    gstPluginsDir = configs.get('GStreamer', 'pluginsDir', fallback='').strip()

    if gstPluginsDir == '':
        if 'GST_PLUGIN_PATH' in os.environ:
            gstPluginsDir = os.environ['GST_PLUGIN_PATH']
        else:
            gstPluginsDir = pkgconfVariable('gstreamer-1.0', 'pluginsdir')

    pluginScanner = configs.get('GStreamer', 'pluginScanner', fallback='').strip()

    if pluginScanner == '':
        if 'GST_PLUGIN_SCANNER' in os.environ:
            pluginScanner = os.environ['GST_PLUGIN_SCANNER']
        else:
            pluginScannerDir = pkgconfVariable('gstreamer-1.0', 'pluginscannerdir')

            if pluginScannerDir != '' and os.path.exists(pluginScannerDir):
                for f in os.listdir(pluginScannerDir):
                    if f.startswith('gst-plugin-scanner'):
                        pluginScanner = os.path.join(pluginScannerDir, f)

                        break

    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    gstPlugins = configs.get('GStreamer', 'plugins', fallback='')

    if gstPlugins == '':
        gstPlugins = []
    else:
        gstPlugins = [plugin.strip() for plugin in gstPlugins.split(',')]

    haveGStreamer = configs.get('GStreamer', 'haveGStreamer', fallback='false').strip()
    haveGStreamer = DTUtils.toBool(haveGStreamer)
    verbose = configs.get('GStreamer', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)

    if not haveGStreamer:
        haveGStreamer = dependsOnGStreammer(configs,
                                            targetPlatform,
                                            targetArch,
                                            debug,
                                            dataDir,
                                            sysLibDir)

    print('GStreamer information')
    print()
    print('Plugins directory: {}'.format(gstPluginsDir))
    print('Plugins output directory: {}'.format(outputGstPluginsDir))
    print('Plugins scanner: {}'.format(pluginScanner))
    print()
    print('Copying required GStreamer plugins')
    print()

    if haveGStreamer:
        copyGStreamerPlugins(globs,
                             outputGstPluginsDir,
                             gstPlugins,
                             gstPluginsDir)
    print()
    print('Copying GStreamer plugins scanner')
    print()

    if haveGStreamer and pluginScanner != '':
        outPluginScanner = os.path.join(outputGstPluginsDir,
                                        os.path.basename(pluginScanner))
        print('    {} -> {}'.format(pluginScanner, outPluginScanner))
        DTUtils.copy(pluginScanner, outputGstPluginsDir)

        try:
            os.chmod(outPluginScanner, 0o755)
        except:
            pass

    print()

def postRun(globs, configs, dataDir):
    pass
