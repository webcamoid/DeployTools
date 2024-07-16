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
import json
import os
import platform
import re
import shutil
import subprocess # nosec
import sys
import time
import xml.etree.ElementTree as ET

from . import DTAndroid
from . import DTBinary
from . import DTMac
from . import DTUtils


def libBaseName(lib):
    basename = os.path.basename(lib)

    return basename[3: len(basename) - 3]

def fixLibsXml(globs, targetArch, dataDir):
    bundledInAssets = []
    assetsDir = os.path.join(dataDir, 'assets')

    for root, dirs, files in os.walk(assetsDir):
        for f in files:
            srcPath = os.path.join(root.replace(assetsDir, '')[1:], f)
            dstPath = os.path.sep.join(srcPath.split(os.path.sep)[1:])

            if (len(dstPath) > 0):
                bundledInAssets += [(srcPath, dstPath)]

    libsXml = os.path.join(dataDir, 'res', 'values', 'libs.xml')

    if not os.path.exists(libsXml):
        return

    libsXmlTemp = os.path.join(dataDir, 'res', 'values', 'libsTemp.xml')

    tree = ET.parse(libsXml)
    root = tree.getroot()
    oldFeatures = set()
    oldPermissions = set()
    resources = {}

    for element in root:
        if element.tag == 'array':
            if not element.attrib['name'] in resources:
                resources[element.attrib['name']] = set()

            for item in element:
                if item.text:
                    lib = item.text.strip()

                    if len(lib) > 0:
                        lib = '<item>{}</item>'.format(lib)
                        resources[element.attrib['name']].add(lib)
        elif element.tag == 'string':
            resources[element.attrib['name']] = element.text.strip() if element.text != None else ''

    libs = []

    if 'libs' in globs:
        libs = globs['libs']

    qtLibs = set(['<item>{};{}</item>'.format(targetArch, libBaseName(lib)) for lib in libs])

    if 'qt_libs' in resources:
        qtLibs -= resources['qt_libs']

    qtLibs = '\n'.join(sorted(list(qtLibs)))
    bundledInLib = []

    if 'bundledInLib' in globs:
        bundledInLib = globs['bundledInLib']

    bundledInLib = set(['<item>{}:{}</item>'.format(lib[0], lib[1]) for lib in bundledInLib])

    if 'bundled_in_lib' in resources:
        bundledInLib -= resources['bundled_in_lib']

    bundledInLib = '\n'.join(sorted(list(bundledInLib)))
    bundledInAssets = set(['<item>{}:{}</item>'.format(lib[0], lib[1]) for lib in bundledInAssets])

    if 'bundled_in_assets' in resources:
        bundledInAssets -= resources['bundled_in_assets']

    bundledInAssets = '\n'.join(sorted(list(bundledInAssets)))
    localLibs = []

    if 'localLibs' in globs:
        localLibs = sorted(list(globs['localLibs']))

    localLibs = {'<item>{};{}</item>'.format(targetArch, ':'.join(localLibs))}

    if 'load_local_libs' in resources:
        localLibs -= resources['load_local_libs']

    localLibs = '\n'.join(sorted(list(localLibs)))
    staticInitClasses = ''

    if 'static_init_classes' in resources:
        staticInitClasses = resources['static_init_classes']

    useLocalQtLibs = '1'

    if 'use_local_qt_libs' in resources:
        useLocalQtLibs = resources['use_local_qt_libs']

        if useLocalQtLibs != '0':
            useLocalQtLibs = '1'

    bundleLocalQtLibs = '1'

    if 'bundle_local_qt_libs' in resources:
        bundleLocalQtLibs = resources['bundle_local_qt_libs']

        if bundleLocalQtLibs != '0':
            bundleLocalQtLibs = '1'

    systemLibsPrefix = ''

    if 'system_libs_prefix' in resources:
        systemLibsPrefix = resources['system_libs_prefix'].strip()

    replace = {'<!-- %%INSERT_EXTRA_LIBS%% -->'       : '',
               '<!-- %%INSERT_QT_LIBS%% -->'          : qtLibs,
               '<!-- %%INSERT_BUNDLED_IN_LIB%% -->'   : bundledInLib,
               '<!-- %%INSERT_BUNDLED_IN_ASSETS%% -->': bundledInAssets,
               '<!-- %%INSERT_LOCAL_LIBS%% -->'       : localLibs,
               '<!-- %%INSERT_INIT_CLASSES%% -->'     : staticInitClasses,
               '<!-- %%USE_LOCAL_QT_LIBS%% -->'       : useLocalQtLibs,
               '<!-- %%BUNDLE_LOCAL_QT_LIBS%% -->'    : bundleLocalQtLibs,
               '<!-- %%SYSTEM_LIBS_PREFIX%% -->'      : systemLibsPrefix}

    with open(libsXml) as inFile:
        with open(libsXmlTemp, 'w') as outFile:
            for line in inFile:
                for key in replace:
                    line = line.replace(key, replace[key])

                outFile.write(line)

    os.remove(libsXml)
    libsXml = os.path.join(dataDir, 'res', 'values', 'libs-{}.xml'.format(targetArch))
    shutil.move(libsXmlTemp, libsXml)

