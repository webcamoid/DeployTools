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
import platform

from . import DTBinary
from . import DTGit
from . import DTSystemPackages
from . import DTUtils


def sysInfo():
    info = ''

    for f in os.listdir('/etc'):
        if f.endswith('-release'):
            with open(os.path.join('/etc' , f)) as releaseFile:
                info += releaseFile.read()

    if len(info) < 1:
        info = ' '.join(platform.uname())

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
        elif 'APPVEYOR_ACCOUNT_NAME' in os.environ \
            and 'APPVEYOR_PROJECT_NAME' in os.environ \
            and 'APPVEYOR_JOB_ID' in os.environ:
            buildLogUrl = 'https://ci.appveyor.com/project/{}/{}/build/job/{}'.format(os.environ['APPVEYOR_ACCOUNT_NAME'],
                                                                                      os.environ['APPVEYOR_PROJECT_SLUG'],
                                                                                      os.environ['APPVEYOR_JOB_ID'])
        elif 'GITHUB_SERVER_URL' in os.environ \
            and 'GITHUB_REPOSITORY' in os.environ \
            and 'GITHUB_RUN_ID' in os.environ:
            buildLogUrl = '{}/{}/actions/runs/{}'.format(os.environ['GITHUB_SERVER_URL'],
                                                         os.environ['GITHUB_REPOSITORY'],
                                                         os.environ['GITHUB_RUN_ID'])

        if len(buildLogUrl) > 0:
            print('    Build log URL: ' + buildLogUrl)
            f.write('Build log URL: ' + buildLogUrl + '\n')

        print()
        f.write('\n')

        # Write host info.

        info = sysInfo()

        for line in info.split('\n'):
            if len(line) > 0:
                print('    ' + line)
                f.write(line + '\n')

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

def createLauncher(globs, mainExecutable, dataDir, libDir):
    programName = os.path.basename(mainExecutable)
    launcherScript = os.path.join(dataDir, programName) + '.sh'
    binDir = os.path.relpath(os.path.dirname(mainExecutable), dataDir)
    libDir = os.path.relpath(libDir, dataDir)

    with open(launcherScript, 'w') as launcher:
        launcher.write('#!/bin/sh\n')
        launcher.write('\n')
        launcher.write('path=$(realpath "$0")\n')
        launcher.write('ROOTDIR=$(dirname "$path")\n')
        launcher.write('export PATH="${{ROOTDIR}}/{}:$PATH"\n'.format(binDir))
        launcher.write('export LD_LIBRARY_PATH="${{ROOTDIR}}/{}:$LD_LIBRARY_PATH"\n'.format(libDir))

        if 'environment' in globs:
            for env in globs['environment']:
                if len(env[2]) > 0:
                    launcher.write('# {}\n'.format(env[2]))

                if env[3]:
                    launcher.write('#')

                launcher.write('export {}={}\n'.format(env[0], env[1]))

        launcher.write('{} "$@"\n'.format(programName))

    os.chmod(launcherScript, 0o744)

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    libDir = configs.get('Package', 'libDir', fallback='lib').strip()
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
    print('Resetting file permissions')
    solver.resetFilePermissions(dataDir)
    print()

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    writeLauncher = configs.get('Package', 'writeLauncher', fallback='true').strip()
    writeLauncher = DTUtils.toBool(writeLauncher)

    if mainExecutable != '':
        mainExecutable = os.path.join(dataDir, mainExecutable)

    libDir = configs.get('Package', 'libDir', fallback='lib').strip()
    libDir = os.path.join(dataDir, libDir)
    buildInfoFile = configs.get('Package', 'buildInfoFile', fallback='build-info.txt').strip()
    buildInfoFile = os.path.join(dataDir, buildInfoFile)

    if writeLauncher and mainExecutable != '':
        print('Writting launcher file')
        createLauncher(globs, mainExecutable, dataDir, libDir)

    print('Writting build system information')
    print()
    writeBuildInfo(globs, buildInfoFile, sourcesDir)
