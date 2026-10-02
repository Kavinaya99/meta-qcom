# ==========================================================================
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: ISC
# ==========================================================================
# gen_its.py - A script to generate FIT (Flattened Image Tree) images from
# ELF/MBN files and raw binaries, using a fixed, #if-gated template.
#
# template.its declares every known image node up front, each wrapped in
# "#if HAVE_<NAME> == 1 ... #endif". Component selection is entirely
# tag-driven: pass only the --<name>_path flags for the images you actually
# want, and this script enables the matching #define, fills in the
# load/entry placeholders, and runs the result through cpp -P to strip
# everything that wasn't selected. Raw-binary components (pmic_cocos,
# pmic_wailua, dcb_lp4, dcb_lp5, ecc) default to their fixed pre-DDR SRAM
# memory-map address (see RAW_BIN_DEFAULT_ADDR below) - pass --<name>_addr
# only if you need to override it.
#
# Example Usage:
# -------------
# Pre-DDR only (verified against real Shikra images):
# python gen_its.py --template template.its \
#                  --pmic_cocos_path Pmic_Cocos.bin \
#                  --pmic_wailua_path Pmic_Wailua.bin \
#                  --dcb_lp4_path 900B_7_0100_0_dcb.bin \
#                  --dcb_lp5_path 900B_7_0100_1_dcb.bin \
#                  --ecc_path Shikra_LCP.bin \
#                  --shrm_path shrm.elf \
#                  --qclib_path QcLib.elf \
#                  --output ./out/shikra_preddr.img
#
# Combined pre-DDR + post-DDR:
# rm -rf ./out/ && python gen_its.py --template template.its \
#   --pmic_cocos_path Pmic_Cocos.bin \
#   --pmic_wailua_path Pmic_Wailua.bin \
#   --dcb_lp4_path 900B_7_0100_0_dcb.bin \
#   --dcb_lp5_path 900B_7_0100_1_dcb.bin \
#   --ecc_path Shikra_LCP.bin \
#   --shrm_path shrm.elf \
#   --qclib_path QcLib.elf \
#   --tfa_bl31_path bl31.elf \
#   --optee_path tee.elf \
#   --uboot_path u-boot.mbn \
#   --rpm_path rpm.mbn \
#   --output ./out/shikra_full.img
#
# Produces shikra_preddr.its/.img (pre-DDR only) or shikra_full.its/.img
# (both pre-ddr-config and post-ddr-config). Raw-binary load addresses use
# RAW_BIN_DEFAULT_ADDR defaults (no --*_addr flags needed).
#
# You can also pack any subset of these by passing only the tags for the
# images you want - e.g. --shrm_path alone produces a FIT with just
# shrm_1/shrm_2 and a pre-ddr-config configuration.
#
# Note: --template and --output are the only always-required arguments.
# At least one image component (or --dpr) must be supplied.
# This script is compatible with both Python 2.7 and Python 3.

from __future__ import print_function

import os
import argparse
import mbn_tools
import subprocess
import shutil
import re
import sys
import errno

# ---------------------------------------------------------------------------
# Component registry
# ---------------------------------------------------------------------------
# Single source of truth for every image the script/template know how to
# pack. template.its has a fixed, hardcoded node (and #if HAVE_<NAME>*
# define) per component per segment slot, so max_segments here MUST match
# the number of "#if HAVE_<NAME>_<i>" slots actually present in the
# template - if a real ELF has more LOAD segments than max_segments, the
# script errors out rather than silently dropping data.
#
# entry_rule selects which segments get an "entry" property and where its
# value comes from, matching the conventions observed in the sample .its:
#   'first_only'      - only segment 1 has entry, set to the ELF's e_entry
#                        (shrm, qclib, uboot, optee)
#   'first_and_last'  - segment 1 AND whichever segment is actually last
#                        both get entry = the ELF's e_entry (tfa_bl31, which
#                        repeats its entry point on both bookend segments)
#   'own_load'        - every segment gets entry = its own load address,
#                        not a single global entry point (rpm)
RAW_BIN_COMPONENTS = ['pmic_cocos', 'pmic_wailua', 'dcb_lp4', 'dcb_lp5', 'ecc']

