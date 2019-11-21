from conans import AutoToolsBuildEnvironment, ConanFile, tools
import os
import platform

class FfmpegConan(ConanFile):
    name = 'ffmpeg'

    source_version = '4.2.1'
    package_version = '0'
    version = '%s-%s' % (source_version, package_version)

    build_requires = 'llvm/3.3-5@vuo/stable', \
                     'vuoutils/1.0@vuo/stable'
    requires = 'openssl/1.1.1c-0@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://www.ffmpeg.org/'
    license = 'http://www.ffmpeg.org/legal.html'
    description = 'A cross-platform library for recording, converting, and streaming audio and video'
    source_dir = 'ffmpeg-%s' % source_version
    build_dir = '_build'
    libs = {
        'avcodec': 58,
        'avdevice': 58,
        'avfilter': 7,
        'avformat': 58,
        'avutil': 56,
        'swresample': 3,
        'swscale': 5,
    }
    exports_sources = '*.patch'

    def requirements(self):
        if platform.system() == 'Linux':
            self.requires('patchelf/0.10pre-1@vuo/stable')
        elif platform.system() != 'Darwin':
            raise Exception('Unknown platform "%s"' % platform.system())

    def source(self):
        tools.get('http://www.ffmpeg.org/releases/ffmpeg-%s.tar.bz2' % self.source_version,
                  sha256='682a9fa3f6864d7f0dbf224f86b129e337bc60286e0d00dffcd710998d521624')

        # On both Linux and macOS, tell ./configure to check for the presence of OPENSSL_init_ssl
        # (instead of the removed-in-openssl-1.1 SSL_library_init).
        if platform.system() == 'Linux':
            # Tell ./configure that it needs the dynamic linker in order to link with OpenSSL.
            # (`autotools.libs.append('dl')` doesn't work because it appears before the OpenSSL libraries on the ./configure command line.)
            tools.replace_in_file('%s/configure' % self.source_dir,
                                  '                               check_lib openssl openssl/ssl.h SSL_library_init -lssl -lcrypto ||',
                                  '                               check_lib openssl openssl/ssl.h OPENSSL_init_ssl -lssl -lcrypto -ldl -lpthread ||')
        else:
            tools.replace_in_file('%s/configure' % self.source_dir,
                                  '                               check_lib openssl openssl/ssl.h SSL_library_init -lssl -lcrypto ||',
                                  '                               check_lib openssl openssl/ssl.h OPENSSL_init_ssl -lssl -lcrypto ||')

        self.run('mv %s/LICENSE.md %s/%s.txt' % (self.source_dir, self.source_dir, self.name))

    def build(self):
        import VuoUtils
        tools.mkdir(self.build_dir)
        with tools.chdir(self.build_dir):
            autotools = AutoToolsBuildEnvironment(self)

            # The LLVM/Clang libs get automatically added by the `requires` line,
            # but this package doesn't need to link with them.
            autotools.libs = []

            autotools.flags.append('-I%s/include' % self.deps_cpp_info['openssl'].rootpath)
            autotools.link_flags.append('-L%s/lib' % self.deps_cpp_info['openssl'].rootpath)

            if platform.system() == 'Darwin':
                autotools.flags.append('-Oz')
                autotools.flags.append('-arch x86_64')
                autotools.flags.append('-isysroot /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk')
                autotools.flags.append('-mmacosx-version-min=10.10')
                autotools.link_flags.append('-arch x86_64')
                autotools.link_flags.append('-Wl,-headerpad_max_install_names')
            elif platform.system() == 'Linux':
                autotools.flags.append('-O4')

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
                                          '--enable-x86asm',
                                          '--disable-debug',
                                          '--enable-demuxer=mpegts',
                                          '--enable-demuxer=mpegtsraw',
                                          '--disable-bsfs',
                                          '--disable-devices',
                                          '--enable-openssl',

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

        self.copy('%s.txt' % self.name, src=self.source_dir, dst='license')

    def package_info(self):
        self.cpp_info.libs = list(self.libs.keys())
