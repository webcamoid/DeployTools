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

def dependsOnVLC(targetPlatform,
                 targetArch,
                 debug,
                 dataDir,
                 sysLibDir):
    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
                                  sysLibDir)
    vlcLibName = ''

    if targetPlatform == 'mac' or targetPlatform == 'windows':
        vlcLibName = 'libvlc'
    else:
        vlcLibName = 'vlc'

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == vlcLibName:
            return True

    return False

def vlcCacheGen(targetPlatform):
    cacheGen = DTUtils.whereBin('vlc-cache-gen')

    if cacheGen != '':
        return cacheGen

    pkgLibDir = pkgconfVariable('vlc-plugin', 'pkglibdir')

    if pkgLibDir == '':
        return ''

    cacheGen = os.path.join(pkgLibDir, 'vlc-cache-gen')

    if targetPlatform == 'windows':
        cacheGen += '.exe'

    if not os.path.exists(cacheGen):
        return ''

    return cacheGen

def copyVlcPlugins(globs,
                   targetPlatform,
                   targetArch,
                   debug,
                   dataDir,
                   haveVLC,
                   outputVlcPluginsDir,
                   vlcPlugins,
                   vlcPluginsDir,
                   sysLibDir):
    if not haveVLC:
        haveVLC = dependsOnVLC(targetPlatform,
                               targetArch,
                               debug,
                               dataDir,
                               sysLibDir)

    if haveVLC:
        for root, _, files in os.walk(vlcPluginsDir):
            relpath = os.path.relpath(root, vlcPluginsDir)

            if relpath != '.' \
                and vlcPlugins != [] \
                and not (relpath in vlcPlugins):
                continue

            for f in files:
                sysPluginPath = os.path.join(root, f)

                if relpath == '.':
                    pluginPath = os.path.join(outputVlcPluginsDir, f)
                else:
                    pluginPath = os.path.join(outputVlcPluginsDir,
                                                relpath,
                                                f)

                if not os.path.exists(sysPluginPath):
                    continue

                print('    {} -> {}'.format(sysPluginPath, pluginPath))
                DTUtils.copy(sysPluginPath, pluginPath)
                globs['dependencies'].add(sysPluginPath)

def regenerateCache(targetPlatform, outputVlcPluginsDir, verbose):
    cacheGen = vlcCacheGen(targetPlatform)

    if cacheGen == '':
        return

    params = [cacheGen, outputVlcPluginsDir]
    process = None

    if verbose:
        process = subprocess.Popen(params) # nosec
    else:
        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process = subprocess.Popen(params, # nosec
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    process.communicate()

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    outputVlcPluginsDir = configs.get('Vlc', 'outputPluginsDir', fallback='plugins').strip()
    outputVlcPluginsDir = os.path.join(dataDir, outputVlcPluginsDir)
    vlcPluginsDir = configs.get('Vlc', 'pluginsDir', fallback='').strip()

    if vlcPluginsDir == '':
        if 'VLC_PLUGIN_PATH' in os.environ:
            vlcPluginsDir = os.environ['VLC_PLUGIN_PATH']

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
    vlcPlugins = configs.get('Vlc', 'plugins', fallback='')

    if vlcPlugins == '':
        vlcPlugins = []
    else:
        vlcPlugins = [plugin.strip() for plugin in vlcPlugins.split(',')]

    haveVLC = configs.get('Vlc', 'haveVLC', fallback='false').strip()
    haveVLC = DTUtils.toBool(haveVLC)
    verbose = configs.get('Vlc', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)

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
                   debug,
                   dataDir,
                   haveVLC,
                   outputVlcPluginsDir,
                   vlcPlugins,
                   vlcPluginsDir,
                   sysLibDir)
    print()
    print('Regenerating VLC plugins cache')
    print()
    regenerateCache(targetPlatform, outputVlcPluginsDir, verbose)

def postRun(globs, configs, dataDir):
    pass
