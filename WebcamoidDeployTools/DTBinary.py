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

import importlib
import os
import re
import subprocess # nosec
import threading
import time

from . import DTUtils


class BinaryTools:
    def __init__(self, 
                 hostPlatform, 
                 targetPlatform, 
                 targetArch, 
                 sysLibDir,
                 stripCmd='strip'):
        super().__init__()
        self.hostPlatform = hostPlatform
        self.targetPlatform = targetPlatform
        self.stripBin = DTUtils.whereBin(stripCmd)
        self.solver = None

        if targetPlatform == 'mac':
            self.solver = importlib.import_module('WebcamoidDeployTools.DTBinaryMach')
        elif targetPlatform == 'windows':
            self.solver = importlib.import_module('WebcamoidDeployTools.DTBinaryPecoff')
        else:
            self.solver = importlib.import_module('WebcamoidDeployTools.DTBinaryElf')

        self.solver.init(targetPlatform, targetArch, sysLibDir)
        self.excludes = []
        self.readExcludes()

    def name(self, binary):
        return self.solver.name(binary)

    def find(self, path):
        binaries = []

        for root, _, files in os.walk(path):
            for f in files:
                binaryPath = os.path.join(root, f)

                if not os.path.islink(binaryPath) and self.solver.isValid(binaryPath):
                    binaries.append(binaryPath)

        return binaries

    def dump(self, binary):
        return self.solver.dump(binary)

    def allDependencies(self, binary):
        deps = self.filterDependencies(self.solver.dependencies(binary))
        solved = set()

        while len(deps) > 0:
            dep = deps.pop()

            for binDep in self.filterDependencies(self.solver.dependencies(dep)):
                if binDep != dep and not binDep in solved:
                    deps.append(binDep)

            if self.hostPlatform == 'mac':
                i = dep.rfind('.framework/')

                if i >= 0:
                    dep = dep[: i] + '.framework'

            solved.add(dep)

        return solved

    def scanDependencies(self, path):
        deps = set()

        for binPath in self.find(path):
            for dep in self.allDependencies(binPath):
                deps.add(dep)

        return sorted(deps)

    def guess(self, mainExecutable, dependency):
        return self.solver.guess(mainExecutable, dependency)

    def strip(self, binary):
        if self.stripBin == '':
            return

        process = subprocess.Popen([self.stripBin, binary], # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process.communicate()

    def stripSymbols(self, path):
        threads = []

        for binary in self.find(path):
            thread = threading.Thread(target=self.strip, args=(binary,))
            threads.append(thread)

            while threading.active_count() >= DTUtils.numThreads():
                time.sleep(0.25)

            thread.start()

        for thread in threads:
            thread.join()

    def readExcludes(self):
        curDir = os.path.dirname(os.path.realpath(__file__))
        self.readExcludeList(os.path.join(curDir, 'exclude', self.targetPlatform + '.txt'))

    def readExcludeList(self, excludeList):
        self.excludes = []

        if os.path.exists(excludeList):
            with open(excludeList) as f:
                for line in f:
                    line = line.strip()

                    if len(line) > 0 and line[0] != '#':
                        i = line.find('#')

                        if i >= 0:
                            line = line[: i]

                        line = line.strip()

                        if len(line) > 0:
                            self.excludes.append(line)

    def isExcluded(self, path):
        for exclude in self.excludes:
            if self.targetPlatform == 'windows':
                path = path.lower().replace('\\', '/')
                exclude = exclude.lower()

            if re.fullmatch(exclude, path):
                return True

        return False

    def filterDependencies(self, deps):
        outDeps = []

        for dep in deps:
            if not self.isExcluded(dep):
                outDeps.append(dep)

        return outDeps

    def resetFilePermissions(self, rootPath, binariesPath):
        for root, dirs, files in os.walk(rootPath):
            for d in dirs:
                permissions = 0o755
                path = os.path.join(root, d)

                if self.hostPlatform == 'mac':
                    os.chmod(path, permissions, follow_symlinks=False)
                else:
                    os.chmod(path, permissions)

            for f in files:
                permissions = 0o644
                path = os.path.join(root, f)

                if root == binariesPath and self.solver.isValid(path):
                    permissions = 0o744

                if self.hostPlatform == 'mac':
                    os.chmod(path, permissions, follow_symlinks=False)
                else:
                    os.chmod(path, permissions)