# Default load addresses per the pre-DDR SRAM memory map (Start Addr column),
# so --<name>_addr doesn't need to be typed on every invocation. Still
# overridable via the CLI flag if the memory map ever changes.
RAW_BIN_DEFAULT_ADDR = {
    'pmic_cocos': '0x0C294800',
    'pmic_wailua': '0x0C2A0400',
    'dcb_lp4': '0x0C2A6400',
    'dcb_lp5': '0x0C2AAC00',
    'ecc': '0x0C2AF400',
}

# Hardcoded load/entry addresses for flat-binary (.bin) inputs.
# Only used when a .bin (not an ELF/MBN) is passed for these components.
BIN_ENTRY_ADDRS = {
    'optee':    '0xa1400000',
    'tfa_bl31': '0xa1300000',
    'uboot':    '0x9f400000',
}

ELF_COMPONENTS = {
    # name         stage    max_segments  entry_rule
    'shrm':       ('pre',   2,            'first_only'),
    'qclib':      ('pre',   2,            'first_only'),
    'tfa_bl31':   ('post',  4,            'first_and_last'),
    'rpm':        ('post',  2,            'own_load'),
    'uboot':      ('post',  1,            'first_only'),
    'optee':      ('post',  2,            'first_only'),
}



def raw_bin_define(name):
    """#define name gating a raw-binary component's node in template.its."""
    return "HAVE_{0}".format(name.upper())


def raw_bin_addr_placeholder(name):
    """Placeholder token for a raw-binary component's load/entry address."""
    return "{0}_ADDR".format(name.upper())


def elf_segment_define(name, index):
    """#define name gating the Nth LOAD-segment node of an ELF component."""
    if index == 1:
        return "HAVE_{0}".format(name.upper())
    return "HAVE_{0}_{1}".format(name.upper(), index)


def elf_segment_load_placeholder(name, index):
    """Placeholder token for the Nth LOAD segment's load address."""
    return "{0}_{1}_LOAD_ADDR".format(name.upper(), index)


def elf_entry_placeholder(name):
    """Placeholder token for an ELF component's global entry point."""
    return "{0}_ENTRY_ADDR".format(name.upper())


def elf_entry_enable_define(name, index):
    """#define name gating a conditional 'entry' property on segment N.

    Only used by the 'first_and_last' entry rule, where the template needs
    to know at runtime which segment is actually last.
    """
    return "HAVE_{0}_{1}_ENTRY".format(name.upper(), index)


def handle_error(operation_name, e, default_return=False):
    """
    Common error handling function for operations.

    Args:
        operation_name: Name of the operation that failed
        e: Exception object
        default_return: Default value to return on error

    Returns:
        The default return value (usually False or empty list/dict)
    """
    error_type = "Error" if isinstance(e, (IOError, OSError)) else "Unexpected error"
    print("{0} in {1}: {2}".format(error_type, operation_name, e))
    return default_return


