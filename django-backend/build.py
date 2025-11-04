# import os
# import shutil
# import py_compile
# from pathlib import Path

# def create_build_folder():
#     """Create or clear the build folder."""
#     build_dir = "build"
#     if os.path.exists(build_dir):
#         shutil.rmtree(build_dir)
#     os.makedirs(build_dir)
#     print(f"Created build folder: {build_dir}")

# def compile_and_copy_py_files(src_path, dest_path):
#     """Compile .py files to .pyc and copy to destination."""
#     src = Path(src_path)
#     dest = Path(dest_path)
    
#     if src.is_file() and src.suffix == ".py":
#         try:
#             # Compile .py to .pyc
#             pyc_file = dest.with_suffix(".pyc")
#             py_compile.compile(str(src), cfile=str(pyc_file), doraise=True)
#             print(f"Compiled {src} to {pyc_file}")
#         except py_compile.PyCompileError as e:
#             print(f"Error compiling {src}: {e}")
#     elif src.is_dir():
#         # Create corresponding directory in build
#         dest.mkdir(parents=True, exist_ok=True)
#         for item in src.iterdir():
#             compile_and_copy_py_files(item, dest / item.name)

# def copy_non_python_files():
#     """Copy non-Python files and directories to build folder."""
#     items_to_copy = [
#         "media",
#         "pids",
#         "templates",
#         "db.sqlite3",
#         "Dockerfile",
#         "requirements.txt",
#         'frontend'
#     ]

#     for item in items_to_copy:
#         src = Path(item)
#         dst = Path("build") / item
#         if src.exists():
#             if src.is_dir():
#                 shutil.copytree(src, dst, dirs_exist_ok=True)
#             else:
#                 shutil.copy2(src, dst)
#             print(f"Copied {item} to build/{item}")
#         else:
#             print(f"Warning: {item} not found, skipping.")

# def verify_build():
#     """Verify that key files exist in the build folder."""
#     build_dir = Path("build")
#     required_items = [
#         "manage.pyc",
#         "image_modifier_app",
#         "Nexify",
#         "sku",
#         "users",
#         "workspace",
#         "utils",
#         "ml_shell_scripts",
#         "domains.pyc",
#         "test_image_sender.pyc",
#         "setup.pyc",
#         "db.sqlite3",
#         "templates",
#         "media",
#         "pids",
#         "requirements.txt",
#         "Dockerfile"
#     ]

#     print("\nVerifying build folder contents:")
#     missing = False
#     for item in required_items:
#         if (build_dir / item).exists():
#             print(f"✓ {item} found")
#         else:
#             print(f"✗ {item} missing")
#             missing = True
#     if missing:
#         print("Warning: Some files/directories are missing. Check compilation errors or source files.")
#     else:
#         print("All expected files/directories found.")

# def main():
#     print(f"Starting compilation process at {Path.cwd()}...")
#     try:
#         create_build_folder()
        
#         # List of directories and files to compile
#         dirs_to_compile = [
#             "image_modifier_app",
#             "Nexify",
#             "sku",
#             "users",
#             "workspace",
#             "utils",
#             "ml_shell_scripts"
#         ]
#         files_to_compile = [
#             "manage.py",
#             "domains.py",
#             "test_image_sender.py",
#             "setup.py"
#         ]

#         # Compile directories
#         for dir_path in dirs_to_compile:
#             if not Path(dir_path).exists():
#                 print(f"Warning: {dir_path} does not exist, skipping.")
#                 continue
#             compile_and_copy_py_files(dir_path, f"build/{dir_path}")

#         # Compile individual files
#         for file_path in files_to_compile:
#             if not Path(file_path).exists():
#                 print(f"Warning: {file_path} does not exist, skipping.")
#                 continue
#             compile_and_copy_py_files(file_path, f"build/{file_path}")

#         # Copy non-Python files
#         copy_non_python_files()
        
#         # Verify build contents
#         verify_build()

#         print("\nCompilation complete! The 'build' folder contains the compiled project.")
#         print("\nTo run the compiled project:")
#         print("1. Navigate to the build folder: cd build")
#         print("2. Install dependencies: pip3 install -r requirements.txt")
#         print("3. Run the Django server: python3 manage.pyc runserver")
#         print("4. For ML scripts, e.g.: python3 ml_shell_scripts/anomaly_detection/train.pyc")
#         print("5. For Docker, update Dockerfile to reference .pyc files, then: docker build -t myapp . && docker run -p 8000:8000 myapp")
#         print("\nNote: Ensure dependencies in requirements.txt are installed.")
#         print("If errors occur, check compilation errors or ensure all source files exist.")
#     except Exception as e:
#         print(f"Compilation failed: {str(e)}")
#         print("Please ensure all source files/directories exist.")

# if __name__ == "__main__":
#     main()

