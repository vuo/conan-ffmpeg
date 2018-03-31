from conans import AutoToolsBuildEnvironment, ConanFile, tools
import os
import platform

class FfmpegConan(ConanFile):
    name = 'ffmpeg'

    source_version = '2.1'
    package_version = '2'
    version = '%s-%s' % (source_version, package_version)

    requires = 'llvm/3.3-2@vuo/stable', \
        'vuoutils/1.0@vuo/stable' \
        'openssl/1.0.2n-2@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://www.ffmpeg.org/'
    license = 'http://www.ffmpeg.org/legal.html'
    description = 'A cross-platform library for recording, converting, and streaming audio and video'
    source_dir = 'ffmpeg-%s' % source_version
    build_dir = '_build'
    libs = {
        'avcodec': 55,
        'avdevice': 55,
        'avfilter': 3,
        'avformat': 55,
        'avutil': 52,
        'swresample': 0,
        'swscale': 2,
    }

    def requirements(self):
        if platform.system() == 'Linux':
            self.requires('patchelf/0.9@vuo/stable')
        elif platform.system() != 'Darwin':
            raise Exception('Unknown platform "%s"' % platform.system())

    def source(self):
        tools.get('http://www.ffmpeg.org/releases/ffmpeg-%s.tar.bz2' % self.source_version,
                  sha256='926603fd974e9b38071a5cfc6fd0d93857801d1968145dfce7fdc627ab1d68df')

    def build(self):
        import VuoUtils
        tools.mkdir(self.build_dir)
        with tools.chdir(self.build_dir):
            autotools = AutoToolsBuildEnvironment(self)

            # The LLVM/Clang libs get automatically added by the `requires` line,
            # but this package doesn't need to link with them.
            autotools.libs = []

            autotools.flags.append('-Oz')
            autotools.flags.append('-arch x86_64')

            autotools.link_flags.append('-arch x86_64')

            if platform.system() == 'Darwin':
                autotools.flags.append('-mmacosx-version-min=10.10')
                autotools.link_flags.append('-Wl,-headerpad_max_install_names')
                autotools.link_flags.append('-Wl,-no_function_starts')
                autotools.link_flags.append('-Wl,-no_version_load_command')

            env_vars = {
                'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
                'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++',
            }
            with tools.environment_append(env_vars):
                autotools.configure(configure_dir='../%s' % self.source_dir,
                                    build=False,
                                    host=False,
                                    args=[
                                          '--disable-programs',
                                          '--disable-doc',
                                          '--enable-shared',
                                          '--disable-stripping',
                                          '--disable-static',
                                          '--enable-pthreads',
                                          '--enable-yasm',
                                          '--disable-debug',
                                          '--enable-demuxer=mpegts',
                                          '--enable-demuxer=mpegtsraw',
                                          '--disable-bsfs',
                                          '--disable-devices',
                                          '--enable-openssl',

                                          # Avoid CPU features unsupported on some systems Vuo runs on
                                          '--disable-runtime-cpudetect',
                                          '--disable-ssse3',
                                          '--disable-sse4',
                                          '--disable-sse42',
                                          '--disable-avx',

                                          # Avoid patent-encumbered codecs
                                          '--disable-decoder=aac',
                                          '--disable-decoder=aac_latm',
                                          '--disable-encoder=aac',
                                          '--disable-parser=aac',
                                          '--disable-parser=aac_latm',
                                          '--disable-demuxer=aac',
                                          '--disable-decoder=mp3',
                                          '--disable-decoder=mp3adu',
                                          '--disable-decoder=mp3adufloat',
                                          '--disable-decoder=mp3float',
                                          '--disable-decoder=mp3on4',
                                          '--disable-decoder=mp3on4float',
                                          '--disable-demuxer=mp3',
                                          '--disable-muxer=mp3',

                                          '--prefix=%s' % os.getcwd()])
                autotools.make(args=['--quiet'])
                autotools.make(target='install', args=['--quiet'])
            with tools.chdir('lib'):
                VuoUtils.fixLibs(self.libs, self.deps_cpp_info)

    def package(self):
        self.copy('*.h', src='%s/include' % self.build_dir, dst='include')

        if platform.system() == 'Darwin':
            libext = 'dylib'
        elif platform.system() == 'Linux':
            libext = 'so'
        else:
            raise Exception('Unknown platform "%s"' % platform.system())

        for f in list(self.libs.keys()):
            self.copy('lib%s.%s' % (f, libext), src='%s/lib' % self.build_dir, dst='lib')

    def package_info(self):
        self.cpp_info.libs = list(self.libs.keys())
