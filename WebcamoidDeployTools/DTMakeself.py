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
import tempfile

from . import DTUtils


def makeself():
    return DTUtils.whereBin('makeself')

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    label,
                    licenseFile,
                    targetDir,
                    installScript,
                    uninstallScript):
    with tempfile.TemporaryDirectory() as tmpdir:
        licenseOutFile = os.path.basename(licenseFile)
        DTUtils.copy(dataDir, tmpdir)
        startupScript = ''
        params = [makeself(),
                  '--xz',
                  '--target', targetDir]

        if installScript != '' and os.path.exists(installScript):
            DTUtils.copy(installScript, tmpdir)
            scriptPath = os.path.basename(installScript)
            startupScript = './{}; rm -f {}'.format(scriptPath, scriptPath)

        if uninstallScript != '' and os.path.exists(uninstallScript):
            DTUtils.copy(uninstallScript, tmpdir)
            params += ['--cleanup', './{}'.format(os.path.basename(uninstallScript))]

        params += ['--license', licenseFile,
                   tmpdir,
                   outPackage,
                   label,
                   startupScript]
        process = subprocess.Popen(params, #nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process.communicate()

        if not os.path.exists(outPackage):
            return

        mutex.acquire()

        if not 'outputPackages' in globs:
            globs['outputPackages'] = []

        globs['outputPackages'].append(outPackage)
        mutex.release()

def platforms():
    return ['mac', 'posix']

def isAvailable(configs):
    return makeself() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('Makeself', 'name', fallback=name).strip()
    appName = configs.get('Makeself', 'appName', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('Makeself', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    label = configs.get('Makeself', 'label', fallback=appName).strip()
    licenseFile = configs.get('Makeself', 'license', fallback='COPYING').strip()
    licenseFile = os.path.join(sourcesDir, licenseFile)
    defaultTargetDir = '/opt/{}'.format(appName)
    targetDir = configs.get('Makeself', 'targetDir', fallback=defaultTargetDir).strip()
    installScript = configs.get('Makeself', 'installScript', fallback='').strip()

    if installScript != '':
        installScript = os.path.join(sourcesDir, installScript)

    uninstallScript = configs.get('Makeself', 'uninstallScript', fallback='').strip()

    if uninstallScript != '':
        uninstallScript = os.path.join(sourcesDir, uninstallScript)

    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    defaultHideArch = DTUtils.toBool(defaultHideArch)
    defaultHideArch = 'true' if defaultHideArch else 'false'
    hideArch = configs.get('Makeself', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    defaultShowTargetPlatform = DTUtils.toBool(defaultShowTargetPlatform)
    defaultShowTargetPlatform = 'true' if defaultShowTargetPlatform else 'false'
    showTargetPlatform = configs.get('Makeself', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.run'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    label,
                    licenseFile,
                    targetDir,
                    installScript,
                    uninstallScript)
