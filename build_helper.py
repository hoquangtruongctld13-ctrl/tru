#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VN TTS Studio - Build Helper Script
====================================

Script này giúp copy các thư viện nặng vào thư mục build.
Chạy sau khi build với PyInstaller.

Usage:
    python build_helper.py --copy-libs
    python build_helper.py --check-libs
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Danh sách các thư viện nặng cần copy
HEAVY_LIBS = [
    'torch',
    'torchaudio',
    'torchvision',
    'librosa',
    'neucodec',
    'phonemizer',
    'onnxruntime',
    'numpy',
    'scipy',
    'soundfile',
    'llama_cpp',  # Optional - for GGUF models
]

# Các file/folder cần exclude khi copy để giảm size
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    'test',
    'tests',
    'testing',
    'examples',
    'docs',
    'doc',
    'benchmarks',
    '*.egg-info',
    '.git',
]


def get_lib_path(lib_name):
    """Get the installation path of a library"""
    try:
        module = __import__(lib_name)
        if hasattr(module, '__path__'):
            return Path(module.__path__[0])
        elif hasattr(module, '__file__'):
            return Path(module.__file__).parent
    except ImportError:
        return None
    return None


def copy_lib(lib_name, dest_dir, verbose=True):
    """Copy a library to destination directory"""
    src_path = get_lib_path(lib_name)
    
    if src_path is None:
        if verbose:
            print(f"  ⚠️ {lib_name}: Not installed, skipping")
        return False
    
    dest_path = dest_dir / lib_name
    
    if verbose:
        print(f"  📦 Copying {lib_name}...", end=" ")
    
    try:
        # Remove old copy if exists
        if dest_path.exists():
            shutil.rmtree(dest_path)
        
        # Copy with exclusions
        def ignore_patterns(directory, files):
            ignored = []
            for f in files:
                for pattern in EXCLUDE_PATTERNS:
                    if pattern.startswith('*'):
                        if f.endswith(pattern[1:]):
                            ignored.append(f)
                            break
                    elif f == pattern:
                        ignored.append(f)
                        break
            return ignored
        
        shutil.copytree(src_path, dest_path, ignore=ignore_patterns)
        
        if verbose:
            size = sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())
            print(f"✓ ({size / 1024 / 1024:.1f} MB)")
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"✗ Error: {e}")
        return False


def check_libs(verbose=True):
    """Check which heavy libraries are installed"""
    if verbose:
        print("Checking installed heavy libraries:")
        print("-" * 40)
    
    installed = []
    missing = []
    
    for lib in HEAVY_LIBS:
        path = get_lib_path(lib)
        if path:
            installed.append(lib)
            if verbose:
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                print(f"  ✓ {lib}: {path} ({size / 1024 / 1024:.1f} MB)")
        else:
            missing.append(lib)
            if verbose:
                print(f"  ✗ {lib}: Not installed")
    
    if verbose:
        print("-" * 40)
        print(f"Installed: {len(installed)}/{len(HEAVY_LIBS)}")
        if missing:
            print(f"Missing: {', '.join(missing)}")
    
    return installed, missing


def copy_all_libs(dest_dir, verbose=True):
    """Copy all heavy libraries to destination"""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        print(f"Copying heavy libraries to: {dest_dir}")
        print("-" * 40)
    
    success = 0
    failed = 0
    
    for lib in HEAVY_LIBS:
        if copy_lib(lib, dest_dir, verbose):
            success += 1
        else:
            failed += 1
    
    if verbose:
        print("-" * 40)
        print(f"Copied: {success}, Failed/Skipped: {failed}")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in dest_dir.rglob('*') if f.is_file())
        print(f"Total size: {total_size / 1024 / 1024:.1f} MB")
    
    return success, failed


def main():
    parser = argparse.ArgumentParser(description='VN TTS Studio Build Helper')
    parser.add_argument('--copy-libs', action='store_true',
                       help='Copy heavy libraries to dist folder')
    parser.add_argument('--check-libs', action='store_true',
                       help='Check installed heavy libraries')
    parser.add_argument('--dest', default='dist/VNTTSStudio/_libs',
                       help='Destination directory for libraries')
    
    args = parser.parse_args()
    
    if args.check_libs:
        check_libs()
    elif args.copy_libs:
        copy_all_libs(args.dest)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
