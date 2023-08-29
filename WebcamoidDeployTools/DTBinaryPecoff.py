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

import mimetypes
import os
import struct
import sys

from . import DTUtils


EXTRA_LIBRARY_PATH = []

def isValid(path):
    mimetype, _ = mimetypes.guess_type(path)

    if mimetype == 'application/x-msdownload':
        return True

    if mimetype != 'application/octet-stream':
        return False

    try:
        with open(path, 'rb') as f:
            if f.read(2) != b'MZ':
                return []

            f.seek(0x3c, os.SEEK_SET)
            peHeaderOffset = struct.unpack('I', f.read(4))
            f.seek(peHeaderOffset[0], os.SEEK_SET)
            peSignatue = f.read(4)

            if peSignatue == b'PE\x00\x00':
                return True
    except:
        pass

    return False

def name(binary, configs=None):
    dep = os.path.basename(binary)

    return dep[: dep.lower().find('.dll')]

def init(targetPlatform, targetArch, sysLibDir):
    global EXTRA_LIBRARY_PATH

    EXTRA_LIBRARY_PATH = sysLibDir

# https://msdn.microsoft.com/en-us/library/windows/desktop/ms680547(v=vs.85).aspx
# https://upload.wikimedia.org/wikipedia/commons/1/1b/Portable_Executable_32_bit_Structure_in_SVG_fixed.svg
def dump(binary):
    # Characteristics flags
    IMAGE_FILE_EXECUTABLE_IMAGE = 0x2

    dllImports = set()

    if not os.path.exists(binary) or not os.path.isfile(binary):
        return {}

    with open(binary, 'rb') as f:
        # Check DOS header signature.
        if f.read(2) != b'MZ':
            return []

        # Move to COFF header.
        f.seek(0x3c, os.SEEK_SET)
        peHeaderOffset = struct.unpack('I', f.read(4))
        f.seek(peHeaderOffset[0], os.SEEK_SET)
        peSignatue = f.read(4)

        # Check COFF header signature.
        if peSignatue != b'PE\x00\x00':
            return []

        # Read COFF header.
        coffHeader = struct.unpack('HHIIIHH', f.read(20))
        nSections = coffHeader[1]
        sectionTablePos = coffHeader[5] + f.tell()
        fileType = 'executable' if coffHeader[6] & IMAGE_FILE_EXECUTABLE_IMAGE != 0 else 'library'

        # Read magic signature in standard COFF fields.
        peType = 'PE32' if f.read(2) == b'\x0b\x01' else 'PE32+'

        # Move to data directories.
        f.seek(102 if peType == 'PE32' else 118, os.SEEK_CUR)

        # Read the import table.
        importTablePos, importTableSize = struct.unpack('II', f.read(8))

        # Move to Sections table.
        f.seek(sectionTablePos, os.SEEK_SET)
        sections = []
        idataTablePhysical = -1

        # Search for 'idata' section.
        for _ in range(nSections):
            # Read section.
            section = struct.unpack('8pIIIIIIHHI', f.read(40))
            sectionName = section[0].replace(b'\x00', b'')

            # Save a reference to the sections.
            sections += [section]

            if sectionName == b'idata' or sectionName == b'rdata':
                idataTablePhysical = section[4]

                # If import table was defined calculate it's position in
                # the file in relation to the address given by 'idata'.
                if importTableSize > 0:
                    idataTablePhysical += importTablePos - section[2]

        if idataTablePhysical < 0:
            return []

        # Move to 'idata' section.
        f.seek(idataTablePhysical, os.SEEK_SET)
        dllList = set()

        # Read 'idata' directory table.
        while True:
            # Read DLL entries.
            try:
                dllImport = struct.unpack('IIIII', f.read(20))
            except:
                break

            # Null directory entry.
            if dllImport[0] | dllImport[1] | dllImport[2] | dllImport[3] | dllImport[4] == 0:
                break

            # Locate where is located the DLL name in relation to the
            # sections.
            for section in sections:
                if dllImport[3] >= section[2] \
                    and dllImport[3] < section[1] + section[2]:
                    dllList.add(dllImport[3] - section[2] + section[4])

                    break

        for dll in dllList:
            # Move to DLL name.
            f.seek(dll, os.SEEK_SET)
            dllName = b''

            # Read string until null character.
            while True:
                c = f.read(1)

                if c == b'\x00':
                    break

                dllName += c

            try:
                dllImports.add(dllName.decode(sys.getdefaultencoding()))
            except:
                pass

    return {'imports': dllImports,
            'type': fileType}

def dependencies(binary):
    info = dump(binary)

    if not 'imports' in info:
        return []

    deps = []

    for dep in info['imports']:
        depPath = DTUtils.whereBin(dep, EXTRA_LIBRARY_PATH)

        if len(depPath) > 0:
            deps.append(depPath)

    return deps

def guess(mainExecutable, dependency):
    return DTUtils.whereBin(dependency, EXTRA_LIBRARY_PATH)
