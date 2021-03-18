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
import threading
import time

from . import DTBinary
from . import DTGit
from . import DTSystemPackages
from . import DTUtils


def removeUnneededFiles(path):
    adirs = set()
    afiles = set()

    for root, dirs, files in os.walk(path):
        for d in dirs:
            if d == 'Headers':
                adirs.add(os.path.join(root, d))

        for f in files:
            if f == 'Headers' or f.endswith('.prl'):
                afiles.add(os.path.join(root, f))

    for adir in adirs:
        try:
            shutil.rmtree(adir, True)
        except:
            pass

    for afile in afiles:
        try:
            if os.path.islink(afile):
                os.unlink(afile)
            else:
                os.remove(afile)
        except:
            pass

def fixLibRpath(solver, mutex, mach, mainExecutable, libDir, sysLibDir):
    binDir = os.path.dirname(mainExecutable)
    rpath = os.path.join('@executable_path', os.path.relpath(libDir, binDir))
    log = '\tFixed {}\n\n'.format(mach)
    machInfo = solver.dump(mach)

    # Change rpath
    if mach.startswith(binDir):
        log += '\t\tChanging rpath to {}\n'.format(rpath)

        for oldRpath in machInfo['rpaths']:
            process = subprocess.Popen(['install_name_tool', # nosec
                                        '-delete_rpath', oldRpath, mach],
                                        stdout=subprocess.PIPE)
            process.communicate()

        process = subprocess.Popen(['install_name_tool', # nosec
                                    '-add_rpath', rpath, mach],
                                    stdout=subprocess.PIPE)
        process.communicate()

    # Change ID
    if mach.startswith(binDir):
        newMachId = machInfo['id']
    elif mach.startswith(libDir):
        newMachId = mach.replace(sysLibDir, rpath)
    else:
        newMachId = os.path.basename(mach)

    if newMachId != machInfo['id']:
        log += '\t\tChanging ID to {}\n'.format(newMachId)

        process = subprocess.Popen(['install_name_tool', # nosec
                                    '-id', newMachId, mach],
                                    stdout=subprocess.PIPE)
        process.communicate()

    # Change library links
    for dep in machInfo['imports']:
        if dep.startswith(rpath):
            continue

        if solver.isExcluded(dep):
            continue

        basename = os.path.basename(dep)
        framework = ''
        inFrameworkPath = ''

        if not basename.endswith('.dylib'):
            frameworkPath = dep[: dep.rfind('.framework')] + '.framework'
            framework = os.path.basename(frameworkPath)
            inFrameworkPath = os.path.join(framework, dep.replace(frameworkPath + '/', ''))

        newDepPath = os.path.join(rpath, basename if len(framework) < 1 else inFrameworkPath)

        if dep != newDepPath:
            log += '\t\t{} -> {}\n'.format(dep, newDepPath)

            process = subprocess.Popen(['install_name_tool', # nosec
                                        '-change', dep, newDepPath, mach],
                                        stdout=subprocess.PIPE)
            process.communicate()

    mutex.acquire()
    print(log)
    mutex.release()

def fixRpaths(solver, dataDir, mainExecutable, libDir, sysLibDir):
    mutex = threading.Lock()
    threads = []

    for mach in solver.find(dataDir):
        thread = threading.Thread(target=fixLibRpath,
                                  args=(solver,
                                        mutex,
                                        mach,
                                        mainExecutable,
                                        libDir,
                                        sysLibDir, ))
        threads.append(thread)

        while threading.active_count() >= DTUtils.numThreads():
            time.sleep(0.25)

        thread.start()

    for thread in threads:
        thread.join()

def sysInfo():
    process = subprocess.Popen(['sw_vers'], # nosec
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    stdout, _ = process.communicate()

    return stdout.decode(sys.getdefaultencoding()).strip()

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

        # Write host info.

        for line in sysInfo().split('\n'):
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

def signPackage(package):
    process = subprocess.Popen(['codesign', # nosec
                                '--force',
                                '--sign',
                                '-',
                                package],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    process.communicate()

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    sysLibDir = configs.get('System', 'libDir', fallback='/usr/local/lib')
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
    solver.resetFilePermissions(dataDir, os.path.dirname(mainExecutable))
    print('Removing unnecessary files')
    removeUnneededFiles(dataDir)
    print('Fixing rpaths\n')
    fixRpaths(solver, dataDir, mainExecutable, libDir, sysLibDir)

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    buildInfoFile = configs.get('Package', 'buildInfoFile', fallback='build-info.txt').strip()
    buildInfoFile = os.path.join(dataDir, buildInfoFile)
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    defaultAppBundle = os.path.basename(mainExecutable) + '.app'
    appBundle = configs.get('Package', 'appBundle', fallback=defaultAppBundle).strip()
    appBundle = os.path.join(dataDir, appBundle)

    print('\nWritting build system information\n')
    writeBuildInfo(globs, buildInfoFile, sourcesDir)
    print('\nSigning bundle\n')
    signPackage(appBundle)
