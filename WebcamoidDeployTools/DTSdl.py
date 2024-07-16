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

import os

from . import DTBinary
from . import DTUtils


def dependsOnSDL(configs,
                 targetPlatform,
                 targetArch,
                 debug,
                 dataDir,
                 sysLibDir):
    solver = DTBinary.BinaryTools(configs,
                                  DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
                                  sysLibDir)

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if libName == 'SDL2':
            return True

    return False

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    defaultClassesFile = '/opt/android-libs/{}/share/java/sdl2.jar'.format(targetArch)
    classesFile = configs.get('SDL', 'classesFile', fallback=defaultClassesFile).strip()

    sysLibDir = configs.get('System', 'libDir', fallback='')
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    haveSDL = configs.get('SDL', 'haveSDL', fallback='false').strip()
    haveSDL = DTUtils.toBool(haveSDL)

    if not haveSDL:
        haveSDL = dependsOnSDL(configs,
                               targetPlatform,
                               targetArch,
                               debug,
                               dataDir,
                               sysLibDir)

    if targetPlatform == 'android':
        print('Copying SDL classes file')
        print()

        if haveSDL:
            if len(classesFile) < 1:
                print('Classes file not set')
            elif os.path.exists(classesFile):
                outJarsDir = os.path.join(dataDir, 'libs')
                print('    {} -> {}'.format(classesFile, outJarsDir))
                DTUtils.copy(classesFile, outJarsDir)
                globs['dependencies'].add(classesFile)
            else:
                print('Classes file not found: {}'.format(classesFile))

def postRun(globs, configs, dataDir):
    pass
