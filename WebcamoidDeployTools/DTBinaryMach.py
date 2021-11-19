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
import struct
import sys


# 32 bits magic number.
MH_MAGIC = 0xfeedface # Native endian
MH_CIGAM = 0xcefaedfe # Reverse endian

# 64 bits magic number.
MH_MAGIC_64 = 0xfeedfacf # Native endian
MH_CIGAM_64 = 0xcffaedfe # Reverse endian

# File types.
MH_EXECUTE = 0x2 # Executable file

def isValid(path):
    try:
        with open(path, 'rb') as f:
            # Read magic number.
            magic = struct.unpack('I', f.read(4))[0]

            if magic == MH_MAGIC \
                or magic == MH_CIGAM \
                or magic == MH_MAGIC_64 \
                or magic == MH_CIGAM_64:
                return True
    except:
        pass

    return False

def name(binary):
    dep = os.path.basename(binary)
    i = dep.find('.dylib')

    if i >= 0:
        dep = dep[: dep.find('.dylib')]

    if 'Qt' in dep and not 'Qt5' in dep:
        dep = dep.replace('Qt', 'Qt5')

    return dep

def init(targetPlatform, targetArch, sysLibDir):
    pass

def solveRefpath(path):
    if not path.startswith('@'):
        return path

    searchPaths = []

    if 'DYLD_LIBRARY_PATH' in os.environ:
        searchPaths += os.environ['DYLD_LIBRARY_PATH'].split(':')

    if 'DYLD_FRAMEWORK_PATH' in os.environ:
        searchPaths += os.environ['DYLD_FRAMEWORK_PATH'].split(':')

    searchPaths += ['/usr/local/lib']

    if path.endswith('.dylib'):
        dep = os.path.basename(path)
    else:
        i = path.rfind(os.sep, 0, path.rfind('.framework'))
        dep = path[i + 1:]

    for fpath in searchPaths:
        realPath = os.path.join(fpath, dep)

        if os.path.exists(realPath):
            return realPath

    return ''

# https://github.com/aidansteele/osx-abi-macho-file-format-reference
def dump(binary):
    if not os.path.exists(binary):
        return {}

    # Commands definitions
    LC_REQ_DYLD = 0x80000000
    LC_LOAD_DYLIB = 0xc
    LC_RPATH = 0x1c | LC_REQ_DYLD
    LC_ID_DYLIB = 0xd

    dylibImports = []
    rpaths = []
    dylibId = ''

    with open(binary, 'rb') as f:
        # Read magic number.
        magic = 0

        try:
            magic = struct.unpack('I', f.read(4))[0]
        except:
            return {}

        if magic == MH_MAGIC or magic == MH_CIGAM:
            is32bits = True
        elif magic == MH_MAGIC_64 or magic == MH_CIGAM_64:
            is32bits = False
        else:
            return {}

        # Read file type.
        f.seek(8, os.SEEK_CUR)
        fileType = struct.unpack('I', f.read(4))[0]
        fileType = 'executable' if fileType == MH_EXECUTE else 'library'

        # Read number of commands.
        ncmds = struct.unpack('I', f.read(4))[0]

        # Move to load commands
        f.seek(8 if is32bits else 12, os.SEEK_CUR)

        for _ in range(ncmds):
            # Read a load command and store it's position in the file.
            loadCommandStart = f.tell()
            loadCommand = struct.unpack('II', f.read(8))

            # If the command list a library
            if loadCommand[0] in [LC_LOAD_DYLIB, LC_RPATH, LC_ID_DYLIB]:
                # Save the position of the next command.
                nextCommand = f.tell() + loadCommand[1] - 8

                # Move to the string
                f.seek(loadCommandStart + struct.unpack('I', f.read(4))[0], os.SEEK_SET)
                dylib = b''

                # Read string until null character.
                while True:
                    c = f.read(1)

                    if c == b'\x00':
                        break

                    dylib += c
                s = dylib.decode(sys.getdefaultencoding())

                if loadCommand[0] == LC_LOAD_DYLIB:
                    dylibImports.append(s)
                elif loadCommand[0] == LC_RPATH:
                    rpaths.append(s)
                elif loadCommand[0] == LC_ID_DYLIB:
                    dylibId = s

                f.seek(nextCommand, os.SEEK_SET)
            else:
                f.seek(loadCommand[1] - 8, os.SEEK_CUR)

    return {'imports': dylibImports,
            'rpaths': rpaths,
            'id': dylibId,
            'type': fileType}

def dependencies(binary):
    machInfo = dump(binary)

    if not machInfo:
        return []

    libs = []

    for mach in machInfo['imports']:
        mach = solveRefpath(mach)

        if len(mach) < 1:
            continue

        dirName = os.path.dirname(mach)
        dirName = os.path.realpath(dirName)
        baseName = os.path.basename(mach)
        libs.append(os.path.join(dirName, baseName))

    return libs

def guess(mainExecutable, dependency):
    dep = solveRefpath(dependency)

    if len(dep) < 1:
        return ''

    dirName = os.path.dirname(dep)
    dirName = os.path.realpath(dirName)
    baseName = os.path.basename(dep)

    return os.path.join(dirName, baseName)
