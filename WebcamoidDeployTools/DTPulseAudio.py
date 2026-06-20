#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2026  Gonzalo Exequiel Pedone
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


def dependsOnPulseAudio(configs,
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

        if libName == 'pulse':
            return True

    return False

def copyPulseAudioModules(globs,
                          outputPulseAudioModulesDir,
                          pulseAudioModules,
                          pulseAudioModulesDir):
    for root, _, files in os.walk(pulseAudioModulesDir):
        relpath = os.path.relpath(root, pulseAudioModulesDir)

        if relpath != '.' \
            and pulseAudioModules != [] \
            and not (relpath in pulseAudioModules):
            continue

        for f in files:
            sysPluginPath = os.path.join(root, f)

            if relpath == '.':
                pluginPath = os.path.join(outputPulseAudioModulesDir, f)
            else:
                pluginPath = os.path.join(outputPulseAudioModulesDir,
                                          relpath,
                                          f)

            if not os.path.exists(sysPluginPath):
                continue

            print('    {} -> {}'.format(sysPluginPath, pluginPath))
            DTUtils.copy(sysPluginPath, pluginPath)
            globs['dependencies'].add(sysPluginPath)

def preRun(globs, configs, dataDir):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    outputPulseAudioModulesDir = configs.get('PulseAudio', 'outputModulesDir', fallback='pulseaudio-modules').strip()
    outputPulseAudioModulesDir = os.path.join(dataDir, outputPulseAudioModulesDir)
    pulseAudioModulesDir = configs.get('PulseAudio', 'modulesDir', fallback='').strip()

    if pulseAudioModulesDir == '':
        if 'PULSEAUDIO_MODULE_DIR' in os.environ:
            pulseAudioModulesDir = os.environ['PULSEAUDIO_MODULE_DIR']

    pulseAudioModules = configs.get('PulseAudio', 'modules', fallback='')

    if pulseAudioModules == '':
        pulseAudioModules = []
    else:
        pulseAudioModules = [plugin.strip() for plugin in pulseAudioModules.split(',')]

    sysLibDir = configs.get('System', 'libDir', fallback='')
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()
    havePulseAudio = configs.get('PulseAudio', 'havePulseAudio', fallback='false').strip()
    havePulseAudio = DTUtils.toBool(havePulseAudio)

    if not havePulseAudio:
        havePulseAudio = dependsOnPulseAudio(configs,
                                             targetPlatform,
                                             targetArch,
                                             debug,
                                             dataDir,
                                             sysLibDir)

    print('PulseAudio information')
    print()
    print('PulseAudio modules directory: {}'.format(pulseAudioModulesDir))
    print('PulseAudio modules output directory: {}'.format(outputPulseAudioModulesDir))
    print()
    print('Copying required PulseAudio modules')
    print()

    if havePulseAudio:
        copyPulseAudioModules(globs,
                              outputPulseAudioModulesDir,
                              pulseAudioModules,
                              pulseAudioModulesDir)

def postRun(globs, configs, dataDir):
    pass