def validate_path(path):
    """
    Validate that a file path is safe and doesn't contain directory traversal attempts.

    Args:
        path: The file path to validate

    Returns:
        bool: True if the path is safe, False otherwise
    """
    try:
        if not path:
            return False  # Empty paths are considered invalid for security

        # Check for shell metacharacters that could be used for command injection
        if re.search(r'[;&|`$!*?~<>^()\[\]{}\'"]', path):
            return False

        # Check for absolute paths (both Unix and Windows styles)
        if os.path.isabs(path):
            return False

        # Check for potentially dangerous Unicode characters
        for char in path:
            if ord(char) > 127:  # Non-ASCII characters
                return False

        # Get the base directory for path resolution
        base_dir = os.path.abspath(os.getcwd())

        # Get the absolute path before normalization
        abs_path_before = os.path.abspath(os.path.join(base_dir, path))

        # Check if the path would resolve outside the base directory
        if not abs_path_before.startswith(base_dir):
            return False

        # Normalize the path once to handle all '..' and '.' components
        normalized_path = os.path.normpath(path)

        # Quick checks on the normalized path
        if not normalized_path or normalized_path == '.' or normalized_path == '..':
            return False

        if normalized_path.startswith('..'):
            return False

        # Check for directory traversal patterns in the normalized path
        path_parts = normalized_path.split(os.sep)
        if '..' in path_parts:
            return False

        # Handle Windows-style separators if on a non-Windows system
        if os.sep != '\\' and '\\' in normalized_path:
            win_path_parts = normalized_path.replace('\\', os.sep).split(os.sep)
            if '..' in win_path_parts:
                return False

        # Get the absolute path after normalization
        abs_path_after = os.path.abspath(os.path.join(base_dir, normalized_path))

        # Ensure the normalized path stays within the base directory
        if not abs_path_after.startswith(base_dir):
            return False

        # Additional check for paths that changed during normalization
        if abs_path_before != abs_path_after:
            rel_path = os.path.relpath(abs_path_after, base_dir)
            if rel_path.startswith('..'):
                return False

        # Validate each path component
        for component in path_parts:
            if component and not validate_filename(component):
                return False

        return True
    except (IOError, OSError, Exception) as e:
        return handle_error("validating path", e, False)


def validate_filename(filename):
    """
    Validate that a filename contains only safe characters.

    Args:
        filename: The filename to validate

    Returns:
        bool: True if the filename is safe, False otherwise
    """
    try:
        # Ensure filename doesn't start with a dot (hidden file)
        if filename.startswith('.'):
            return False
        # Ensure filename doesn't contain consecutive dots
        if '..' in filename:
            return False
        # Ensure filename doesn't contain any potentially dangerous characters
        # Use match with ^ and $ to ensure the entire string matches the pattern
        return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', filename))
    except (IOError, OSError, Exception) as e:
        return handle_error("validating filename", e, False)


def validate_hex_address(value):
    """
    Validate that a string is a hex address literal accepted by the DTS
    "load"/"entry" cell syntax (e.g. "0x8CB5800").

    Args:
        value: The address string to validate

    Returns:
        bool: True if the address is a valid hex literal, False otherwise
    """
    return bool(re.match(r'^0[xX][0-9a-fA-F]+$', value or ''))


def sanitize_path(path):
    """
    Sanitize a path to ensure it's safe for file operations.

    Args:
        path: The path to sanitize

    Returns:
        tuple: (bool, str) - (True, normalized_path) if valid, (False, None) if invalid
    """
    try:
        # First validate the path using the comprehensive validate_path function
        if not path or not validate_path(path):
            return (False, None)

        # Path is valid, return the normalized version
        return (True, os.path.normpath(path))
    except Exception as e:
        # Use the return value from handle_error for consistency
        success = handle_error("sanitizing path", e, False)
        return (success, None)


