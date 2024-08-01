#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2024  Gonzalo Exequiel Pedone
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

import glob
import os
import subprocess

from . import DTBinary
from . import DTUtils


def patchelf():
    return DTUtils.whereBin('patchelf')

def dependsOnOpenSSL(solver, dataDir):
    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == 'crypto' or libName == 'ssl':
            return True

    return False

def renameLibraries(solver, mainExecutable, packageLibDir, androidOpensslSuffix, verbose):
    patchelfCmd = patchelf()
    sslLibs = ['libcrypto.so', 'libssl.so']

    for lib in sslLibs:
        libPath = solver.guess(mainExecutable, lib)

        if len(patchelfCmd) < 1:
            continue

        bn, ext = os.path.splitext(lib)
        dstbn = '{}{}{}'.format(bn, androidOpensslSuffix, ext)
        dst = os.path.join(packageLibDir, dstbn)

        print('    {} -> {}'.format(libPath, dst))
        DTUtils.copy(libPath, dst)

        if len(patchelfCmd) > 0:
            params = [patchelfCmd,
                      '--set-soname', dstbn,
                      dst]

            if verbose:
                process = subprocess.Popen(params) # nosec
            else:
                process = subprocess.Popen(params, # nosec
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

            process.communicate()

        solver.strip(dst)

def fixDependencies(solver, packageLibDir, androidOpensslSuffix, verbose):
    patchelfCmd = patchelf()

    if len(patchelfCmd) < 1:
        return

    sslLibs = ['crypto', 'ssl']

    for lib in glob.glob('*.so', root_dir=packageLibDir):
        libPath = os.path.join(packageLibDir, lib)

        for dep in solver.dependencies(libPath):
            for sslDep in sslLibs:
                fullSslDep = 'lib{}.so'.format(sslDep)

                if os.path.basename(dep) == fullSslDep:
                    print('    Patching {}'.format(libPath))
                    params = [patchelfCmd,
                              '--replace-needed', fullSslDep, 'lib{}{}.so'.format(sslDep, androidOpensslSuffix),
                              libPath]

                    if verbose:
                        process = subprocess.Popen(params) # nosec
                    else:
                        process = subprocess.Popen(params, # nosec
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)

                    process.communicate()

def preRun(globs, configs, dataDir):
    pass

def postRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    packageLibDir = configs.get('Package', 'libDir', fallback='').strip()
    packageLibDir = os.path.join(dataDir, packageLibDir)
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    androidOpensslSuffix = configs.get('OpenSSL', 'androidOpensslSuffix', fallback='').strip()
    verbose = configs.get('OpenSSL', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    sysLibDir = configs.get('System', 'libDir', fallback='')
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    haveOpenSSL = configs.get('OpenSSL', 'haveOpenSSL', fallback='false').strip()
    haveOpenSSL = DTUtils.toBool(haveOpenSSL)

    solver = DTBinary.BinaryTools(configs,
                                DTUtils.hostPlatform(),
                                targetPlatform,
                                targetArch,
                                debug,
                                sysLibDir)

    if not haveOpenSSL:
        haveOpenSSL = dependsOnOpenSSL(solver, dataDir)

    if targetPlatform == 'android':
        if haveOpenSSL:
            print('Fix OpenSSL libraries')
            print()
            print('Suffix: {}'.format(androidOpensslSuffix))
            print()

            if len(androidOpensslSuffix) > 0:
                print('Copying OpenSSL libraries with suffix')
                print()
                renameLibraries(solver,
                                mainExecutable,
                                packageLibDir,
                                androidOpensslSuffix,
                                verbose)
                print()
                print('Fixing OpenSSL dependencies')
                print()
                fixDependencies(solver,
                                packageLibDir,
                                androidOpensslSuffix,
                                verbose)
                print()
