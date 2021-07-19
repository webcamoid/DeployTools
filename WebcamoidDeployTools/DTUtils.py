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

import configparser
import hashlib
import math
import multiprocessing
import os
import shutil
import sys

from . import DTGit
from . import DTBinary
from . import DTMac


def toBool(string):
    if string.lower() in ['true', 'yes', '1']:
        return True

    return False

def whereBin(binary, extraPaths=[]):
    pathSep = ';' if hostPlatform() == 'windows' else ':'
    sysPath = os.environ['PATH'].split(pathSep) if 'PATH' in os.environ else []
    paths = extraPaths + sysPath

    for path in paths:
        path = os.path.join(path, binary)

        if os.path.exists(path):
            return path
        elif hostPlatform() == 'windows' \
            and not path.endswith('.exe') \
            and os.path.exists(path + '.exe'):
                return path + '.exe'

    return ''

def copy(src, dst='.', copyReals=False, overwrite=True):
    if not os.path.exists(src):
        return False

    if hostPlatform() == 'windows':
        copyReals = True

    if os.path.isfile(src):
        dstdir = os.path.dirname(dst)
        dstfile = dst

        if os.path.isdir(dst):
            dstdirs = dst
            dstfile = os.path.join(dst, os.path.basename(src))

        if not os.path.exists(dstdir):
            try:
                os.makedirs(os.path.normpath(dstdir))
            except:
                return False

        print('COPY {} -> {}'.format(src, dstfile))

        if overwrite or not os.path.exists(dstfile):
            print('OVERWRITE')

            if os.path.exists(dstfile) or os.path.islink(dstfile):
                os.remove(dstfile)

            if os.path.islink(src) and copyReals:
                print('COPY_SYMLINK')
                realsrc = os.path.realpath(src)
                realsrcdir = os.path.dirname(realsrc)
                srcdir = os.path.dirname(src)
                relsrcdir = os.path.relpath(realsrcdir, srcdir)
                dstfile = os.path.join(dstdir, relsrcdir, os.path.basename(realsrc))
                copy(realsrc, dstfile, copyReals, overwrite)
            else:
                try:
                    print('COPY_NORMAL')
                    shutil.copy(src, dstfile, follow_symlinks=copyReals)
                    print('COPY_DONE')
                except:
                    return False

        return True

    if os.path.isfile(dst):
        return False

    for root, dirs, files in os.walk(src):
        for f in files:
            srcfile = os.path.join(root, f)
            relsrcfile = os.path.relpath(srcfile, src)
            dstfile = os.path.join(dst, relsrcfile)
            copy(srcfile, dstfile, copyReals, overwrite)

        for d in dirs:
            srcdir = os.path.join(root, d)
            relsrcdir = os.path.relpath(srcdir, src)
            dstdir = os.path.join(dst, relsrcdir)

            if os.path.exists(dstdir):
                if os.path.islink(dstdir):
                    try:
                        os.unlink(dstdir)
                    except:
                        return False
                elif os.path.isfile(dstdir):
                    try:
                        os.remove(dstdir)
                    except:
                        return False
                elif os.path.islink(srcdir):
                    try:
                        shutil.rmtree(dstdir)
                    except:
                        return False

            if os.path.islink(srcdir):
                if copyReals:
                    copy(srcdir, dstdir, copyReals, overwrite)
                else:
                    realsrcdir = os.path.realpath(srcdir)
                    relsrcdir = os.path.relpath(realsrcdir,
                                                os.path.dirname(srcdir))

                    try:
                        os.symlink(relsrcdir, dstdir)
                    except:
                        pass
            else:
                try:
                    os.makedirs(dstdir)
                except:
                    pass

    return True

def move(src, dst='.', moveReals=False):
    if not os.path.exists(src):
        return False

    if os.path.isdir(src):
        if os.path.isfile(dst):
            return False

        for root, dirs, files in os.walk(src):
            for f in files:
                fromF = os.path.join(root, f)
                toF = os.path.relpath(fromF, src)
                toF = os.path.join(dst, toF)
                toF = os.path.normpath(toF)
                move(fromF, toF, moveReals)

            for d in dirs:
                fromD = os.path.join(root, d)
                toD = os.path.relpath(fromD, src)
                toD = os.path.join(dst, toD)

                try:
                    os.makedirs(os.path.normpath(toD))
                except:
                    pass
    elif os.path.isfile(src):
        if os.path.isdir(dst):
            dst = os.path.realpath(dst)
            dst = os.path.join(dst, os.path.basename(src))

        dirname = os.path.dirname(dst)

        if len(dirname) < 1:
            dirname = os.getcwd()

        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                return False

        if os.path.exists(dst):
            try:
                os.remove(dst)
            except:
                return False

        if moveReals and os.path.islink(src):
            realpath = os.path.realpath(src)
            basename = os.path.basename(realpath)
            os.symlink(os.path.join('.', basename), dst)
            move(realpath, os.path.join(dirname, basename), moveReals)
        else:
            try:
                shutil.move(src, dst)
            except:
                return False

    return True