class ElfParser:
    """
    Class for parsing ELF/MBN files and extracting necessary information.
    """
    def __init__(self, input_file, component_name, output_dir, temp_files_list=None):
        """
        Initialize the ElfParser.

        Args:
            input_file: Path to the input ELF/MBN file
            component_name: Name of the component (used for output file naming)
            output_dir: Directory where output files will be saved
            temp_files_list: List to track temporary files created (optional)
        """
        self.input_file = input_file
        self.component_name = component_name
        self.load_segments = []
        self.entry_point = None
        self.arch = None
        self.output_dir = output_dir
        self.temp_files_list = temp_files_list

    def parse(self):
        """
        Parse the ELF file and extract LOAD segments, entry point, and architecture.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        # Create output directory if it doesn't exist
        try:
            os.makedirs(self.output_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                return handle_error("creating output directory", e)
        except Exception as e:
            return handle_error("creating output directory", e)

        load_info = []
        load_info_filename = os.path.join(self.output_dir, "{0}_load_addresses.txt".format(self.component_name))

        # Track temporary files if a list was provided
        if self.temp_files_list is not None and isinstance(self.temp_files_list, list):
            try:
                self.temp_files_list.append(load_info_filename)
            except Exception as e:
                print("Warning: Failed to add {0} to tracking list: {1}".format(load_info_filename, e))

        try:
            with mbn_tools.OPEN(self.input_file, "r+b") as elf:
                [elf_header, phdr_table] = mbn_tools.preprocess_elf_file(self.input_file)

                if elf_header.e_ident[mbn_tools.ELFINFO_CLASS_INDEX] == mbn_tools.ELFINFO_CLASS_64:
                    self.arch = "arm64"
                else:
                    self.arch = "arm"

                elf_entry_vaddr = elf_header.e_entry
                load_info.append("arch: {0}".format(self.arch))
                load_info.append("entry_point (vaddr): 0x{0:X}".format(elf_entry_vaddr))

                load_segment_count = 1
                entry_point_paddr = None

                # Process all LOAD segments
                for phdr_index in range(elf_header.e_phnum):
                    curr_phdr = phdr_table[phdr_index]

                    if curr_phdr.p_type == 0x1 and curr_phdr.p_memsz > 0 and curr_phdr.p_filesz > 0:
                        elf.seek(curr_phdr.p_offset)
                        file_buff = elf.read(curr_phdr.p_filesz)

                        load_filename = os.path.join(self.output_dir, "{0}_{1}_load_segment.bin".format(self.component_name, load_segment_count))

                        try:
                            with open(load_filename, 'wb') as load_file:
                                load_file.write(file_buff)
                            if self.temp_files_list is not None and isinstance(self.temp_files_list, list):
                                try:
                                    self.temp_files_list.append(load_filename)
                                except Exception as e:
                                    print("Warning: Failed to add {0} to tracking list: {1}".format(load_filename, e))
                        except (IOError, OSError) as e:
                            return handle_error("writing load segment file {0}".format(load_filename), e)
                        except Exception as e:
                            return handle_error("writing load segment file {0}".format(load_filename), e)

                        # Use the physical address (p_paddr), not the virtual
                        # address (p_vaddr) - the FIT "load" property must be
                        # where the bootloader physically places the segment
                        # in memory, not its runtime virtual mapping.
                        load_address = curr_phdr.p_paddr
                        segment_info = {
                            'filename': os.path.basename(load_filename),
                            'load_address': "0x{0:X}".format(load_address)
                        }
                        self.load_segments.append(segment_info)
                        load_info.append("{0}: 0x{1:X}".format(os.path.basename(load_filename), load_address))
                        load_segment_count += 1

                        # e_entry is a virtual address; translate it to the
                        # matching physical address via whichever LOAD
                        # segment's vaddr range contains it, using that
                        # segment's fixed vaddr->paddr offset.
                        if (entry_point_paddr is None and
                                curr_phdr.p_vaddr <= elf_entry_vaddr < curr_phdr.p_vaddr + curr_phdr.p_memsz):
                            entry_point_paddr = curr_phdr.p_paddr + (elf_entry_vaddr - curr_phdr.p_vaddr)

                if entry_point_paddr is None:
                    # Entry point isn't covered by any LOAD segment (unusual,
                    # but not fatal) - fall back to the raw virtual address
                    # rather than failing the whole component.
                    print("Warning: entry point 0x{0:X} not within any LOAD segment's vaddr "
                          "range for {1}; using it unmapped".format(elf_entry_vaddr, self.component_name))
                    entry_point_paddr = elf_entry_vaddr

                self.entry_point = entry_point_paddr
                load_info.append("entry_point (paddr): 0x{0:X}".format(self.entry_point))

            try:
                with open(load_info_filename, 'w') as info_file:
                    info_file.write("\n".join(load_info))
            except (IOError, OSError) as e:
                return handle_error("writing load info file {0}".format(load_info_filename), e)
            except Exception as e:
                return handle_error("writing load info file {0}".format(load_info_filename), e)

            print("Split {0} into {1} load segment(s)".format(self.component_name, len(self.load_segments)))
            print("Saved load addresses to {0}_load_addresses.txt\n".format(self.component_name))

            return True
        except (IOError, OSError) as e:
            return handle_error("opening ELF file", e)
        except Exception as e:
            return handle_error("opening ELF file", e)

    def get_load_segments(self):
        """
        Get the LOAD segments.

        Returns:
            list: List of load segment dicts (filename, load_address)
        """
        return self.load_segments

    def get_entry_point(self):
        """
        Get the entry point.

        Returns:
            str: Entry point address as a hex string
        """
        return "0x{0:X}".format(self.entry_point) if self.entry_point else "0x00000000"


class FitImageGenerator:
    """
    Class for orchestrating the FIT image generation process: parsing input
    files, enabling the matching #if blocks/placeholders in the fixed
    template, and invoking mkimage to produce the final FIT image.
    """
    def __init__(self, args):
        """
        Initialize the FitImageGenerator.

        Args:
            args: Command line arguments
        """
        self.args = args
        self.temp_files = []  # List to track temporary files created during execution
        self.defines_to_enable = set()
        self.placeholders = {}

        # Extract directory and filename from args.output
        output_dir, output_filename = os.path.split(args.output)
        if not output_dir:
            output_dir = os.getcwd()
        else:
            output_dir = os.path.join(os.getcwd(), output_dir)

        self.output_dir = output_dir
        self.img_file = os.path.join(self.output_dir, output_filename)

        filename_root, filename_ext = os.path.splitext(output_filename)
        if filename_ext:
            its_filename = "{0}.its".format(filename_root)
        else:
            its_filename = "{0}.its".format(output_filename)

        self.its_file = os.path.join(self.output_dir, its_filename)

    def process_raw_bin_components(self):
        """
        Enable the template's #if block and set the load/entry placeholder
        for every raw-binary component supplied on the command line
        (pmic_cocos, pmic_wailua, dcb_lp4, dcb_lp5, ecc). These are always
        pre-DDR, single-node, with load == entry == the supplied address (or
        its RAW_BIN_DEFAULT_ADDR memory-map default if --<name>_addr wasn't
        passed).

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        for name in RAW_BIN_COMPONENTS:
            path_val = getattr(self.args, "{0}_path".format(name), None)
            if not path_val:
                continue

            addr_val = getattr(self.args, "{0}_addr".format(name), None) or RAW_BIN_DEFAULT_ADDR.get(name)
            # template.its hardcodes the incbin filename per component (e.g.
            # "./pmic_cocos.bin"), independent of the source file's actual
            # name - always copy to that fixed name, same convention as the
            # ELF path's "<name>_<i>_load_segment.bin" outputs.
            output_path = os.path.join(self.output_dir, "{0}.bin".format(name))

            try:
                shutil.copy2(path_val, output_path)
                self.temp_files.append(output_path)
            except (IOError, OSError) as e:
                return handle_error("copying {0} binary".format(name), e, False)

            self.defines_to_enable.add(raw_bin_define(name))
            self.placeholders[raw_bin_addr_placeholder(name)] = addr_val
            self.defines_to_enable.add("HAVE_PRE_DDR")
            print("Added raw-binary component: {0}".format(name))

        return True

    def process_elf_components(self):
        """
        Parse and enable the template's #if block(s)/placeholders for every
        ELF-based component supplied on the command line, per the
        ELF_COMPONENTS registry. Each LOAD segment found in the ELF enables
        one fixed "<name>_<i>" node slot in the template; the registry's
        entry_rule decides which segments carry an "entry" property.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        for name, (stage, max_segments, entry_rule) in ELF_COMPONENTS.items():
            path_val = getattr(self.args, "{0}_path".format(name), None)
            if not path_val:
                continue

            if path_val.lower().endswith('.bin') and name in BIN_ENTRY_ADDRS:
                bin_entry = BIN_ENTRY_ADDRS[name]
                seg_filename = os.path.join(self.output_dir,
                                            "{0}_1_load_segment.bin".format(name))
                try:
                    shutil.copy2(path_val, seg_filename)
                    self.temp_files.append(seg_filename)
                except (IOError, OSError) as e:
                    return handle_error("copying {0} binary".format(name), e, False)

                self.defines_to_enable.add(elf_segment_define(name, 1))
                self.placeholders[elf_segment_load_placeholder(name, 1)] = bin_entry
                self.placeholders[elf_entry_placeholder(name)]           = bin_entry

                if stage == 'pre':
                    self.defines_to_enable.add("HAVE_PRE_DDR")
                else:
                    self.defines_to_enable.add("HAVE_POST_DDR")

                print("Added binary component: {0} (load/entry: {1})".format(name, bin_entry))
                continue

            parser = ElfParser(path_val, name, self.output_dir, self.temp_files)
            if not parser.parse():
                return False

            segments = parser.get_load_segments()
            count = len(segments)
            if count == 0:
                print("Error: {0} ELF has no LOAD segments".format(name))
                return False
            if count > max_segments:
                print("Error: {0} ELF has {1} LOAD segments, but template.its only has "
                      "{2} slot(s) defined for it. Add more \"#if HAVE_{3}_<N>\" node "
                      "slots to template.its to support this ELF.".format(
                          name, count, max_segments, name.upper()))
                return False

            elf_entry = parser.get_entry_point()

            for i, segment in enumerate(segments, 1):
                self.defines_to_enable.add(elf_segment_define(name, i))
                self.placeholders[elf_segment_load_placeholder(name, i)] = segment['load_address']

            if entry_rule in ('first_only', 'first_and_last'):
                self.placeholders[elf_entry_placeholder(name)] = elf_entry

            if entry_rule == 'first_and_last' and count > 1:
                self.defines_to_enable.add(elf_entry_enable_define(name, count))

            if stage == 'pre':
                self.defines_to_enable.add("HAVE_PRE_DDR")
            else:
                self.defines_to_enable.add("HAVE_POST_DDR")

            print("Added ELF component: {0} ({1} segment(s))".format(name, count))

        return True

    def process_dpr(self):
        """
        Enable the template's DPR #if block: copy the DPR ELF into the
        output directory as a single whole-image pre-DDR node (no segment
        splitting).

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not self.args.dpr_path:
            return True

        if not self.args.dpr_addr:
            print("Error: --dpr_addr is required when --dpr is supplied")
            return False

        dpr_basename = os.path.basename(self.args.dpr_path)
        output_dpr_path = os.path.join(self.output_dir, dpr_basename)

        try:
            shutil.copy2(self.args.dpr_path, output_dpr_path)
            self.temp_files.append(output_dpr_path)
        except (IOError, OSError) as e:
            return handle_error("copying DPR ELF file", e, False)

        self.defines_to_enable.add("HAVE_DPR")
        self.placeholders["DPR_FILENAME"] = dpr_basename
        self.placeholders["DPR_LOAD_ADDR"] = self.args.dpr_addr
        self.defines_to_enable.add("HAVE_PRE_DDR")
        print("Added DPR component")

        return True

    def process_dtb(self):
        """
        Enable the template's HAVE_FDT #if block: copy the optional DTB
        file into the output directory.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not self.args.dtb_path:
            return True

        dtb_basename = os.path.basename(self.args.dtb_path)
        output_dtb_path = os.path.join(self.output_dir, dtb_basename)

        try:
            shutil.copy2(self.args.dtb_path, output_dtb_path)
            self.defines_to_enable.add("HAVE_FDT")
            self.placeholders["FDT_PATH"] = dtb_basename
            print("Copied DTB file to output directory: {0}".format(dtb_basename))
        except FileNotFoundError:
            print("Error: Source DTB file does not exist: {0}".format(self.args.dtb_path))
            return False
        except PermissionError:
            print("Error: Permission denied accessing DTB file: {0}".format(self.args.dtb_path))
            return False
        except (IOError, OSError) as e:
            return handle_error("copying DTB file", e, False)

        return True

    def generate_its_file(self):
        """
        Load the fixed template, flip on the #define for every selected
        component, substitute its load/entry placeholders, run the result
        through cpp -P to strip every #if block that wasn't selected, and
        write the final .its file.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        try:
            with open(self.args.template, 'r') as f:
                template_content = f.read()
        except (IOError, OSError) as e:
            return handle_error("loading template file {0}".format(self.args.template), e)

        for define_name in self.defines_to_enable:
            template_content = template_content.replace(
                "#define {0} 0".format(define_name),
                "#define {0} 1".format(define_name))

        for placeholder_name, placeholder_value in self.placeholders.items():
            template_content = template_content.replace(placeholder_name, placeholder_value)

        temp_path = "temp_template_{0}.its".format(os.getpid())
        preprocessed_path = temp_path + ".preprocessed"
        self.temp_files.append(os.path.join(os.getcwd(), temp_path))

        try:
            with open(temp_path, 'w') as temp_file:
                temp_file.write(template_content)

            returncode = subprocess.call(
                ['cpp', '-P', '-nostdinc', '-undef', temp_path, '-o', preprocessed_path],
                shell=False
            )
            if returncode != 0:
                print("Error: cpp preprocessing failed with return code {0}".format(returncode))
                return False

            with open(preprocessed_path, 'r') as preprocessed_file:
                preprocessed_content = preprocessed_file.read()

            with open(self.its_file, 'w') as f:
                f.write(preprocessed_content)

            print("Generated ITS file: {0}".format(self.its_file))
            return True
        except (IOError, OSError, subprocess.SubprocessError, Exception) as e:
            return handle_error("processing template", e, False)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(preprocessed_path):
                os.unlink(preprocessed_path)

    def create_fit_image(self):
        """
        Create the FIT image using mkimage.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        try:
            returncode = subprocess.call(
                ['mkimage', '-E', '-f', os.path.basename(self.its_file), os.path.basename(self.img_file)],
                cwd=self.output_dir,
                shell=False
            )

            if returncode != 0:
                print("Error: mkimage command failed with return code {0}".format(returncode))
                return False
            else:
                print("Successfully created FIT image: {0}".format(self.img_file))
        except (subprocess.SubprocessError, Exception) as e:
            return handle_error("executing mkimage command", e, False)

        return True

    def cleanup_temporary_files(self):
        """
        Clean up temporary files created during the FIT image generation
        process. Only deletes files that were specifically created by this
        script execution.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not self.temp_files:
            print("No temporary files to clean up")
            return True

        for file_path in self.temp_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print("Deleted temporary file: {0}".format(os.path.basename(file_path)))
                except (IOError, OSError, Exception) as e:
                    return handle_error("deleting temporary file {0}".format(file_path), e, False)

        return True

    def run(self):
        """
        Run the entire process: parse inputs, generate the .its file, build
        the FIT image, and clean up temporary artifacts.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        try:
            os.makedirs(self.output_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                return handle_error("creating output directory", e)
        except Exception as e:
            return handle_error("creating output directory", e)

        if not self.process_raw_bin_components():
            return False
        if not self.process_elf_components():
            return False
        if not self.process_dpr():
            return False
        if not self.process_dtb():
            return False

        if not self.generate_its_file():
            return False

        if not self.create_fit_image():
            return False

        if not self.cleanup_temporary_files():
            print("Warning: Failed to clean up some temporary files")

        return True


def build_arg_parser():
    """
    Build the command-line argument parser. Flags for every registered
    component (raw-binary and ELF) are generated from RAW_BIN_COMPONENTS
    and ELF_COMPONENTS so the registry stays the single source of truth.

    Returns:
        argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Generate a FIT image from a tag-selected subset of ELF/MBN/binary "
                     "images using a fixed, #if-gated template. Only the components you "
                     "pass a --<name>_path for are included in the output.")
    parser.add_argument('--template', type=str, required=True,
                        help="Path to the template ITS file")
    parser.add_argument('-o', '--output', type=str, required=True,
                        help="Output file path and name (e.g., './out_path/bootldr.img')")
    parser.add_argument('--dtb_path', type=str, help="Path to Device Tree Blob (DTB) file")
    parser.add_argument('--dpr', dest='dpr_path', type=str, default=None,
                        help="Path to DPR ELF file (optional). When provided, the entire ELF is "
                             "included as a single pre-DDR image in the FIT.")
    parser.add_argument('--dpr_addr', type=str, default=None,
                        help="Load address for the DPR image (required if --dpr is supplied)")

    for name in RAW_BIN_COMPONENTS:
        parser.add_argument('--{0}_path'.format(name), type=str, default=None,
                            help="Path to the {0} raw binary".format(name))
        default_addr = RAW_BIN_DEFAULT_ADDR.get(name)
        parser.add_argument('--{0}_addr'.format(name), type=str, default=None,
                            help="Load address for {0} (also used as its entry address). "
                                 "Defaults to the memory-map address {1} if omitted.".format(
                                     name, default_addr))

    for name in ELF_COMPONENTS:
        if name in BIN_ENTRY_ADDRS:
            help_text = ("Path to the {0} ELF/MBN file, or a flat binary (.bin). "
                         "When a .bin is given, load/entry defaults to {1}.".format(
                             name, BIN_ENTRY_ADDRS[name]))
        else:
            help_text = "Path to the {0} ELF/MBN file".format(name)
        parser.add_argument('--{0}_path'.format(name), type=str, default=None,
                            help=help_text)

    return parser


