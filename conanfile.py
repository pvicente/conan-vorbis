from conans import ConanFile, AutoToolsBuildEnvironment, VisualStudioBuildEnvironment, tools
from conans.tools import download, unzip, replace_in_file, build_sln_command, run_in_windows_bash, ConanException
import os


class VorbisConan(ConanFile):
    name = "vorbis"
    version = "1.3.5"
    sources_folder = "sources"
    generators = "txt"
    settings = "os", "arch", "build_type", "compiler"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"
    url="http://github.com/dimi309/conan-packages"
    description="The VORBIS library"
    requires = "ogg/1.3.3@bincrafters/stable"
    license="BSD"
    exports = "FindVORBIS.cmake"

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio":
            raise ConanException("On Windows, version 1.3.5 of the vorbis package only supports the Visual Studio compiler for the time being.")
            
        del self.settings.compiler.libcxx

        if self.settings.os == "Windows":
            self.options.remove("fPIC")

    def source(self):
        if self.settings.os == "Windows":
            zip_name ="v%s.zip" % self.version
        else:
            zip_name = "libvorbis-%s.zip" % self.version

        if self.settings.os == "Windows":
            download("https://github.com/xiph/vorbis/archive/%s" % zip_name, zip_name)
        else:
            download("http://downloads.xiph.org/releases/vorbis/%s" % zip_name, zip_name)

        unzip(zip_name)
        os.unlink(zip_name)
        if self.settings.os == "Windows":
            os.rename("%s-%s" % (self.name, self.version), self.sources_folder)
        else:
            os.rename("libvorbis-%s" % self.version, self.sources_folder)

    def build(self):
        if self.settings.compiler == "Visual Studio":
            
            env = VisualStudioBuildEnvironment(self)
            with tools.environment_append(env.vars):
            
                if self.options.shared:
                    vs_suffix = "_dynamic"
                else:
                    vs_suffix = "_static"

                libdirs="<AdditionalLibraryDirectories>"
                libdirs_ext="<AdditionalLibraryDirectories>$(LIB);"
                if self.options.shared:
                    replace_in_file("%s\\%s\\win32\\VS2010\\libvorbis\\libvorbis%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), libdirs, libdirs_ext)
                    replace_in_file("%s\\%s\\win32\\VS2010\\libvorbis\\libvorbis%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), "libogg.lib", "ogg.lib")
                if self.options.shared:
                    replace_in_file("%s\\%s\\win32\\VS2010\\libvorbisfile\\libvorbisfile%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), libdirs, libdirs_ext)
                    replace_in_file("%s\\%s\\win32\\VS2010\\libvorbisfile\\libvorbisfile%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix),  "libogg.lib", "ogg.lib")
                replace_in_file("%s\\%s\\win32\\VS2010\\vorbisdec\\vorbisdec%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), libdirs, libdirs_ext)
                
                if self.options.shared:
                    replace_in_file("%s\\%s\\win32\\VS2010\\vorbisdec\\vorbisdec%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), "libogg.lib", "ogg.lib")
                else:
                    replace_in_file("%s\\%s\\win32\\VS2010\\vorbisdec\\vorbisdec%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), "libogg_static.lib", "ogg.lib")
                    
                replace_in_file("%s\\%s\\win32\\VS2010\\vorbisenc\\vorbisenc%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), libdirs, libdirs_ext)
                if self.options.shared:
                    replace_in_file("%s\\%s\\win32\\VS2010\\vorbisenc\\vorbisenc%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), "libogg.lib", "ogg.lib")
                else:
                    replace_in_file("%s\\%s\\win32\\VS2010\\vorbisenc\\vorbisenc%s.vcxproj" %
                                (self.conanfile_directory, self.sources_folder, vs_suffix), "libogg_static.lib", "ogg.lib")

                vcvars = tools.vcvars_command(self.settings)
                cd_build = "cd %s\\%s\\win32\\VS2010" % (self.conanfile_directory, self.sources_folder)
                build_command = build_sln_command(self.settings, "vorbis%s.sln" % vs_suffix)
                self.run("%s && %s && %s" % (vcvars, cd_build, build_command.replace("x86", "Win32")))

        else:
            base_path = ("%s/" % self.conanfile_directory) if self.settings.os != "Windows" else ""
            cd_build = "cd %s%s" % (base_path, self.sources_folder)
            
            env = AutoToolsBuildEnvironment(self)

            if self.settings.os != "Windows":
                env.fpic = self.options.fPIC 

            with tools.environment_append(env.vars):

                if self.settings.os == "Macos":
                    old_str = '-install_name \\$rpath/\\$soname'
                    new_str = '-install_name \\$soname'
                    replace_in_file("%s/%s/configure" % (self.conanfile_directory, self.sources_folder), old_str, new_str)

                if self.settings.os == "Windows":
                    run_in_windows_bash(self, "%s && ./configure" % cd_build)
                    run_in_windows_bash(self, "%s && make" % cd_build)
                else:
                    configure_options = " --prefix=%s" % self.package_folder
                    if self.options.shared:
                        configure_options += " --disable-static --enable-shared"
                    else:
                        configure_options += " --disable-shared --enable-static"
                    self.run("%s && chmod +x ./configure" % cd_build)
                    self.run("%s && chmod +x ./install-sh" % cd_build)
                    self.run("%s && ./configure%s" % (cd_build, configure_options))
                    self.run("%s && make" % cd_build)
                    self.run("%s && make install" % cd_build)

    def package(self):
        self.copy("FindVORBIS.cmake", ".", ".")
        self.copy("include/vorbis/*", ".", "%s" % self.sources_folder, keep_path=True)
        self.copy("%s/copying*" % self.sources_folder, dst="licenses",  ignore_case=True, keep_path=False)

        if self.settings.compiler == "Visual Studio":
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", keep_path=False)
            self.copy(pattern="*.pdb", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
        else:
            if self.options.shared:
                if self.settings.os == "Windows":
                    self.copy(pattern="*.dll.a", dst="lib", keep_path=False)
                    self.copy(pattern="*.dll", dst="bin", keep_path=False)

    def package_info(self):
        if self.settings.compiler == "Visual Studio" and self.version == "1.3.5":
            if self.options.shared:
                self.cpp_info.libs = ['libvorbis', 'libvorbisfile']
            else:
                self.cpp_info.libs = ['libvorbis_static', 'libvorbisfile_static']
                self.cpp_info.exelinkflags.append('-NODEFAULTLIB:LIBCMTD')
                self.cpp_info.exelinkflags.append('-NODEFAULTLIB:LIBCMT')
        else:
            self.cpp_info.libs = ['vorbisfile', 'vorbisenc', 'vorbis']

        if self.settings.os == "Linux" and not self.options.shared:
            self.cpp_info.libs.append("m")
