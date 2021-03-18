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
import zipfile


def platforms():
    return ['mac', 'posix', 'windows']

def isAvailable(configs):
    return True

def run(globs, configs, dataDir, outputDir, mutex):
    name = configs.get('Package', 'name', fallback='app').strip()
    version = configs.get('Package', 'version', fallback='1.0.0').strip()
    packageName = configs.get('CompressedZip', 'name', fallback=name).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    defaultHideArch = DTUtils.toBool(defaultHideArch)
    defaultHideArch = 'true' if defaultHideArch else 'false'
    hideArch = configs.get('CompressedZip', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    outPackage = os.path.join(outputDir, '{}-{}'.format(packageName, version))
                     
    if not hideArch:
        outPackage += '-' + targetArch
        
    outPackage += '.zip'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    with zipfile.ZipFile(outPackage, 'w', zipfile.ZIP_DEFLATED, False) as zipFile:
        for root, dirs, files in os.walk(dataDir):
            for f in dirs + files:
                filePath = os.path.join(root, f)
                dstPath = os.path.join(name,
                                       filePath.replace(dataDir + os.sep, ''))
                zipFile.write(filePath, dstPath)

    if not os.path.exists(outPackage):
        return

    mutex.acquire()

    if not 'outputPackages' in globs:
        globs['outputPackages'] = []

    globs['outputPackages'].append(outPackage)
    mutex.release()