def readXmlLibs(libsXml):
    tree = ET.parse(libsXml)

    libs = {
        'qt_sources': set([item.text for item in tree.findall("array[@name='qt_sources']/item")]),
        'bundled_libs': set([item.text for item in tree.findall("array[@name='bundled_libs']/item")]),
        'qt_libs': set([item.text for item in tree.findall("array[@name='qt_libs']/item")]),
        'load_local_libs': set([item.text for item in tree.findall("array[@name='load_local_libs']/item")]),
        'static_init_classes': set([item.text for item in tree.findall("string[@name='static_init_classes']")]),
        'use_local_qt_libs': set([item.text for item in tree.findall("string[@name='use_local_qt_libs']")]),
        'bundle_local_qt_libs': set([item.text for item in tree.findall("string[@name='bundle_local_qt_libs']")]),
        'system_libs_prefix': set([item.text for item in tree.findall("string[@name='system_libs_prefix']")])
    }

    return libs

def mergeXmlLibs(libsXmlDir, keep=False):
    if not os.path.exists(libsXmlDir):
        return

    libs = {}
    deleteFiles = []

    for f in os.listdir(libsXmlDir):
        xmlPath = os.path.join(libsXmlDir, f)

        if os.path.isfile(xmlPath) and re.match('^libs-.+\\.xml$', f):
            items = readXmlLibs(xmlPath)

            for key in items:
                if key in libs:
                    libs[key].update(items[key])
                else:
                    libs[key] = items[key]

            if not keep:
                deleteFiles.append(xmlPath)

    strings = ['static_init_classes',
               'use_local_qt_libs',
               'bundle_local_qt_libs',
               'system_libs_prefix']

    with open(os.path.join(libsXmlDir, 'libs.xml'), 'w') as outFile:
        outFile.write('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n')
        outFile.write('<resources>\n')

        if not 'qt_sources' in libs:
            outFile.write('    <array name="qt_sources">\n')
            outFile.write('    </array>\n')

        for key in libs:
            if key in strings:
                value = libs[key]

                if len(value) > 0:
                    value = list(value)[0] if list(value)[0] != None else ''
                else:
                    value = ''

                outFile.write('    <string name="{}">{}</string>\n'.format(key, value))
            else:
                outFile.write('    <array name="{}">\n'.format(key))

                for item in sorted(list(libs[key])):
                    outFile.write('        <item>{}</item>\n'.format(item))

                outFile.write('    </array>\n')

        outFile.write('</resources>\n')

    for f in deleteFiles:
        try:
            os.remove(f)
        except:
            pass

def copyAndroidTemplates(dataDir,
                         qtVersion,
                         qtSourcesDir,
                         sdkBuildToolsRevision,
                         minSdkVersion,
                         targetSdkVersion,
                         ndkABIFilters,
                         gradleParallel,
                         gradleDaemon,
                         gradleConfigureOnDemand):
    templates = [os.path.join(qtSourcesDir, '3rdparty/gradle'),
                 os.path.join(qtSourcesDir, 'android/templates')]

    for template in templates:
        for root, dirs, files in os.walk(template):
            for f in files:
                src = os.path.join(root, f)
                dst = os.path.join(dataDir, f)
                print('{} -> {}'.format(src, dst))

        DTUtils.copy(template, dataDir, overwrite=False)

    androidNDK = ''

    if 'ANDROID_NDK_ROOT' in os.environ:
        androidNDK = os.environ['ANDROID_NDK_ROOT']
    elif 'ANDROID_NDK_ROOT' in os.environ:
        androidNDK = os.environ['ANDROID_NDK_ROOT']

    ndkInfoFile = os.path.join(androidNDK, 'source.properties')
    androidNdkVersion = ''

    try:
        with open(ndkInfoFile) as ndkf:
            for line in ndkf:
                if 'Pkg.Revision' in line:
                    androidNdkVersion = line.split('=')[1].strip()
    except:
        pass

    properties = os.path.join(dataDir, 'gradle.properties')
    javaDir = os.path.join(qtSourcesDir, 'android', 'java')

    with open(properties, 'w') as f:
        f.write('android.useAndroidX=false\n')
        f.write('org.gradle.parallel={}\n'.format('true' if gradleParallel else 'false'))
        f.write('org.gradle.daemon={}\n'.format('true' if gradleDaemon else 'false'))
        f.write('org.gradle.configureondemand={}\n'.format('true' if gradleConfigureOnDemand else 'false'))
        f.write('org.gradle.configuration-cache=true\n')
        f.write('org.gradle.caching=true\n')
        f.write('org.gradle.jvmargs=-Xmx2048M\n')

        if len(sdkBuildToolsRevision) > 0:
            f.write('androidBuildToolsVersion={}\n'.format(sdkBuildToolsRevision))

        f.write('androidCompileSdkVersion=android-{}\n'.format(minSdkVersion))
        f.write('minSdkVersion=android-{}\n'.format(minSdkVersion))
        f.write('androidNdkVersion={}\n'.format(androidNdkVersion))
        f.write('qtMinSdkVersion={}\n'.format(minSdkVersion))
        f.write('qtTargetSdkVersion={}\n'.format(targetSdkVersion))
        f.write('qtTargetAbiList={}\n'.format(ndkABIFilters))
        f.write('buildDir=build\n')
        f.write('qt{}AndroidDir={}\n'.format(qtVersion, javaDir))
        f.write('qtAndroidDir={}\n'.format(javaDir))

    if minSdkVersion < 31:
        buildGradle = os.path.join(dataDir, 'build.gradle')

        if os.path.exists(buildGradle):
            lines = []

            with open(buildGradle, 'r') as f:
                for line in f:
                    if not "implementation 'androidx.core:" in line:
                        lines.append(line)

            with open(buildGradle, 'w') as f:
                for line in lines:
                    f.write(line)

