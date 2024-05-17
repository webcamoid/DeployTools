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
import platform
import shutil
import xml.etree.ElementTree as ET

from . import DTBinary
from . import DTGit
from . import DTSystemPackages
from . import DTUtils


def buildToolsVersions():
    androidSDK = ''

    if 'ANDROID_HOME' in os.environ:
        androidSDK = os.environ['ANDROID_HOME']

    buildToolsDir = os.path.join(androidSDK, 'build-tools')
    buildToolsVersions = []

    try:
        buildToolsVersions = list(os.listdir(buildToolsDir))
    except:
        pass

    sorted(buildToolsVersions, key=lambda v: DTUtils.versionCode(v), reverse=True)

    return buildToolsVersions

def buildToolsVersion(configs=None):
    versions = buildToolsVersions()
    latestVersion = '' if len(versions) < 1 else versions[0]

    if configs == None:
        return latestVersion

    return configs.get('System', 'sdkBuildToolsRevision', fallback=latestVersion).strip()

def sysInfo():
    info = ''

    for f in os.listdir('/etc'):
        if f.endswith('-release'):
            with open(os.path.join('/etc' , f)) as releaseFile:
                info += releaseFile.read()

    if len(info) < 1:
        info = ' '.join(platform.uname())

    return info

def writeBuildInfo(globs,
                   buildInfoFile,
                   sourcesDir,
                   minSdkVersion,
                   targetSdkVersion):
    outputDir = os.path.dirname(buildInfoFile)

    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

    # Write repository info.

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
        elif 'GITHUB_SERVER_URL' in os.environ and os.environ['GITHUB_SERVER_URL'] != '' \
            and 'GITHUB_REPOSITORY' in os.environ and os.environ['GITHUB_REPOSITORY'] != '' \
            and 'GITHUB_RUN_ID' in os.environ and os.environ['GITHUB_RUN_ID'] != '':
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

        # Write SDK and NDK info.

        androidSDK = ''

        if 'ANDROID_HOME' in os.environ:
            androidSDK = os.environ['ANDROID_HOME']

        androidNDK = ''

        if 'ANDROID_NDK_ROOT' in os.environ:
            androidNDK = os.environ['ANDROID_NDK_ROOT']
        elif 'ANDROID_NDK_ROOT' in os.environ:
            androidNDK = os.environ['ANDROID_NDK_ROOT']

        sdkInfoFile = os.path.join(androidSDK, 'tools', 'source.properties')
        ndkInfoFile = os.path.join(androidNDK, 'source.properties')

        print('    Android Platform: {}'.format(minSdkVersion))
        f.write('Android Platform: {}\n'.format(minSdkVersion))
        print('    Minimum SDK version: {}'.format(minSdkVersion))
        f.write('Minimum SDK version: {}\n'.format(minSdkVersion))
        print('    Target SDK version: {}'.format(targetSdkVersion))
        f.write('Target SDK version: {}\n'.format(targetSdkVersion))
        print('    SDK Info: \n')
        f.write('SDK Info: \n\n')

        with open(sdkInfoFile) as sdkf:
            for line in sdkf:
                if len(line) > 0:
                    print('        ' + line.strip())
                    f.write('    ' + line)

        print('\n    NDK Info: \n')
        f.write('\nNDK Info: \n\n')

        with open(ndkInfoFile) as ndkf:
            for line in ndkf:
                if len(line) > 0:
                    print('        ' + line.strip())
                    f.write('    ' + line)

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
            if f.endswith('.jar'):
                afiles.add(os.path.join(root, f))

    for afile in afiles:
        os.remove(afile)

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    buildType = configs.get('Package', 'buildType', fallback='Debug').strip()
    defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()
    libs = set()

    if sysLibDir != '':
        for lib in sysLibDir.split(','):
            lib = lib.strip()

            if len(lib) > 0:
                libs.add(lib.strip())

    sysLibDir = list(libs)
    extraLibs = configs.get('System', 'extraLibs', fallback='')
    elibs = set()

    if extraLibs != '':
        for lib in extraLibs.split(','):
            lib = lib.strip()

            if len(lib) > 0:
                elibs.add(lib.strip())

    extraLibs = list(elibs)
    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
                                  sysLibDir,
                                  stripCmd)

    print('Copying required libs')
    print()
    DTUtils.solvedepsLibs(globs,
                          mainExecutable,
                          targetPlatform,
                          targetArch,
                          debug,
                          dataDir,
                          libDir,
                          sysLibDir,
                          extraLibs,
                          stripCmd)
    print()

    if buildType == 'Release' or buildType == 'MinSizeRel':
        print('Stripping symbols')
        solver.stripSymbols(dataDir)

    print('Removing old build files')

    try:
        shutil.rmtree(os.path.join(dataDir, '.gradle'), True)
    except:
        pass

    try:
        shutil.rmtree(os.path.join(dataDir, 'build'), True)
    except:
        pass

    print('Removing unnecessary files')
    removeUnneededFiles(libDir)
    print()

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    buildInfoFile = configs.get('Package', 'buildInfoFile', fallback='build-info.txt').strip()
    buildInfoFile = os.path.join(dataDir, buildInfoFile)
    minSdkVersion = configs.get('Android', 'minSdkVersion', fallback='24').strip()
    targetSdkVersion = configs.get('Android', 'targetSdkVersion', fallback='24').strip()

    print('Writting build system information')
    print()
    writeBuildInfo(globs,
                   buildInfoFile,
                   sourcesDir,
                   minSdkVersion,
                   targetSdkVersion)
