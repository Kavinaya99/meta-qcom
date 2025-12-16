
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# Copyright OpenEmbedded Contributors
#
# SPDX-License-Identifier: GPL-2.0-only
#
# This file contains functions for Qualcomm-specific DTB-only FIT image generation,
# which imports classes from OE-Core fitimage.py and enhances to meet Qualcomm FIT
# specifications.
#
# For details on Qualcomm DTB metadata and FIT requirements, see:
# https://github.com/qualcomm-linux/qcom-dtb-metadata/blob/main/Documentation.md

import os
import shlex
import subprocess
import bb
from typing import Tuple
from oe.fitimage import ItsNodeRootKernel, ItsNodeConfiguration, get_compatible_from_dtb

# Custom extension of ItsNodeRootKernel to inject compatible strings
class QcomItsNodeRoot(ItsNodeRootKernel):

    def __init__(self, description, address_cells, conf_prefix, mkimage=None, datastore=None):
        # We only pass the essential parameters needed for QCOM DTB-only FIT image generation
        # because FIT features like signing, hashing, and padding are not required here.
        # Original full signature for reference:
        # super().__init__(description, address_cells, host_prefix, arch, conf_prefix,
        #                  sign_enable, sign_keydir, mkimage, mkimage_dtcopts,
        #                  mkimage_sign, mkimage_sign_args, hash_algo, sign_algo,
        #                  pad_algo, sign_keyname_conf, sign_individual, sign_keyname_img
        super().__init__(description, address_cells, None, "arm64", conf_prefix,
                         False, None, mkimage, None,
                         None, None, None, None,
                         None, None, False, None)

        self._mkimage_extra_opts = []
        self._dtbs = []
        self._d = datastore

    def set_extra_opts(self, mkimage_extra_opts):
        self._mkimage_extra_opts = shlex.split(mkimage_extra_opts) if mkimage_extra_opts else []

    # Emit the DTB section for the FIT image
    def fitimage_emit_section_dtb(self, dtb_id, dtb_path,
                                  compatible_str=None):
        load = None
        dtb_ext = os.path.splitext(dtb_path)[1]

        opt_props = {
            "data": '/incbin/("' + dtb_path + '")',
            "arch": self._arch
        }
        if load:
            opt_props["load"] = f"&lt;{load}&gt;"

        if dtb_id == "qcom-metadata.dtb":
            dtb_type = "qcom_metadata"
        else:
            dtb_type = "flat_dt"

        dtb_node = self.its_add_node_dtb(
            "fdt-" + dtb_id,
            "Flattened Device Tree blob",
            dtb_type,
            "none",
            opt_props,
            compatible_str
        )
        self._dtbs.append(dtb_node)

    def _fitimage_emit_one_section_config(self, conf_node_name, dtb=None):
        """Emit the fitImage ITS configuration section"""
        opt_props = {}
        conf_desc = []

        if dtb:
            conf_desc.append("FDT blob")
            opt_props["fdt"] = dtb.name
            if dtb.compatible:
                opt_props["compatible"] = dtb.compatible

        conf_node = ItsNodeConfiguration(
            conf_node_name,
            self.configurations,
            description="FDT Blob",
            opt_props=opt_props
        )

    def fitimage_emit_section_config(self, default_dtb_image=None):
        d = self._d
        conf_idx = 1
        for dtb_pos, dtb_node in enumerate(self._dtbs):
            # conf-0 corresponds to qcom-metadata.dtb, skipping it as it's metadata-only
            if dtb_pos == 0:
                continue

            # Add conf- entries only for dtb
            if dtb_node.name.endswith(".dtb"):
                conf_name = f"{self._conf_prefix}{conf_idx}"
                self._fitimage_emit_one_section_config(conf_name, dtb_node)

                dtb_name = dtb_node.name
                if dtb_name.startswith("fdt-"):
                    dtb_name = dtb_name[len("fdt-"):]
                if dtb_name.endswith(".dtb"):
                    dtb_name = dtb_name[:-len(".dtb")]
                base_dtb = dtb_name

                # Get the overlays for a given base DTB
                overlays = d.getVarFlag("OVERLAY_DTBOS", base_dtb) or ""
                overlay_dtbos = [g.strip() for g in overlays.split(";") if g.strip()]

                compatibles = d.getVarFlag("FIT_DTB_DTBO_COMPATIBLE", base_dtb) or ""
                dtbo_compatible_strings = [s.strip() for s in compatibles.split(";") if s.strip()]

                # Generate conf entries for DTBOs alongwith their corresponding DTB
                for idx, overlay in enumerate(overlay_dtbos):
                    items = [tok for tok in overlay.split() if tok]
                    fdt_base = f"fdt-{base_dtb}.dtb"
                    fdt_ovls = []
                    for it in items:
                        name = it
                        if not name.startswith("fdt-"):
                            name = f"fdt-{name}"
                        if not name.endswith(".dtbo"):
                            name = f"{name}.dtbo"
                        fdt_ovls.append(name)

                    fdtentries = [fdt_base] + fdt_ovls
                    conf_idx += 1
                    conf_name = f"{self._conf_prefix}{conf_idx}"
                    self._fitimage_emit_one_section_config(conf_name, dtb_node)

                    compat_str = dtbo_compatible_strings[idx] if idx < len(dtbo_compatible_strings) else ""

                    conf_node = self.configurations.sub_nodes[-1]
                    conf_node.add_property('fdt', fdtentries)
                    conf_node.add_property('compatible', compat_str)
                conf_idx += 1

    # Override mkimage assemble to inject extra opts
    def run_mkimage_assemble(self, itsfile, fitfile):
        cmd = [self._mkimage, *self._mkimage_extra_opts, '-f', itsfile, fitfile]
        if self._mkimage_dtcopts:
            cmd.insert(1, '-D')
            cmd.insert(2, self._mkimage_dtcopts)

        bb.note(f"Running mkimage with extra opts: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            bb.fatal(
                f"Command '{' '.join(cmd)}' failed with return code {e.returncode}\n"
                f"stdout: {e.stdout.decode()}\n"
                f"stderr: {e.stderr.decode()}\n"
                f"itsfile: {os.path.abspath(itsfile)}"
                )