def validate_args(args):
    """
    Validate all paths and addresses supplied on the command line.

    Args:
        args: parsed argparse.Namespace

    Returns:
        bool: True if all arguments are valid, False otherwise
    """
    if not validate_path(args.template):
        print("Error: Invalid template path '{0}'.".format(args.template))
        return False

    output_dir, output_file_base = os.path.split(args.output)
    if output_dir:
        success, _ = sanitize_path(output_dir)
        if not success:
            print("Error: Invalid output directory path '{0}'.".format(output_dir))
            return False
    if output_file_base and not validate_filename(output_file_base):
        print("Error: Invalid output file base name '{0}'.".format(output_file_base))
        return False

    path_args = ['dtb_path', 'dpr_path']
    path_args += ['{0}_path'.format(name) for name in RAW_BIN_COMPONENTS]
    path_args += ['{0}_path'.format(name) for name in ELF_COMPONENTS]

    any_component_given = False
    for arg_name in path_args:
        file_path = getattr(args, arg_name, None)
        if not file_path:
            continue
        if arg_name != 'dtb_path':
            any_component_given = True

        success, normalized_path = sanitize_path(file_path)
        if not success:
            print("Error: Invalid file path '{0}' for {1}.".format(file_path, arg_name))
            return False
        setattr(args, arg_name, normalized_path)

    if not any_component_given:
        print("Error: No image component supplied. Pass at least one --<name>_path "
              "(or --dpr) flag for the image(s) you want in the FIT.")
        return False

    for name in RAW_BIN_COMPONENTS:
        path_val = getattr(args, '{0}_path'.format(name), None)
        addr_val = getattr(args, '{0}_addr'.format(name), None)
        if path_val and not addr_val and name not in RAW_BIN_DEFAULT_ADDR:
            print("Error: --{0}_addr must be supplied ({0} has no default load address).".format(name))
            return False
        if addr_val and not validate_hex_address(addr_val):
            print("Error: --{0}_addr '{1}' is not a valid hex address (e.g. 0x8CB5800).".format(name, addr_val))
            return False

    if args.dpr_path and args.dpr_addr and not validate_hex_address(args.dpr_addr):
        print("Error: --dpr_addr '{0}' is not a valid hex address (e.g. 0x8CB5800).".format(args.dpr_addr))
        return False

    return True


def main():
    """
    Main function that parses command line arguments and orchestrates the
    FIT image generation process.

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    args = build_arg_parser().parse_args()

    if not validate_args(args):
        return False

    generator = FitImageGenerator(args)
    return generator.run()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
