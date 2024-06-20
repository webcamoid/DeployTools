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
from . import DTUtils


def hostPlatform():
    if os.name == 'posix' and sys.platform.startswith('darwin'):
        return 'mac'
    elif os.name == 'nt' and sys.platform.startswith('win32'):
        return 'windows'
    elif os.name == 'posix':
        return 'posix'

    return ''

def realPath(path):
    if hostPlatform() == 'windows':
        return path

    return os.path.realpath(path)

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

def isPathHiger(path, start=os.curdir):
    rel = os.path.relpath(os.path.normpath(path), start)

    return rel.startswith("..")

def repositionPath(path, start=os.curdir):
    rel = os.path.relpath(os.path.normpath(path), start)

    if rel.startswith(".."):
        return os.path.join(start, rel.replace('..', 'up'))

    return path

def copy(src, dst='.', copyReals=False, overwrite=True, rootPath=''):
    if not os.path.exists(src):
        return False

    if hostPlatform() == 'windows':
        copyReals = True

    realsrc = realPath(src)

    if os.path.isfile(realsrc):
        dstdir = os.path.normpath(os.path.dirname(dst))
        dstfile = dst

        if os.path.isdir(dst):
            dstdirs = dst
            dstfile = os.path.join(dst, os.path.basename(src))

        if not os.path.exists(dstdir):
            try:
                os.makedirs(dstdir)
            except:
                return False

        if overwrite or not os.path.exists(dstfile):
            if os.path.exists(dstfile) or os.path.islink(dstfile):
                os.remove(dstfile)

            realsrcdir = os.path.dirname(realsrc)
            srcdir = os.path.dirname(src)
            relsrcdir = os.path.relpath(realsrcdir, srcdir)
            srclink = os.path.join(relsrcdir, os.path.basename(realsrc))
            dstlink = os.path.normpath(os.path.join(dstdir, srclink))

            if rootPath != '' \
                and not copyReals \
                and os.path.islink(src) \
                and isPathHiger(dstlink, rootPath):
                rep = os.path.dirname(repositionPath(dstlink, rootPath))
                reldstdir = os.path.relpath(rep, dstdir)
                dstlink = os.path.join(reldstdir, os.path.basename(dstlink))

                try:
                    os.symlink(dstlink, dstfile)
                except:
                    return False
            else:
                try:
                    shutil.copy(src, dstfile, follow_symlinks=copyReals)
                except:
                    return False

            if os.path.islink(src) and not copyReals:
                dstfile = os.path.join(dstdir, relsrcdir, os.path.basename(realsrc))

                if rootPath != '':
                    dstfile = repositionPath(dstfile, rootPath)

                if not copy(realsrc, dstfile, copyReals, overwrite, rootPath):
                    return False

        return True

    if os.path.isfile(dst):
        return False

    for root, dirs, files in os.walk(src):
        for f in files:
            srcfile = os.path.join(root, f)
            relsrcfile = os.path.relpath(srcfile, src)
            dstfile = os.path.join(dst, relsrcfile)
            copy(srcfile, dstfile, copyReals, overwrite, rootPath)

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
                    copy(srcdir, dstdir, copyReals, overwrite, rootPath)
                else:
                    realsrcdir = realPath(srcdir)
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
            dst = realPath(dst)
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
            realpath = realPath(src)
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
    if size < 1:
        return '0 B'

    i = int(math.log(size) // math.log(1024))

    if i < 1:
        return '{} B'.format(size)

    units = ['KiB', 'MiB', 'GiB', 'TiB']
    sizeKiB = size / (1024 ** i)

    return '{:.2f} {}'.format(sizeKiB, units[i - 1])

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
    hideCommitCount = configs.get('Git', 'hideCommitCount', fallback='false').strip()
    hideCommitCount = DTUtils.toBool(hideCommitCount)
    dailyBuild = configs.get('Package', 'dailyBuild', fallback='false').strip()
    dailyBuild = DTUtils.toBool(dailyBuild)

    if dailyBuild:
        branch = ''

        if 'TRAVIS_BRANCH' in os.environ:
            branch = os.environ['TRAVIS_BRANCH']
        elif 'APPVEYOR_REPO_BRANCH' in os.environ:
            branch = os.environ['APPVEYOR_REPO_BRANCH']
        elif 'GITHUB_REF' in os.environ and os.environ['GITHUB_REF'] != '':
            branch = os.path.basename(os.environ['GITHUB_REF'])
        else:
            branch = DTGit.branch(sourcesDir)

        if hideCommitCount:
            return 'daily-' + branch

        count = DTGit.commitCount(sourcesDir)

        return 'daily-{}-{}'.format(branch, count)

    return configs.get('Package', 'version', fallback='0.0.0').strip()

def versionCode(version):
    return ''.join([n.rjust(4, '0') for n in version.split('.')])

def compareVersions(version1, op, version2):
    ver1 = versionCode(version1)
    ver2 = versionCode(version2)

    return op(ver1, v2)

def solvedepsLibs(globs,
                  mainExecutable,
                  targetPlatform,
                  targetArch,
                  debug,
                  dataDir,
                  libDir,
                  sysLibDir,
                  extraLibs,
                  stripCmd='strip'):
    solver = DTBinary.BinaryTools(hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
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
                copyReals = targetPlatform == 'windows'
                copy(dep, depPath, copyReals, True, dataDir)

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
