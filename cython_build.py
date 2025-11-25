import os

import shutil

from setuptools import setup, Extension

from Cython.Build import cythonize
 
# === 1. Define Python files and their desired compiled module names ===

# Format →  "source_py_name": "compiled_module_name"

modules = {

    "main": "tgpl_model",   # Compile main.py → mainbos.so/pyd

    # "file2": "securemod2",  # Add more if you want

}
 
# === 2. Convert .py → .pyx ===

for src, mod in modules.items():

    py_file = f"{src}.py"

    pyx_file = f"{src}.pyx"
 
    if os.path.exists(py_file):

        print(f"Renaming {py_file} → {pyx_file}")

        os.rename(py_file, pyx_file)

    else:

        raise FileNotFoundError(f"❌ Error: {py_file} not found!")
 
# === 3. Prepare Cython Extensions with custom names ===

extensions = []

for src, mod in modules.items():

    extensions.append(

        Extension(

            name=mod,                 # This becomes PyInit_<mod>

            sources=[f"{src}.pyx"],   # Use original source filename

        )

    )
 
# === 4. Run Cython build ===

setup(

    ext_modules=cythonize(

        extensions,

        compiler_directives={"language_level": "3"},

        build_dir="build"

    ),

    script_args=["build_ext", "--inplace"]

)
 
# === 5. Cleanup ===

for src, mod in modules.items():

    # Remove temporary PYX

    pyx_file = f"{src}.pyx"

    if os.path.exists(pyx_file):

        os.remove(pyx_file)
 
    # Remove generated C file

    c_file = f"{src}.c"

    if os.path.exists(c_file):

        os.remove(c_file)
 
# Remove build directory

if os.path.exists("build"):

    shutil.rmtree("build")
 
print("\n✅ Compilation complete!")

print("🎉 Compiled modules created:")

for src, mod in modules.items():

    print(f"   → {mod}.so / {mod}.pyd")

print("You can now safely import using the new module name.")

 