def solvedepsAndroid(globs,
                     dataDir,
                     libDir,
                     sysLibDir,
                     appName,
                     appLibName,
                     version,
                     minSdkVersion,
                     targetSdkVersion,
                     qmakeExecutable):
    jars = set()
    permissions = set()
    features = set()
    initClasses = set()
    libs = set()

    for f in os.listdir(libDir):
        basename = os.path.basename(f)[3:]
        basename = os.path.splitext(basename)[0]

        if not basename.startswith('Qt'):
            continue

        for ldir in sysLibDir:
            depFile = os.path.join(ldir,
                                   basename + '-android-dependencies.xml')

            if os.path.exists(depFile):
                tree = ET.parse(depFile)
                root = tree.getroot()

                for jar in root.iter('jar'):
                    jars.add(jar.attrib['file'])

                    if 'initClass' in jar.attrib:
                        initClasses.add(jar.attrib['initClass'])

                for permission in root.iter('permission'):
                    permissions.add(permission.attrib['name'])

                for feature in root.iter('feature'):
                    features.add(feature.attrib['name'])

                for lib in root.iter('lib'):
                    if 'file' in lib.attrib:
                        libs.add(lib.attrib['file'])


    if not 'localLibs' in globs:
        globs['localLibs'] = set()

    for lib in libs:
        globs['localLibs'].add(os.path.basename(lib))

    print('Copying jar files')
    qtInstallPrefx = qmakeQuery('QT_INSTALL_PREFIX', qmakeExecutable)
    outJarsDir = os.path.join(dataDir, 'libs')
    print()
    print('From: ', os.path.join(qtInstallPrefx, 'jar'))
    print('To: ', outJarsDir)
    print()

    for jar in sorted(list(jars)):
        srcPath = os.path.join(qtInstallPrefx, jar)

        if os.path.exists(srcPath):
            dstPath = os.path.join(outJarsDir,
                                   os.path.basename(jar))
            print('    {} -> {}'.format(srcPath, dstPath))
            DTUtils.copy(srcPath, dstPath)

    manifest = os.path.join(dataDir, 'AndroidManifest.xml')
    manifestTemp = os.path.join(dataDir, 'AndroidManifestTemp.xml')
    tree = ET.parse(manifest)
    root = tree.getroot()
    oldFeatures = set()
    oldPermissions = set()

    for element in root:
        if element.tag == 'uses-feature':
            for key in element.attrib:
                if key.endswith('name'):
                    oldFeatures.add(element.attrib[key])
        elif element.tag == 'uses-permission':
            for key in element.attrib:
                if key.endswith('name'):
                    oldPermissions.add(element.attrib[key])

    features -= oldFeatures
    permissions -= oldPermissions
    featuresWritten = len(features) < 1
    permissionsWritten = len(permissions) < 1
    replace = {'-- %%INSERT_APP_NAME%% --'     : appName,
               '-- %%INSERT_APP_LIB_NAME%% --' : appLibName,
               '-- %%INSERT_VERSION_NAME%% --' : version,
               '-- %%INSERT_VERSION_CODE%% --' : DTUtils.versionCode(version),
               '-- %%INSERT_INIT_CLASSES%% --' : ':'.join(sorted(initClasses)),
               '-- %%BUNDLE_LOCAL_QT_LIBS%% --': '1',
               '-- %%USE_LOCAL_QT_LIBS%% --'   : '1',
               '-- %%INSERT_LOCAL_LIBS%% --'   : ':'.join(sorted(libs)),
               '-- %%INSERT_LOCAL_JARS%% --'   : ':'.join(sorted(jars))}

    with open(manifest) as inFile:
        with open(manifestTemp, 'w') as outFile:
            for line in inFile:
                for key in replace:
                    line = line.replace(key, replace[key])

                if not 'android.app.ministro_not_found_msg' in line \
                   and not 'android.app.ministro_needed_msg' in line:
                    outFile.write(line)

                spaces = len(line)
                line = line.lstrip()
                spaces -= len(line)

                if line.startswith('<uses-feature') and not featuresWritten:
                    print('\nUpdating features\n')

                    for feature in features:
                        print('    ' + feature)
                        outFile.write(spaces * ' ' + '<uses-feature android:name="{}"/>\n'.format(feature))

                    featuresWritten = True

                if line.startswith('<uses-permission') and not permissionsWritten:
                    print('\nUpdating permissions\n')

                    for permission in permissions:
                        print('    ' + permission)
                        outFile.write(spaces * ' ' + '<uses-permission android:name="{}"/>\n'.format(permission))

                    permissionsWritten = True

    os.remove(manifest)
    shutil.move(manifestTemp, manifest)

    if minSdkVersion >= 30:
        tree = ET.parse(manifest)
        ET.register_namespace('android', "http://schemas.android.com/apk/res/android")
        root = tree.getroot()

        application = root.find('application')

        if application != None:
            application.set('requestLegacyExternalStorage', 'true')
            application.set('allowNativeHeapPointerTagging', 'false')

            with open('person.xml', 'wb') as f:
                tree.write(manifest)

