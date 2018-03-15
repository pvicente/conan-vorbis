#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment, VisualStudioBuildEnvironment
from conans.errors import ConanException
import os


class VorbisConan(ConanFile):
    name = "vorbis"
    version = "1.3.5"
    description = "The VORBIS audio codec library"
    url = "http://github.com/bincrafters/conan-vorbis"
    homepage = "https://xiph.org/vorbis/"
    license = "BSD"
    exports = ["LICENSE.md", "FindVORBIS.cmake"]
    source_subfolder = "sources"
    settings = "os", "arch", "build_type", "compiler"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"
    requires = "ogg/1.3.3@bincrafters/stable"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.remove("fPIC")

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio":
            raise ConanException(
                "On Windows, version 1.3.5 of the vorbis package only supports "
                "the Visual Studio compiler for the time being."
            )

        del self.settings.compiler.libcxx

    def source(self):
        source_url = "http://downloads.xiph.org/releases"
        archive_name = "lib" + self.name + "-" + self.version
        tools.get("{url}/{libname}/{archive_name}.tar.gz".format(
            url=source_url, libname=self.name, archive_name=archive_name)
        )
        os.rename(archive_name, self.source_subfolder)

    def build(self):
        if self.settings.compiler == "Visual Studio":
            env_build = VisualStudioBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                for project in ["vorbisenc", "vorbisdec", "libvorbis", "libvorbisfile"]:
                    self.update_project_content(project)
                
                sln_filename = "vorbis" + self.get_msvc_suffix() + ".sln"
                sln_path = os.path.join(self.source_subfolder, "win32", "VS2010")
                
                msvc_command = tools.msvc_build_command(self.settings, sln_filename) \
                    .replace('Platform="x86"', 'Platform="Win32"')
                
                with tools.chdir(sln_path):
                    self.run(msvc_command)

        else:
            env = AutoToolsBuildEnvironment(self)
            if self.settings.os != "Windows":
                env.fpic = self.options.fPIC 

            with tools.environment_append(env.vars):
                with tools.chdir(self.source_subfolder):
                    if self.settings.os == "Macos":
                        old_str = '-install_name \\$rpath/\\$soname'
                        new_str = '-install_name \\$soname'
                        tools.replace_in_file("configure", old_str, new_str)

                    if self.settings.os == "Windows":
                        tools.run_in_windows_bash(self, "./configure")
                        tools.run_in_windows_bash(self, "make")
                    else:
                        configure_options = " --prefix=%s" % self.package_folder
                        if self.options.shared:
                            configure_options += " --disable-static --enable-shared"
                        else:
                            configure_options += " --disable-shared --enable-static"
                        self.run("chmod +x ./configure")
                        self.run("chmod +x ./install-sh")
                        self.run("./configure%s" % configure_options)
                        self.run("make")
                        self.run("make install")

    def package(self):
        self.copy("FindOGG.cmake")
        self.copy("COPYING", src=self.source_subfolder, keep_path=False)
        src_include_dir = os.path.join(self.source_subfolder, "include")
        
        self.copy("*", dst="include", src=src_include_dir, keep_path=True)

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

    def update_project_content(self, project):
        libdirs="<AdditionalLibraryDirectories>"
        libdirs_ext="<AdditionalLibraryDirectories>$(LIB);"
        path = self.get_vcxproj_path(project)

        updated_content = tools \
            .load(path) \
            .replace("libogg.lib", "ogg.lib") \
            .replace("libogg_static.lib", "ogg.lib") \
            .replace(libdirs, libdirs_ext)
            
        tools.save(path, updated_content)
        
    def get_vcxproj_path(self, project):
        filename = self.get_vcxproj_filename(project)
        return os.path.join(self.source_subfolder, "win32", "VS2010", project, filename)
        
    def get_vcxproj_filename(self, project):
        return project + self.get_msvc_suffix() + ".vcxproj"

    def get_msvc_suffix(self):
        return "_dynamic" if self.options.shared else "_static"
