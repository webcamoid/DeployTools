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
import tempfile

from . import DTUtils


def makeself():
    return DTUtils.whereBin('makeself')

def makeselfVersion():
    process = subprocess.Popen([makeself(), '--version'], # nosec
                               stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    versionArr = stdout.strip().decode(sys.getdefaultencoding()).split()

    return versionArr[2] if len(versionArr) >= 3 else '0.0.0'

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    label,
                    licenseFile,
                    targetDir,
                    installScript,
                    installScriptArgs,
                    uninstallScript,
                    verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        DTUtils.copy(dataDir, tmpdir)
        startupScript = ''
        params = [makeself(),
                  '--xz',
                  '--target', targetDir]

        if installScript != '' and os.path.exists(installScript):
            DTUtils.copy(installScript, tmpdir)
            scriptPath = os.path.basename(installScript)
            startupScript = './' + scriptPath

        if uninstallScript != '' and os.path.exists(uninstallScript):
            DTUtils.copy(uninstallScript, tmpdir)

            mkselfVersion = makeselfVersion()

            if DTUtils.versionCode(mkselfVersion) >= DTUtils.versionCode('2.4.2'):
                params += ['--cleanup', './{}'.format(os.path.basename(uninstallScript))]

        if licenseFile != '':
            licenseOutFile = os.path.join(tmpdir, os.path.basename(licenseFile))
            charReplacement = {'"': '\\"',
                               '`': '\\`'}

            with open(licenseFile) as ifile:
                with open(licenseOutFile, 'w') as ofile:
                    for line in ifile:
                        for c in charReplacement:
                            line = line.replace(c, charReplacement[c])

                        ofile.write(line)

            params += ['--license', licenseOutFile]

        params += [tmpdir,
                   outPackage,
                   label,
                   startupScript]

        if installScriptArgs != '':
            params += installScriptArgs.split()

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
    installScriptArgs = configs.get('Makeself', 'installScriptArgs', fallback='').strip()

    if installScript != '':
        installScript = os.path.join(sourcesDir, installScript)

    uninstallScript = configs.get('Makeself', 'uninstallScript', fallback='').strip()

    if uninstallScript != '':
        uninstallScript = os.path.join(sourcesDir, uninstallScript)

    verbose = configs.get('Makeself', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('Makeself', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
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
                    installScriptArgs,
                    uninstallScript,
                    verbose)
