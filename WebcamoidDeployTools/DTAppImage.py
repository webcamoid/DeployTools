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

import configparser
import os
import subprocess
import tempfile

from . import DTUtils


def appimagetool(targetArch):
    appimage = DTUtils.whereBin('appimagetool')

    if len(appimage) > 0:
        return appimage

    appImageArchs = {'x64': 'x86_64',
                     'x86': 'i686',
                     'arm64': 'aarch64',
                     'arm32': 'armhf'}

    if not targetArch in appImageArchs:
        return ''

    return DTUtils.whereBin('appimagetool-{}.AppImage'.format(appImageArchs[targetArch]))

def createAppImage(globs,
                   mutex,
                   targetArch,
                   dataDir,
                   outPackage,
                   launcher,
                   desktopFile,
                   desktopIcon,
                   dirIcon,
                   verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        appDirName = os.path.splitext(os.path.basename(outPackage))[0]
        appDir = \
            os.path.join(tmpdir,
                         '{}.AppDir'.format(appDirName))

        if not os.path.exists(appDir):
            os.makedirs(appDir)

        DTUtils.copy(dataDir, appDir)
        launcherSrc = os.path.join(appDir, os.path.relpath(launcher, dataDir))
        launcherDst = os.path.join(appDir, 'AppRun')
        DTUtils.move(launcherSrc, launcherDst)
        DTUtils.copy(desktopFile, appDir)
        desktopFile = os.path.join(appDir, os.path.basename(desktopFile))
        config = configparser.ConfigParser()
        config.optionxform=str
        config.read(desktopFile, 'utf-8')
        config['Desktop Entry']['Exec'] = 'AppRun'
        del config['Desktop Entry']['Keywords']

        with open(desktopFile, 'w', encoding='utf-8') as configFile:
            config.write(configFile, space_around_delimiters=False)

        DTUtils.copy(desktopIcon, appDir)
        DTUtils.copy(dirIcon, os.path.join(appDir, '.DirIcon'))
        params = [appimagetool(targetArch),
                  '-v',
                  '--no-appstream',
                  '--comp', 'xz',
                  appDir,
                  outPackage]
        penv = os.environ.copy()
        penv['ARCH'] = targetArch

        if verbose:
            process = subprocess.Popen(params, # nosec
                                       env=penv)
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       env=penv)

        process.communicate()

        if not os.path.exists(outPackage):
            return

        mutex.acquire()

        if not 'outputPackages' in globs:
            globs['outputPackages'] = []

        globs['outputPackages'].append(outPackage)
        mutex.release()

def platforms():
    return ['posix']

def isAvailable(configs):
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()

    return appimagetool(targetArch) != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('AppImage', 'name', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('AppImage', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    launcher = configs.get('AppImage', 'launcher', fallback='AppRun').strip()
    launcher = os.path.join(dataDir, launcher)
    desktopFile = configs.get('AppImage', 'desktopFile', fallback='app.desktop').strip()
    desktopFile = os.path.join(sourcesDir, desktopFile)
    desktopIcon = configs.get('AppImage', 'desktopIcon', fallback='app.png').strip()
    desktopIcon = os.path.join(sourcesDir, desktopIcon)
    dirIcon = configs.get('AppImage', 'dirIcon', fallback='app.png').strip()
    dirIcon = os.path.join(sourcesDir, dirIcon)
    verbose = configs.get('AppImage', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('AppImage', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    showTargetPlatform = configs.get('AppImage', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.AppImage'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createAppImage(globs,
                   mutex,
                   targetArch,
                   dataDir,
                   outPackage,
                   launcher,
                   desktopFile,
                   desktopIcon,
                   dirIcon,
                   verbose)
