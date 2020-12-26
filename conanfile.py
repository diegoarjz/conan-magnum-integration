#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
import os

def sort_libs(correct_order, libs, lib_suffix='', reverse_result=False):
    # Add suffix for correct string matching
    correct_order[:] = [s.__add__(lib_suffix) for s in correct_order]

    result = []
    for expectedLib in correct_order:
        for lib in libs:
            if expectedLib == lib:
                result.append(lib)

    if reverse_result:
        # Linking happens in reversed order
        result.reverse()

    return result

class LibnameConan(ConanFile):
    name = "magnum-integration"
    version = "2020.06"
    description =   "Integration libraries for Magnum"
    # topics can get used for searches, GitHub topics, Bintray tags etc. Add here keywords about the library
    topics = ("conan", "corrade", "graphics", "rendering", "3d", "2d", "opengl")
    url = ""
    homepage = "https://magnum.graphics"
    author = ""
    license = "MIT"  # Indicates license type of the packaged library; please use SPDX Identifiers https://spdx.org/licenses/
    exports = []
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    short_paths = True  # Some folders go out of the 260 chars path length scope (windows)

    # Options may need to change depending on the packaged library.
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_imgui": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_imgui": True
    }

    # Custom attributes for Bincrafters recipe conventions
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    _imgui_version = "1.79"
    _imgui_subfolder = "imgui_subfolder"

    requires = (
        "corrade/2020.06@helmesjo/stable",
        "magnum/2020.06@pagoda/stable"
    )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options['corrade'].shared = True

    def requirements(self):
        pass

    def source(self):
        source_url = "https://github.com/mosra/magnum-integration"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version))
        extracted_dir = self.name + "-" + self.version
        # Rename to "source_subfolder" is a convention to simplify later steps
        os.rename(extracted_dir, self._source_subfolder)

        # ImGUI
        if self.options.with_imgui:
            source_url = "https://github.com/ocornut/imgui"
            tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self._imgui_version))
            extracted_dir = "imgui-{0}".format(self._imgui_version)
            os.rename(extracted_dir, self._imgui_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            cmake.definitions[var_name] = var_value
            print("{0}={1}".format(var_name, var_value))

        for option, value in self.options.items():
            add_cmake_option(option, value)

        if self.options.with_imgui:
            imgui_dir = os.path.abspath(os.path.join(".", self._imgui_subfolder))
            add_cmake_option("IMGUI_DIR", imgui_dir)

        add_cmake_option("BUILD_STATIC", not self.options.shared)
        add_cmake_option("BUILD_STATIC_PIC", not self.options.shared and self.options.get_safe("fPIC") == True)

        # Magnum uses suffix on the resulting 'lib'-folder when running cmake.install()
        # Set it explicitly to empty, else Magnum might set it implicitly (eg. to "64")
        add_cmake_option("LIB_SUFFIX", "")
        cmake.configure(build_folder=self._build_subfolder)

        return cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        self.copy("{}/*".format(self._imgui_subfolder))
        self.copy("{}/modules/*".format(self._source_subfolder))

    def package_info(self):
        # See dependency order here: https://doc.magnum.graphics/magnum/custom-buildsystems.html
        allLibs = [
            "MagnumImGuiIntegration"
        ]

        # Sort all built libs according to above, and reverse result for correct link order
        suffix = '-d' if self.settings.build_type == "Debug" else ''
        builtLibs = tools.collect_libs(self)
        print("Found libs: ", builtLibs)
        self.cpp_info.libs = sort_libs(correct_order=allLibs, libs=builtLibs, lib_suffix=suffix, reverse_result=True)
        print("Link order: ", self.cpp_info.libs)

        if self.options.shared:
            if self.settings.os == "Windows":
                self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
            if self.settings.os == "Linux":
                self.env_info.LD_LIBRARY_PATH.append(os.path.join(self.package_folder, "lib"))
            if self.settings.os == "Macos":
                self.env_info.DYLD_LIBRARY_PATH.append(os.path.join(self.package_folder, "lib"))
