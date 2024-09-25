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

import math
import os
import subprocess
import sys
import tempfile
import time

from . import DTUtils


def dirSize(path):
    size = 0

    for root, _, files in os.walk(path):
        for f in files:
            fpath = os.path.join(root, f)

            if not os.path.islink(fpath):
                size += os.path.getsize(fpath)

    return size

def signPackage(package, verbose):
    params = ['codesign', # nosec
              '--verbose',
              '--force',
              '--sign',
              '-',
              package]

    if verbose:
        process = subprocess.Popen(params) # nosec
    else:
        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

# https://asmaloney.com/2013/07/howto/packaging-a-mac-os-x-application-using-a-dmg/
def createDmg(globs,
              mutex,
              dataDir,
              outPackage,
              name,
              version,
              appIcon,
              verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        staggingDir = os.path.join(tmpdir, 'stagging')

        if not os.path.exists(staggingDir):
            os.makedirs(staggingDir)

        DTUtils.copy(dataDir, staggingDir)
        imageSize = dirSize(staggingDir)
        tmpDmg = os.path.join(tmpdir, name + '_tmp.dmg')
        volumeName = "{}-{}".format(name, version)
        params = ['hdiutil', 'create',
                  '-verbose',
                  '-srcfolder', staggingDir,
                  '-volname', volumeName,
                  '-fs', 'HFS+',
                  '-fsargs', '-c c=64,a=16,e=16',
                  '-format', 'UDRW',
                  '-size', str(math.ceil(imageSize * 1.1)),
                  tmpDmg]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        process.communicate()

        params = ['hdiutil',
                  'attach',
                  '-readwrite',
                  '-noverify',
                  tmpDmg]

        if verbose:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE}
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE)
        stdout, _ = process.communicate()
        device = ''

        for line in stdout.split(b'\n'):
            line = line.strip()

            if len(line) < 1:
                continue

            dev = line.split()

            if len(dev) > 2:
                device = dev[0].decode(sys.getdefaultencoding())

                break

        time.sleep(2)
        volumePath = os.path.join('/Volumes', volumeName)
        volumeIcon = os.path.join(volumePath, '.VolumeIcon.icns')
        DTUtils.copy(appIcon, volumeIcon)

        params = ['SetFile',
                  '-c', 'icnC',
                  volumeIcon]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        process.communicate()

        params = ['SetFile',
                  '-a', 'C',
                  volumeIcon]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        process.communicate()

        appsShortcut = os.path.join(volumePath, 'Applications')

        try:
            if not os.path.exists(appsShortcut):
                os.symlink('/Applications', appsShortcut)
        except:
            pass

        os.sync()

        params = ['hdiutil', # nosec
                  'detach',
                  '-verbose',
                  device]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        process.communicate()

        params = ['hdiutil', # nosec
                  'convert',
                  tmpDmg,
                  '-verbose',
                  '-format', 'UDZO',
                  '-imagekey', 'zlib-level=9',
                  '-o', outPackage]

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
    if len(DTUtils.whereBin('hdiutil')) < 1:
        return False

    if len(DTUtils.whereBin('SetFile')) < 1:
        return False

    if len(DTUtils.whereBin('codesign')) < 1:
        return False

    return True

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('Dmg', 'name', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('Dmg', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    icon = configs.get('Dmg', 'icon', fallback='app.icns').strip()
    icon = os.path.join(sourcesDir, icon)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('Dmg', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    verbose = configs.get('AndroidAPK', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    showTargetPlatform = configs.get('Dmg', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.dmg'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createDmg(globs,
              mutex,
              dataDir,
              outPackage,
              packageName,
              version,
              icon,
              verbose)