def createRccBundle(outputAssetsDir, verbose):
    outputAssetsDir = os.path.join(outputAssetsDir, 'android_rcc_bundle')

    if not os.path.exists(outputAssetsDir):
        return

    assetsDir = os.path.abspath(os.path.join(outputAssetsDir, '..'))
    assetsFolder = os.path.relpath(outputAssetsDir, assetsDir)
    qrcFile = os.path.join(outputAssetsDir, assetsFolder + '.qrc')

    params = ['rcc',
              '--verbose',
              '--project',
              '-o', qrcFile]

    if verbose:
        process = subprocess.Popen(params, # nosec
                                   cwd=outputAssetsDir)
    else:
        process = subprocess.Popen(params, # nosec
                                   cwd=outputAssetsDir,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    params = ['rcc',
              '--verbose',
              '--root=/{}'.format(assetsFolder),
              '--binary',
              '-o', outputAssetsDir + '.rcc',
              qrcFile]

    if verbose:
        process = subprocess.Popen(params, # nosec
                                   cwd=assetsDir)
    else:
        process = subprocess.Popen(params, # nosec
                                   cwd=assetsDir,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    shutil.rmtree(outputAssetsDir, True)

def fixQtLibs(globs, libDir, outputQtPluginsDir, outputAssetsDir):
    if not 'bundledInLib' in globs:
        globs['bundledInLib'] = set()

    rccDir = os.path.abspath(os.path.join(outputQtPluginsDir, '..'))

    for root, dirs, files in os.walk(outputAssetsDir):
        for f in files:
            if f.endswith('.so'):
                srcPath = os.path.join(root, f)
                relPath = os.path.relpath(root, rccDir)
                prefix = 'lib' + relPath.replace(os.path.sep, '_') + '_'
                lib = ''

                if f.startswith(prefix):
                    lib = f
                else:
                    lib = prefix + f

                dstPath = os.path.join(libDir, lib)
                print('    {} -> {}'.format(srcPath, dstPath))
                DTUtils.move(srcPath, dstPath)
                globs['bundledInLib'].add((lib, os.path.join(relPath, f)))

    try:
        shutil.rmtree(outputQtPluginsDir)
    except:
        pass

def qmakeQuery(var='', qmakeExecutable='qmake'):
    try:
        args = [qmakeExecutable, '-query']

        if var != '':
            args += [var]

        process = subprocess.Popen(args, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        return stdout.strip().decode(sys.getdefaultencoding())
    except:
        pass

    return ''

def modulePath(importLine):
    if len(importLine) < 1:
        return ''

    if not importLine.startswith('import ') \
          and not importLine.startswith('depends '):
        importLine = 'import ' + importLine

    imp = importLine.strip().split()
    path = imp[1].replace('.', '/')

    if len(imp) > 2:
        majorVersion = imp[2].split('.')[0]

        try:
            if int(majorVersion) > 1:
                path += '.{}'.format(majorVersion)
        except:
            pass

    return path

def scanImports(path):
    if not os.path.isfile(path):
        return []

    fileName = os.path.basename(path)
    imports = set()

    if fileName.endswith('.qml'):
        with open(path, 'rb') as f:
            for line in f:
                if re.match(b'^import \\w+' , line):
                    imports.add(modulePath(line.strip().decode(sys.getdefaultencoding())))
    elif fileName == 'qmldir':
        with open(path, 'rb') as f:
            for line in f:
                if re.match(b'^depends ' , line):
                    imports.add(modulePath(line.strip().decode(sys.getdefaultencoding())))

    return list(imports)

def listQmlFiles(path):
    qmlFiles = set()

    if os.path.isfile(path):
        baseName = os.path.basename(path)

        if baseName == 'qmldir' or path.endswith('.qml'):
            qmlFiles.add(path)
    else:
        for root, _, files in os.walk(path):
            for f in files:
                if f == 'qmldir' or f.endswith('.qml'):
                    qmlFiles.add(os.path.join(root, f))

    return list(qmlFiles)

def solvedepsQml(globs,
                 sourcesDir,
                 sourcesQmlDirs,
                 outputQmlDir,
                 qtQmlDir,
                 qtExtraQmlImports):
    qmlFiles = set()

    for path in sourcesQmlDirs:
        path = os.path.join(sourcesDir, path)

        for f in listQmlFiles(path):
            qmlFiles.add(f)

    solved = set()
    solvedImports = set()

    if not 'dependencies' in globs:
        globs['dependencies'] = set()

    for module in qtExtraQmlImports:
        imp = modulePath(module)
        sysModulePath = os.path.join(qtQmlDir, imp)
        installModulePath = os.path.join(outputQmlDir, imp)

        if os.path.exists(sysModulePath):
            print('    {} -> {}'.format(sysModulePath, installModulePath))
            DTUtils.copy(sysModulePath, installModulePath)
            solvedImports.add(imp)
            globs['dependencies'].add(os.path.join(sysModulePath, 'qmldir'))

            for f in listQmlFiles(sysModulePath):
                if not f in solved:
                    qmlFiles.add(f)

    while len(qmlFiles) > 0:
        qmlFile = qmlFiles.pop()

        for imp in scanImports(qmlFile):
            if imp in solvedImports:
                continue

            sysModulePath = os.path.join(qtQmlDir, imp)
            installModulePath = os.path.join(outputQmlDir, imp)

            if os.path.exists(sysModulePath):
                print('    {} -> {}'.format(sysModulePath, installModulePath))
                DTUtils.copy(sysModulePath, installModulePath)
                solvedImports.add(imp)
                globs['dependencies'].add(os.path.join(sysModulePath, 'qmldir'))

                for f in listQmlFiles(sysModulePath):
                    if not f in solved:
                        qmlFiles.add(f)

        solved.add(qmlFile)

def solvedepsPlugins(globs,
                     configs,
                     mainExecutable,
                     targetPlatform,
                     targetArch,
                     debug,
                     dataDir,
                     qtVersion,
                     outputQtPluginsDir,
                     qtPluginsDir,
                     qtExtraPlugins,
                     libDir,
                     sysLibDir,
                     stripCmd='strip'):
    pluginsMap = {
        'Qt{}3DRenderer'.format(qtVersion): ['sceneparsers',
                                             'renderers',
                                             'renderplugins',
                                             'geometryloaders'],
        'Qt{}3DQuickRenderer'.format(qtVersion): ['renderplugins'],
        'Qt{}Declarative'.format(qtVersion): ['qml1tooling'],
        'Qt{}EglFSDeviceIntegration'.format(qtVersion): ['egldeviceintegrations'],
        'Qt{}GamePad'.format(qtVersion): ['gamepads'],
        'Qt{}Gui'.format(qtVersion): ['accessible',
                                      'generic',
                                      'iconengines',
                                      'imageformats',
                                      'platforms',
                                      'platforminputcontexts',
                                      'styles',
                                      'virtualkeyboard'
                                      'xcbglintegrations'],
        'Qt{}Location'.format(qtVersion): ['geoservices'],
        'Qt{}Multimedia'.format(qtVersion): ['audio',
                                             'mediaservice',
                                             'multimedia',
                                             'playlistformats'],
        'Qt{}Network'.format(qtVersion): ['bearer',
                                          'networkaccess',
                                          'networkinformation',
                                          'tls'],
        'Qt{}Positioning'.format(qtVersion): ['position'],
        'Qt{}PrintSupport'.format(qtVersion): ['printsupport'],
        'Qt{}QmlTooling'.format(qtVersion): ['qmltooling'],
        'Qt{}Quick'.format(qtVersion): ['scenegraph', 'qmltooling'],
        'Qt{}Sensors'.format(qtVersion): ['sensors', 'sensorgestures'],
        'Qt{}SerialBus'.format(qtVersion): ['canbus'],
        'Qt{}ShaderTools'.format(qtVersion): ['renderers'],
        'Qt{}Sql'.format(qtVersion): ['sqldrivers'],
        'Qt{}TextToSpeech'.format(qtVersion): ['texttospeech'],
        'Qt{}WaylandClient'.format(qtVersion): ['wayland-decoration-client',
                                                'wayland-graphics-integration-client',
                                                'wayland-graphics-integration-server',
                                                'wayland-shell-integration'],
        'Qt{}WebEngine'.format(qtVersion): ['qtwebengine'],
        'Qt{}WebEngineCore'.format(qtVersion): ['qtwebengine'],
        'Qt{}WebEngineWidgets'.format(qtVersion): ['qtwebengine'],
        'Qt{}WebView'.format(qtVersion): ['webview'],
        'Qt{}Widgets'.format(qtVersion): ['styles'],
    }

    pluginsMap.update({lib + 'd': pluginsMap[lib] for lib in pluginsMap})
    pluginsMap.update({lib.replace('Qt{}'.format(qtVersion), 'Qt'): pluginsMap[lib] for lib in pluginsMap})

    if targetPlatform == 'android':
        pluginsMap.update({lib + '_' + targetArch: pluginsMap[lib] for lib in pluginsMap})
    elif targetPlatform == 'mac':
        pluginsMap.update({lib + '.framework': pluginsMap[lib] for lib in pluginsMap})

    if not 'dependencies' in globs:
        globs['dependencies'] = set()

    solver = DTBinary.BinaryTools(configs,
                                  DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  debug,
                                  sysLibDir,
                                  stripCmd)
    plugins = []

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep, configs)

        if not libName in pluginsMap:
            continue

        # QtMultimediaQuick seems to be a dynamically loaded library so copy it
        # to the library directory.
        if targetPlatform == 'mac' and re.match('.*Qt[0-9]*Multimedia\\.framework', libName) \
            and not 'MultimediaQuick' in libName:
                if os.path.exists(dep):
                    multimediaQuickLibName = \
                        libName.replace('Multimedia', 'MultimediaQuick')
                    multimediaQuickLib = \
                        dep.replace(libName, multimediaQuickLibName)
                    dst = os.path.join(libDir, os.path.basename(multimediaQuickLib))

                    print('    {} -> {}'.format(multimediaQuickLib, dst))
                    DTMac.copyBundle(multimediaQuickLib, dst)
        elif re.match('.*Qt[0-9]*Multimedia' , libName) \
            and not 'MultimediaQuick' in libName:
                if os.path.exists(dep):
                    multimediaQuickLibName = \
                        libName.replace('Multimedia', 'MultimediaQuick')
                    multimediaQuickLib = \
                        dep.replace(libName, multimediaQuickLibName)
                    dst = ''

                    if targetPlatform == 'windows':
                        binDir = os.path.dirname(mainExecutable)
                        dst = os.path.join(binDir, os.path.basename(multimediaQuickLib))
                    else:
                        dst = os.path.join(libDir, os.path.basename(multimediaQuickLib))

                    print('    {} -> {}'.format(multimediaQuickLib, dst))
                    DTUtils.copy(multimediaQuickLib, dst)

        for plugin in pluginsMap[libName]:
            if not plugin in plugins:
                sysPluginPath = os.path.join(qtPluginsDir, plugin)
                pluginPath = os.path.join(outputQtPluginsDir, plugin)

                if not os.path.exists(sysPluginPath):
                    continue

                print('    {} -> {}'.format(sysPluginPath, pluginPath))
                DTUtils.copy(sysPluginPath, pluginPath)
                plugins.append(plugin)
                globs['dependencies'].add(sysPluginPath)

    for plugin in qtExtraPlugins:
        if not plugin in plugins:
            sysPluginPath = os.path.join(qtPluginsDir, plugin)
            pluginPath = os.path.join(outputQtPluginsDir, plugin)

            if not os.path.exists(sysPluginPath):
                continue

            print('    {} -> {}'.format(sysPluginPath, pluginPath))
            DTUtils.copy(sysPluginPath, pluginPath)
            plugins.append(plugin)
            globs['dependencies'].add(sysPluginPath)

def removeDebugs(dataDir, qmakeExecutable):
    dbgFiles = set()
    libQtInstallDir = \
        qmakeQuery('QT_INSTALL_ARCHDATA', qmakeExecutable) \
            .replace(qmakeQuery('QT_INSTALL_PREFIX', qmakeExecutable), dataDir)

    for root, _, files in os.walk(libQtInstallDir):
        for f in files:
            if f.endswith('.dll'):
                fname, ext = os.path.splitext(f)
                dbgFile = os.path.join(root, '{}d{}'.format(fname, ext))

                if os.path.exists(dbgFile):
                    dbgFiles.add(dbgFile)

    for f in dbgFiles:
        os.remove(f)

def removeInvalidAndroidArchs(targetArch, assetsDir):
    suffix = '_{}.so'.format(targetArch)

    for root, dirs, files in os.walk(assetsDir):
        for f in files:
            if f.endswith('.so') and not f.endswith(suffix):
                os.remove(os.path.join(root, f))

def writeQtConf(qtConfFile,
                mainExecutable,
                targetPlatform,
                outputQmlDir,
                outputQtPluginsDir):
    prefix = os.path.dirname(mainExecutable)

    if targetPlatform == 'mac':
        prefix = os.path.abspath(os.path.join(prefix, '..'))

    paths = {'Plugins': os.path.relpath(outputQtPluginsDir, prefix).replace('\\', '/'),
             'Imports': os.path.relpath(outputQmlDir, prefix).replace('\\', '/'),
             'Qml2Imports': os.path.relpath(outputQmlDir, prefix).replace('\\', '/')}
    confPath = os.path.dirname(qtConfFile)

    if not os.path.exists(confPath):
        os.makedirs(confPath)

    with open(qtConfFile, 'w') as qtconf:
        qtconf.write('[Paths]\n')
        print('[Paths]')

        for path in paths:
            qtconf.write('{} = {}\n'.format(path, paths[path]))
            print('{} = {}'.format(path, paths[path]))

def preRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    debug =  configs.get('Package', 'debug', fallback='false').strip()
    debug = DTUtils.toBool(debug)
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    qtVersion = configs.get('Qt', 'version', fallback='6').strip()

    try:
        qtVersion = int(qtVersion)
    except:
        qtVersion = 6

    qmakeExecutable = configs.get('Qt', 'qmakeExecutable', fallback='qmake').strip()
    libDir = os.path.join(dataDir, libDir)
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    qtSourcesQmlDirs = configs.get('Qt', 'sourcesQmlDirs', fallback='').strip()
    sourcesQmlDirs = set()

    for qmlDir in qtSourcesQmlDirs.split(','):
        qmlDir = qmlDir.strip()

        if len(qmlDir) > 0:
            sourcesQmlDirs.add(qmlDir.strip())

    sourcesQmlDirs = list(sourcesQmlDirs)
    outputQmlDir = configs.get('Qt', 'outputQmlDir', fallback='qml').strip()
    outputQmlDir = os.path.join(dataDir, outputQmlDir)
    defaultQtQmlDir = qmakeQuery('QT_INSTALL_QML', qmakeExecutable)
    qtQmlDir = configs.get('Qt', 'qtQmlDir', fallback=defaultQtQmlDir).strip()
    outputQtPluginsDir = configs.get('Qt', 'outputQtPluginsDir', fallback='plugins').strip()
    outputQtPluginsDir = os.path.join(dataDir, outputQtPluginsDir)
    defaultQtPluginsDir = qmakeQuery('QT_INSTALL_PLUGINS', qmakeExecutable)
    qtPluginsDir = configs.get('Qt', 'qtPluginsDir', fallback=defaultQtPluginsDir).strip()
    outputAssetsDir = configs.get('Android', 'outputAssetsDir', fallback='assets').strip()
    outputAssetsDir = os.path.join(dataDir, outputAssetsDir)
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    qtConfFile = configs.get('Qt', 'qtConfFile', fallback='qt.conf').strip()
    qtConfFile = os.path.join(dataDir, qtConfFile)
    qtExtraQmlImports = configs.get('Qt', 'extraQmlImports', fallback='').strip()
    extraQmlImports = set()

    for module in qtExtraQmlImports.split(','):
        module = module.strip()

        if len(module) > 0:
            extraQmlImports.add(module.strip())

    qtExtraQmlImports = list(extraQmlImports)
    qtExtraPlugins = configs.get('Qt', 'extraPlugins', fallback='').strip()
    extraPlugins = set()

    for plugin in qtExtraPlugins.split(','):
        plugin = plugin.strip()

        if len(plugin) > 0:
            extraPlugins.add(plugin.strip())

    qtExtraPlugins = list(extraPlugins)

    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()
    ndkABIFilters = configs.get('Android', 'ndkABIFilters', fallback=targetArch).strip()

    if len(ndkABIFilters) < 1:
        ndkABIFilters = targetArch

    gradleParallel = configs.get('AndroidAPK', 'gradleParallel', fallback='false').strip()
    gradleParallel = DTUtils.toBool(gradleParallel)
    gradleDaemon = configs.get('AndroidAPK', 'gradleDaemon', fallback='false').strip()
    gradleDaemon = DTUtils.toBool(gradleDaemon)
    gradleConfigureOnDemand = configs.get('AndroidAPK', 'gradleConfigureOnDemand', fallback='false').strip()
    gradleConfigureOnDemand = DTUtils.toBool(gradleConfigureOnDemand)

    print('Qt information')
    print()
    print('Qml sources directory: {}'.format(sourcesQmlDirs))
    print('Qt plugins directory: {}'.format(qtPluginsDir))
    print('Qt plugins output directory: {}'.format(outputQtPluginsDir))
    print('Qt Qml files directory: {}'.format(qtQmlDir))
    print('Qt Qml files output directory: {}'.format(outputQmlDir))
    print('Qt qmake executable: {}'.format(qmakeExecutable))
    qtSourcesDir = ''

    if targetPlatform == 'android':
        qtSourcesDir = configs.get('Qt', 'sourcesDir', fallback='').strip()
        print('Qt sources directory: {}'.format(qtSourcesDir))

    print()
    print('Copying Qml modules')
    print()
    solvedepsQml(globs,
                 sourcesDir,
                 sourcesQmlDirs,
                 outputQmlDir,
                 qtQmlDir,
                 qtExtraQmlImports)
    print()
    print('Copying required plugins')
    print()
    solvedepsPlugins(globs,
                     configs,
                     mainExecutable,
                     targetPlatform,
                     targetArch,
                     debug,
                     dataDir,
                     qtVersion,
                     outputQtPluginsDir,
                     qtPluginsDir,
                     qtExtraPlugins,
                     libDir,
                     sysLibDir,
                     stripCmd)
    print()

    if targetPlatform == 'windows':
        print('Removing Qt debug libraries')
        removeDebugs(dataDir, qmakeExecutable)
    elif targetPlatform == 'android':
        assetsDir = configs.get('Package', 'assetsDir', fallback='assets').strip()
        assetsDir = os.path.join(dataDir, assetsDir)
        sdkBuildToolsRevision = DTAndroid.buildToolsVersion(configs)
        minSdkVersion = DTAndroid.readMinimumSdkVersion(configs)
        targetSdkVersion = DTAndroid.readTargetSdkVersion(configs)

        print('Removing unused architectures')
        removeInvalidAndroidArchs(targetArch, assetsDir)
        print('Fixing Android libs')
        print()
        fixQtLibs(globs, libDir, outputQtPluginsDir, outputAssetsDir)
        print()
        print('Copying Android build templates')
        print()
        copyAndroidTemplates(dataDir,
                             qtVersion,
                             qtSourcesDir,
                             sdkBuildToolsRevision,
                             minSdkVersion,
                             targetSdkVersion,
                             ndkABIFilters,
                             gradleParallel,
                             gradleDaemon,
                             gradleConfigureOnDemand)

    if targetPlatform != 'android':
        print('Writting qt.conf file')
        print()
        writeQtConf(qtConfFile,
                    mainExecutable,
                    targetPlatform,
                    outputQmlDir,
                    outputQtPluginsDir)

    print()

    if not 'environment' in globs:
        globs['environment'] = set()

    if targetPlatform == 'windows':
        globs['environment'].add(('QT_OPENGL', 'angle', 'Default values: desktop | angle | software', True))
        globs['environment'].add(('QT_ANGLE_PLATFORM', 'd3d11', 'Default values: d3d11 | d3d9 | warp', True))
        globs['environment'].add(('QT_QUICK_BACKEND', '', 'Default values: software | d3d12 | openvg', True))

    globs['environment'].add(('QT_DEBUG_PLUGINS', 1, 'Enable plugin debugging', True))
    globs['environment'].add(('QT_LOGGING_RULES', '"*.debug=true"', 'Enable logging', True))

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    appLibName = configs.get('Android', 'appLibName', fallback=name).strip()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    verbose = configs.get('Qt', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    qtVersion = configs.get('Qt', 'version', fallback='6').strip()

    try:
        qtVersion = int(qtVersion)
    except:
        qtVersion = 6

    qmakeExecutable = configs.get('Qt', 'qmakeExecutable', fallback='qmake').strip()
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        lib = lib.strip()

        if len(lib) > 0:
            libs.add(lib.strip())

    sysLibDir = list(libs)
    outputAssetsDir = configs.get('Android', 'outputAssetsDir', fallback='assets').strip()
    outputAssetsDir = os.path.join(dataDir, outputAssetsDir)

    if targetPlatform == 'android':
        minSdkVersion = configs.get('Android', 'minSdkVersion', fallback='24').strip()

        try:
            minSdkVersion = int(minSdkVersion)
        except:
            minSdkVersion = 0

        targetSdkVersion = configs.get('Android', 'targetSdkVersion', fallback='24').strip()

        try:
            targetSdkVersion = int(targetSdkVersion)
        except:
            targetSdkVersion = 0

        print('Solving Android dependencies')
        solvedepsAndroid(globs,
                         dataDir,
                         libDir,
                         sysLibDir,
                         name,
                         appLibName,
                         version,
                         minSdkVersion,
                         targetSdkVersion,
                         qmakeExecutable)
        print()
        print('Fixing libs.xml file')
        fixLibsXml(globs, targetArch, dataDir)
        print('Creating .rcc bundle file')
        createRccBundle(outputAssetsDir, verbose)
        print()
