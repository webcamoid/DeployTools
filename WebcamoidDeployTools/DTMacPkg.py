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


def pkgbuild():
    return DTUtils.whereBin('pkgbuild')

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    version,
                    targetDir,
                    subFolder,
                    identifier,
                    installScripts,
                    uninstallScript,
                    verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        installDestDir = tmpdir

        if subFolder != '':
            installDestDir = os.path.join(tmpdir, subFolder)

        DTUtils.copy(dataDir, installDestDir)

        if uninstallScript != '':
            DTUtils.copy(uninstallScript, installDestDir)
            os.chmod(os.path.join(installDestDir,
                                  os.path.basename(uninstallScript)),
                     0o755)

        params = [pkgbuild(),
                  '--identifier', identifier,
                  '--version', version,
                  '--install-location', targetDir]

        if installScripts != '':
            params += ['--scripts', installScripts]

        params += ['--root', tmpdir,
                   outPackage]
        process = None

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
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
    return ['mac']

def isAvailable(configs):
    return pkgbuild() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('MacPkg', 'name', fallback=name).strip()
    appName = configs.get('MacPkg', 'appName', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('MacPkg', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    defaultTargetDir = '/Applications'
    targetDir = configs.get('MacPkg', 'targetDir', fallback=defaultTargetDir).strip()
    subFolder = configs.get('MacPkg', 'subFolder', fallback='').strip()
    defaultIdentifier = 'com.{}.{}'.format(name, appName)
    identifier = configs.get('MacPkg', 'identifier', fallback=defaultIdentifier).strip()
    installScripts = configs.get('MacPkg', 'installScripts', fallback='').strip()

    if installScripts != '':
        installScripts = os.path.join(sourcesDir, installScripts)

    uninstallScript = configs.get('MacPkg', 'uninstallScript', fallback='').strip()

    if uninstallScript != '':
        uninstallScript = os.path.join(sourcesDir, uninstallScript)

    verbose = configs.get('MacPkg', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    defaultHideArch = DTUtils.toBool(defaultHideArch)
    defaultHideArch = 'true' if defaultHideArch else 'false'
    hideArch = configs.get('MacPkg', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    defaultShowTargetPlatform = DTUtils.toBool(defaultShowTargetPlatform)
    defaultShowTargetPlatform = 'true' if defaultShowTargetPlatform else 'false'
    showTargetPlatform = configs.get('MacPkg', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.pkg'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    version,
                    targetDir,
                    subFolder,
                    identifier,
                    installScripts,
                    uninstallScript,
                    verbose)
