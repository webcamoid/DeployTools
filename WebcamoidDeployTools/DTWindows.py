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
from . import DTGit
from . import DTSystemPackages
from . import DTUtils


def sysInfo():
    info = ''

    if DTUtils.hostPlatform() == 'posix':
        for f in os.listdir('/etc'):
            if f.endswith('-release'):
                with open(os.path.join('/etc' , f)) as releaseFile:
                    info += releaseFile.read()

    return info

def writeBuildInfo(globs, buildInfoFile, sourcesDir):
    outputDir = os.path.dirname(buildInfoFile)

    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

    with open(buildInfoFile, 'w') as f:
        # Write repository info.

        commitHash = DTGit.commitHash(sourcesDir)

        if len(commitHash) < 1:
            commitHash = 'Unknown'

        print('    Commit hash: ' + commitHash)
        f.write('Commit hash: ' + commitHash + '\n')

        buildLogUrl = ''

        if 'TRAVIS_BUILD_WEB_URL' in os.environ:
            buildLogUrl = os.environ['TRAVIS_BUILD_WEB_URL']
        elif 'APPVEYOR_ACCOUNT_NAME' in os.environ and 'APPVEYOR_PROJECT_NAME' in os.environ and 'APPVEYOR_JOB_ID' in os.environ:
            buildLogUrl = 'https://ci.appveyor.com/project/{}/{}/build/job/{}'.format(os.environ['APPVEYOR_ACCOUNT_NAME'],
                                                                                        os.environ['APPVEYOR_PROJECT_SLUG'],
                                                                                        os.environ['APPVEYOR_JOB_ID'])

        if len(buildLogUrl) > 0:
            print('    Build log URL: ' + buildLogUrl)
            f.write('Build log URL: ' + buildLogUrl + '\n')

        print()
        f.write('\n')

        if DTUtils.hostPlatform() == 'posix':
            # Write host info.

            info = sysInfo()

            for line in info.split('\n'):
                if len(line) > 0:
                    print('    ' + line)
                    f.write(line + '\n')

            print()
            f.write('\n')

            # Write Wine version and emulated system info.

            wineVersion = ''

            try:
                process = subprocess.Popen(['wine', '--version'], # nosec
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                stdout, _ = process.communicate()
                wineVersion = stdout.decode(sys.getdefaultencoding()).strip()
            except:
                pass

            if len(wineVersion) < 1:
                wineVersion = 'Unknown'

            print('    Wine Version: {}'.format(wineVersion))
            f.write('Wine Version: {}\n'.format(wineVersion))

            fakeWindowsVersion = ''

            try:
                process = subprocess.Popen(['wine', 'cmd', '/c', 'ver'], # nosec
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                stdout, _ = process.communicate()
                fakeWindowsVersion = stdout.decode(sys.getdefaultencoding()).strip()
            except:
                pass

            if len(fakeWindowsVersion) < 1:
                fakeWindowsVersion = 'Unknown'

            print('    Windows Version: {}'.format(fakeWindowsVersion))
            f.write('Windows Version: {}\n'.format(fakeWindowsVersion))
            print()
            f.write('\n')

        # Write binary dependencies info.

        packages = set()

        if 'dependencies' in globs:
            for dep in globs['dependencies']:
                packageInfo = DTSystemPackages.searchPackageFor(dep)

                if len(packageInfo) > 0:
                    packages.add(packageInfo)

        packages = sorted(packages)

        for packge in packages:
            print('    ' + packge)
            f.write(packge + '\n')

def removeUnneededFiles(path):
    afiles = set()

    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith('.a') \
                or f.endswith('.static.prl') \
                or f.endswith('.pdb') \
                or f.endswith('.lib'):
                afiles.add(os.path.join(root, f))

    for afile in afiles:
        os.remove(afile)

def createLauncher(globs, mainExecutable, programArgs, dataDir):
    programName = os.path.basename(mainExecutable)
    launcherScript = os.path.join(dataDir, programName) + '.bat'
    binDir = os.path.relpath(os.path.dirname(mainExecutable), dataDir)

    with open(launcherScript, 'w') as launcher:
        launcher.write('@echo off\n')

        if 'environment' in globs:
            for env in globs['environment']:
                if len(env[2]) > 0:
                    launcher.write('rem {}\n'.format(env[2]))

                if env[3]:
                    launcher.write('rem ')

                launcher.write('set {}={}\n'.format(env[0], env[1]))

        launcher.write('start /b "" "%~dp0{}\\{}"'.format(binDir, programName))

        if len(programArgs) > 0:
            launcher.write(' ' + programArgs)

        launcher.write('\n')

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    sysLibDir = configs.get('System', 'libDir', fallback='')
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()
    libs = set()

    if sysLibDir != '':
        for lib in sysLibDir.split(','):
            libs.add(lib.strip())

    sysLibDir = list(libs)
    extraLibs = configs.get('System', 'extraLibs', fallback='')
    elibs = set()

    if extraLibs != '':
        for lib in extraLibs.split(','):
            elibs.add(lib.strip())

    extraLibs = list(elibs)
    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  sysLibDir,
                                  stripCmd)

    print('Copying required libs')
    print()
    DTUtils.solvedepsLibs(globs,
                          mainExecutable,
                          targetPlatform,
                          targetArch,
                          dataDir,
                          libDir,
                          sysLibDir,
                          extraLibs,
                          stripCmd)
    print()
    print('Stripping symbols')
    solver.stripSymbols(dataDir)
    print('Removing unnecessary files')
    removeUnneededFiles(dataDir)

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()

    if mainExecutable != '':
        mainExecutable = os.path.join(dataDir, mainExecutable)

    programArgs = configs.get('Package', 'programArgs', fallback='').strip()
    buildInfoFile = configs.get('Package', 'buildInfoFile', fallback='build-info.txt').strip()
    buildInfoFile = os.path.join(dataDir, buildInfoFile)

    if mainExecutable != '':
        print('Writting launcher file')
        createLauncher(globs, mainExecutable, programArgs, dataDir)

    print('Writting build system information')
    print()
    writeBuildInfo(globs, buildInfoFile, sourcesDir)
