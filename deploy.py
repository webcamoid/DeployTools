#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid, webcam capture application.
# Copyright (C) 2021  Gonzalo Exequiel Pedone
#
# Webcamoid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Webcamoid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Webcamoid. If not, see <http://www.gnu.org/licenses/>.
#
# Web-Site: http://webcamoid.github.io/

import importlib
import optparse
import os
import platform
import sys
import threading

from WebcamoidDeployTools import DTUtils
from WebcamoidDeployTools import DTBinary


if __name__ =='__main__':
    usage = """%prog [options]"""
    description = 'Deploy tools for Webcamoid.'
    epilog =  'For more info go here: <https://github.com/webcamoid/DeployTools>'
    parser = optparse.OptionParser(usage=usage, version='1.0.0', description=description, epilog=epilog)
    parser.add_option('-d',
                      '--data',
                      action='store',
                      type='string',
                      dest='data_dir',
                      help='Directory with the data to package.',
                      metavar='DATA_FOLDER',
                      default='')
    parser.add_option('-c',
                      '--config',
                      action='append',
                      type='string',
                      dest='config_file',
                      help='Packaging settings.',
                      metavar='CONFIG_FILE')
    parser.add_option('-o',
                      '--output',
                      action='store',
                      type='string',
                      dest='output_dir',
                      help='Output directory for packages.',
                      metavar='PACKAGES_FOLDER',
                      default=os.getcwd())
    parser.add_option('-r',
                      '--prepare',
                      action='store_true',
                      dest='prepare_only',
                      help='Prepare the data for packaging.')
    parser.add_option('-s',
                      '--package',
                      action='store_true',
                      dest='package_only',
                      help='Just package the data.')
    options, args = parser.parse_args()

    if len(options.data_dir) < 1 or len(options.config_file) < 1:
        parser.print_help()
        exit()

    if not os.path.exists(options.data_dir) or not os.path.isdir(options.data_dir):
        print("Invalid data directory", file=sys.stderr)
        exit(-1)

    if len(os.listdir(options.data_dir)) < 1:
        print("The data directory is empty", file=sys.stderr)
        exit(-1)

    configs = DTUtils.readConfigs(options.config_file)

    if not configs:
        print("The config file is invalid", file=sys.stderr)
        exit(-1)

    hostPlatform = DTUtils.hostPlatform()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    globs = {}

    print('Build info')
    print()
    print('Python version:', platform.python_version())
    print('Config files:', options.config_file)
    print('Sources directory:', sourcesDir)
    print('Data directory:', options.data_dir)
    print('Output directory:', options.output_dir)
    print('Host platform:', hostPlatform)
    print('Target platform:', targetPlatform)
    print('Target architecture:', targetArch)
    print('Number of threads:', DTUtils.numThreads())
    print('Program version:', DTUtils.programVersion(configs, sourcesDir))
    print()

    if options.prepare_only or \
        (not options.prepare_only and not options.package_only):
        modules = configs.get('Package', 'modules', fallback='')

        if modules == '':
            modules = []
        else:
            modules = [module.strip() for module in modules.split(',')]

        modules.append(targetPlatform.capitalize())

        for module in modules:
            print('Running {} module pre-processing'.format(module))
            print()
            mod = importlib.import_module('WebcamoidDeployTools.DT' + module)
            mod.preRun(globs, configs, options.data_dir)

        for module in modules:
            print('Running {} module post-processing'.format(module))
            print()
            mod = importlib.import_module('WebcamoidDeployTools.DT' + module)
            mod.postRun(globs, configs, options.data_dir)

        print()

    if options.package_only or \
        (not options.prepare_only and not options.package_only):
        print('Packaged data:')
        print()
        packagedFiles = []

        for root, _, files in os.walk(options.data_dir):
            for f in files:
                packagedFiles.append(os.path.join(root, f))

        packagedFiles = sorted(packagedFiles)

        for f in packagedFiles:
            print('    ' + os.path.relpath(f, options.data_dir))

        print()
        size = DTUtils.pathSize(options.data_dir)
        print('Packaged data size:', DTUtils.hrSize(size))
        print()

        outputFormats = configs.get('Package', 'outputFormats', fallback='')

        if outputFormats == '':
            outputFormats = []
        else:
            outputFormats = [fmt.strip() for fmt in outputFormats.split(',')]

        packagingTools = []

        for format in outputFormats:
            mod = importlib.import_module('WebcamoidDeployTools.DT' + format)

            if targetPlatform in mod.platforms() and mod.isAvailable(configs):
                packagingTools.append(format)

        if len(packagingTools) > 0:
            print('Running packaging')
            print()
            print('Formats: {}'.format(', '.join(packagingTools)))
            print()

            if not os.path.exists(options.output_dir):
                os.makedirs(options.output_dir)

            mutex = threading.Lock()
            threads = []

            for format in packagingTools:
                mod = importlib.import_module('WebcamoidDeployTools.DT' + format)
                threads.append(threading.Thread(target=mod.run,
                                                args=(globs,
                                                      configs,
                                                      options.data_dir,
                                                      options.output_dir,
                                                      mutex,)))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            if 'outputPackages' in globs and len(globs['outputPackages']) > 0:
                print('Packages created:')

                for package in globs['outputPackages']:
                    print('   ', os.path.basename(package), DTUtils.hrSize(os.path.getsize(package)))
                    print('        md5sum:', DTUtils.md5sum(package))

            else:
                print('No packages were created')
        else:
            print('Packaging formats not detected')
