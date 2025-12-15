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
from typing import Optional, Any, List, Tuple

from oe.fitimage import (
    ItsNodeRootKernel,
    ItsNodeConfiguration,
)

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
        self._mkimage_extra_opts: List[str] = []
        self._dtbs: List[Tuple[Any, List[str]]] = []
        self._d = datastore  # BitBake datastore (d)

    def set_extra_opts(self, mkimage_extra_opts):
        self._mkimage_extra_opts = shlex.split(mkimage_extra_opts) if mkimage_extra_opts else []

    # Emit DTB/DTBO image node (unchanged except metadata kept)
    def fitimage_emit_section_dtb(self, dtb_id, dtb_path, dtb_loadaddress=None,
                                  dtbo_loadaddress=None, add_compatible=False,
                                  compatible_str=None, dtb_abspath=None):
        load = None
        dtb_ext = os.path.splitext(dtb_path)[1]
        if dtb_ext == ".dtbo":
            if dtbo_loadaddress:
                load = dtbo_loadaddress
        elif dtb_loadaddress:
            load = dtb_loadaddress

        opt_props = {
            "data": '/incbin/("' + dtb_path + '")',
            "arch": self._arch,
        }
        if load:
            opt_props["load"] = f"<{load}>"

        compatibles = None
        if add_compatible and compatible_str:
            compatibles = str(compatible_str).split()

        dtb_node = self.its_add_node_dtb(
            "fdt-" + dtb_id,
            "Flattened Device Tree blob",
            "flat_dt",
            "none",
            opt_props,
            compatibles
        )
        self._dtbs.append((dtb_node, compatibles or []))

    def _fitimage_emit_one_section_config(self,
                                          conf_node_name: str,
                                          dtb: Optional[Any] = None,
                                          compat_override: Optional[str] = None):
        opt_props = {}
        conf_desc = []

        if dtb:
            conf_desc.append("FDT blob")
            if isinstance(dtb, (list, tuple)):
                # multi-FDT entries: base + one or more dtbos
                opt_props["fdt"] = list(dtb)
            elif hasattr(dtb, "name"):
                opt_props["fdt"] = dtb.name
                if getattr(dtb, "compatible", None) and not compat_override:
                    opt_props["compatible"] = dtb.compatible
            elif isinstance(dtb, str):
                opt_props["fdt"] = dtb
            else:
                raise TypeError(f"Unsupported dtb type in config: {type(dtb)}")

            if self._sign_enable:
                sign_entries.append("fdt")

        if compat_override:
            opt_props["compatible"] = compat_override

        # First configuration becomes default (same as upstream)
        default_flag = "1" if len(self.configurations.sub_nodes) == 0 else "0"

        conf_node = ItsNodeConfiguration(
            conf_node_name,
            self.configurations,
            f"{default_flag} {', '.join(conf_desc) if conf_desc else ''}".strip(),
            opt_props=opt_props
        )

    # Configurations for base DTBs with DTBO groups
    def fitimage_emit_section_config(self, default_dtb_image=None):
        d = self._d
        if d is None:
            # Fall back to upstream if no datastore provided
            return super().fitimage_emit_section_config(default_dtb_image)

        def split_semicolon(s: str):
            return [x.strip() for x in (s or "").split(";") if x.strip()]

        def split_space(s: str):
            return [x.strip() for x in (s or "").split() if x.strip()]

        kernel_devicetree = d.getVar('KERNEL_DEVICETREE') or ""

        # Preserve order; ignore qcom-metadata.dtb
        base_dtbs: List[str] = []
        for item in kernel_devicetree.split():
            name = os.path.basename(item)
            if name.endswith(".dtb") and name != "qcom-metadata.dtb":
                base_dtbs.append(os.path.splitext(name)[0])

        conf_counter = 1
        for base in base_dtbs:
            base_label = f"fdt-{base}.dtb"
            base_compat = d.getVarFlag("FIT_DTB_COMPATIBLE", base) or ""

            # Base-only config
            self._fitimage_emit_one_section_config(
                f"{self._conf_prefix}{conf_counter}",
                dtb=base_label,
                compat_override=(base_compat or None)
            )
            conf_counter += 1

            # DTBO groups: each group may contain multiple DTBOs.
            dtbo_groups = split_semicolon(d.getVarFlag("OVERLAY_DTBOS", base) or "")
            compat_groups = split_semicolon(d.getVarFlag("FIT_DTB_DTBO_COMPATIBLE", base) or "")

            for idx, group in enumerate(dtbo_groups):
                dtbos = split_space(group)  
                fdt_list = [base_label] + [f"fdt-{x}" for x in dtbos]
                compat_val = compat_groups[idx] if idx < len(compat_groups) else (base_compat or None)

                self._fitimage_emit_one_section_config(
                    f"{self._conf_prefix}{conf_counter}",
                    dtb=fdt_list,
                    compat_override=compat_val
                )
                conf_counter += 1

        # Default configuration name
        default_conf = self.configurations.sub_nodes[0].name if self.configurations.sub_nodes else f"{self._conf_prefix}1"
        if default_dtb_image and base_dtbs:
            default_conf = self._conf_prefix + str(default_dtb_image)
        self.configurations.add_property('default', default_conf)

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