def sha256sum(fileName):
    sha = hashlib.sha256()

    with open(fileName, 'rb') as f:
        while True:
            data = f.read(1024)

            if not data:
                break

            sha.update(data)

    return sha.hexdigest()

def md5sum(fileName):
    sha = hashlib.md5()

    with open(fileName, 'rb') as f:
        while True:
            data = f.read(1024)

            if not data:
                break

            sha.update(data)

    return sha.hexdigest()

def hrSize(size):
    i = int(math.log(size) // math.log(1024))

    if i < 1:
        return '{} B'.format(size)

    units = ['KiB', 'MiB', 'GiB', 'TiB']
    sizeKiB = size / (1024 ** i)

    return '{:.2f} {}'.format(sizeKiB, units[i - 1])

def hostPlatform():
    if os.name == 'posix' and sys.platform.startswith('darwin'):
        return 'mac'
    elif os.name == 'nt' and sys.platform.startswith('win32'):
        return 'windows'
    elif os.name == 'posix':
        return 'posix'

    return ''

def readConfigs(configFile):
    try:
        packageConf = configparser.ConfigParser()
        packageConf.optionxform=str
        packageConf.read(configFile, 'utf-8')
        configs = packageConf
    except:
        pass

    return configs

def numThreads():
    nthreads = multiprocessing.cpu_count()

    if nthreads < 4:
        return 4

    return nthreads

def programVersion(configs, sourcesDir):
    if 'DAILY_BUILD' in os.environ:
        branch = ''

        if 'TRAVIS_BRANCH' in os.environ:
            branch = os.environ['TRAVIS_BRANCH']
        elif 'APPVEYOR_REPO_BRANCH' in os.environ:
            branch = os.environ['APPVEYOR_REPO_BRANCH']
        elif 'GITHUB_REF' in os.environ:
            branch = os.path.basename(os.path.basename(os.environ['GITHUB_REF']))
        else:
            branch = DTGit.branch(sourcesDir)

        count = DTGit.commitCount(sourcesDir)

        return 'daily-{}-{}'.format(branch, count)

    return configs.get('Package', 'version', fallback='0.0.0').strip()

def versionCode(version):
    return ''.join([n.rjust(4, '0') for n in version.split('.')])

def solvedepsLibs(globs,
                  mainExecutable,
                  targetPlatform,
                  targetArch,
                  dataDir,
                  libDir,
                  sysLibDir,
                  extraLibs,
                  stripCmd='strip'):
    solver = DTBinary.BinaryTools(hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  sysLibDir,
                                  stripCmd)

    if not 'dependencies' in globs:
        globs['dependencies'] = set()

    deps = set(solver.scanDependencies(dataDir))

    if mainExecutable != '':
        for dep in extraLibs:
            path = solver.guess(mainExecutable, dep)

            if path != '':
                deps.add(path)
                deps.update(solver.allDependencies(path))

    deps = sorted(deps)
    depsInstallDir = ''

    if targetPlatform == 'windows':
        depsInstallDir = os.path.dirname(mainExecutable)
    else:
        depsInstallDir = libDir

    for dep in deps:
        dep = dep.replace('\\', '/')
        depPath = os.path.join(depsInstallDir, os.path.basename(dep))
        depPath = depPath.replace('\\', '/')

        if dep != depPath:
            if hostPlatform() == 'windows':
                dep = dep.replace('/', '\\')
                depPath = depPath.replace('/', '\\')

            print('    {} -> {}'.format(dep, depPath))

            if hostPlatform() == 'mac' and dep.endswith('.framework'):
                DTMac.copyBundle(dep, depPath)
            else:
                copyReals = targetPlatform != 'windows'
                copy(dep, depPath, copyReals)

            globs['dependencies'].add(dep)

    globs['libs'] = set(deps)

def pathSize(path):
    if os.path.isfile(path):
        return os.path.getsize(path)

    size = 0

    for root, _, files in os.walk(path):
        for f in files:
            fpath = os.path.join(root, f)

            if not os.path.islink(fpath):
                size += os.path.getsize(fpath)

    return size
