inherit kernel-arch uboot-config

require conf/image-fitimage.conf

DEPENDS += "\
    u-boot-tools-native dtc-native \
    qcom-dtb-metadata \
"

# Initialize root node
python fitimage_init_rootnode() {
    import sys, os
    file_path = d.getVar('FILE')
    customfit = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(file_path))), 'lib')
    if os.path.isdir(customfit) and customfit not in sys.path:
        sys.path.insert(0, customfit)
        bb.note("Added to sys.path (parse-time): %s" % customfit)
    import oe.types
    from qcom_fitimage import QcomItsNodeRootKernel
    root_node = QcomItsNodeRootKernel(
        d.getVar("FIT_DESC"), d.getVar("FIT_ADDRESS_CELLS"),
        d.getVar('HOST_PREFIX'), d.getVar('UBOOT_ARCH'), d.getVar("FIT_CONF_PREFIX"),
        oe.types.boolean(d.getVar('UBOOT_SIGN_ENABLE')), d.getVar("UBOOT_SIGN_KEYDIR"),
        d.getVar("UBOOT_MKIMAGE"), d.getVar("UBOOT_MKIMAGE_DTCOPTS"),
        d.getVar("UBOOT_MKIMAGE_SIGN"), d.getVar("UBOOT_MKIMAGE_SIGN_ARGS"),
        d.getVar('FIT_HASH_ALG'), d.getVar('FIT_SIGN_ALG'), d.getVar('FIT_PAD_ALG'),
        d.getVar('UBOOT_SIGN_KEYNAME'),
        oe.types.boolean(d.getVar('FIT_SIGN_INDIVIDUAL')), d.getVar('UBOOT_SIGN_IMG_KEYNAME')
    )
    d.setVar("__fit_root_node", root_node)
    bb.debug(1, "Global root_node initialized")
}

# Add DTB section
python fitimage_add_dtb_section() {
    import shutil, os
    deploydir = d.getVar('DEPLOY_DIR_IMAGE')
    kerneldeploydir = d.getVar("DEPLOYDIR")
    root_node = d.getVar("__fit_root_node")
    if not root_node:
        bb.fatal("root_node not initialized.")

    # Pass additional options
    root_node.set_extra_opts(d.getVar("UBOOT_MKIMAGE_EXTRA_OPTS"))
    kernel_devicetree = d.getVar('KERNEL_DEVICETREE')

    # Handle qcom metadata
    kernel_devicetree = 'qcom-metadata.dtb ' + kernel_devicetree
    shutil.copy(os.path.join(deploydir, 'qcom-metadata.dtb'), os.path.join(kerneldeploydir, 'qcom-metadata.dtb'))

    if kernel_devicetree:
        for dtb in kernel_devicetree.split():
            dtb_name = os.path.basename(dtb)
            dtb_base = os.path.splitext(dtb_name)[0]
            compatible = d.getVarFlag("FIT_DTB_COMPATIBLE", dtb_base) or ""
            abs_path = os.path.join(deploydir, dtb_name)
            root_node.fitimage_emit_section_dtb(dtb_name, dtb_name,
                d.getVar("UBOOT_DTB_LOADADDRESS"), d.getVar("UBOOT_DTBO_LOADADDRESS"), True,
                compatible_str=compatible, dtb_abspath=abs_path)
}

# Modify ITS file
python fitimage_modify_its_file() {
    import re

    deploy_dir = d.getVar("DEPLOYDIR")
    itsfile = os.path.join(deploy_dir, "fit-image.its")

    with open(itsfile, 'r') as f:
        content = f.read()

    # Replace type as qcom_metadata for qcom-dtb-metadata
    content = re.sub(r'(fdt-qcom-metadata.dtb\s*\{[^}]*?)type\s*=\s*"flat_dt";',
                     r'\1type = "qcom_metadata";', content, flags=re.DOTALL)

    # Replace fdt-qcom-metadata.dtb as fdt-0
    content = re.sub(r'fdt-qcom-metadata\.dtb', 'fdt-0', content)

    # Remove conf-0 entry which corresponds to fdt-0
    content = re.sub(r'conf-0\s*\{[^}]*\};', '', content, flags=re.DOTALL)

    with open(itsfile, 'w') as f:
        f.write(content)
}



python fitimage_add_dtbo() {
    import os, re

    deploy_dir = d.getVar("DEPLOYDIR")
    itsfile = os.path.join(deploy_dir, "fit-image.its")

    # Read the ITS file content
    with open(itsfile, 'r') as f:
        content = f.read()

    # ----------------------------- Helpers -----------------------------------
    def find_configurations_span(s):
        """
        Return (open_brace_idx, close_brace_idx) spanning the 'configurations { ... }' block.
        open_brace_idx points to '{', close_brace_idx points to the matching '}'.
        """
        kw_pos = s.find("configurations")
        if kw_pos < 0:
            return (-1, -1)
        brace_open = s.find("{", kw_pos)
        if brace_open < 0:
            return (-1, -1)
        depth = 0
        for i in range(brace_open, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return (brace_open, i)
        return (-1, -1)

    def next_conf_index(s):
        """Find the max existing conf-<n> and return next free index."""
        nums = [int(n) for n in re.findall(r'\bconf-(\d+)\b', s)]
        return (max(nums) + 1) if nums else 0

    def parse_existing_confs(cfg_body):
        """
        Parse existing conf blocks and return:
          - a set of triples (dtb_token, dtbo_tokens_tuple, compatible) already present
          - a list of (block_text, description) base DTB-only conf blocks for cloning
        """
        seen = set()
        base_templates = []

        # Iterate conf-* blocks
        for m in re.finditer(r'(conf-\d+\s*\{[^}]*\})', cfg_body, flags=re.DOTALL):
            block = m.group(1)

            # Description
            desc_m = re.search(r'^\s*description\s*=\s*"([^"]+)"\s*;', block, flags=re.MULTILINE)
            desc = desc_m.group(1) if desc_m else "0 FDT blob"

            # fdt list
            fdt_m = re.search(r'^\s*fdt\s*=\s*([^;]+);', block, flags=re.MULTILINE)
            if not fdt_m:
                continue
            list_text = fdt_m.group(1)
            tokens = re.findall(r'"([^"]+)"', list_text)
            if not tokens:
                continue

            dtb_token = tokens[0]
            dtbo_tokens = tuple(tokens[1:])  # order matters

            # compatible (optional)
            comp_m = re.search(r'^\s*compatible\s*=\s*"([^"]+)"\s*;', block, flags=re.MULTILINE)
            comp = comp_m.group(1) if comp_m else ""

            # Track seen combinations (to avoid duplicates)
            seen.add((dtb_token, dtbo_tokens, comp))

            # Base templates (DTB-only)
            if len(tokens) == 1:
                base_templates.append((block, desc))

        return seen, base_templates

    # Indentation policy — adjust if you want 16-space conf blocks
    INDENT_CONF = " " * 16         # "" for inline conf start; set to " " * 16 to indent conf line
    INDENT_PROP = " " * 24     # properties aligned at 8 spaces (match your base ITS)
    INDENT_CLOSE = " " * 16    # closing brace aligned at 4 spaces

    def make_conf_block(conf_name, description, dtb_token, dtbo_tokens, compatible):
        """
        Create a new conf-* block string with consistent indentation.
        """
        dtbos_part = ""
        if dtbo_tokens:
            dtbos_part = ", " + ", ".join(f'"{t}"' for t in dtbo_tokens)

        comp_line = ""
        if compatible:
            comp_line = f'\n{INDENT_PROP}compatible = "{compatible}";'

        return (
f"""{INDENT_CONF}{conf_name} {{
{INDENT_PROP}description = "{description}";
{INDENT_PROP}fdt = "{dtb_token}"{dtbos_part};{comp_line}
{INDENT_CLOSE}}};
""")

    # ---------------------- Locate configurations block ----------------------
    cfg_open, cfg_close = find_configurations_span(content)
    if cfg_open < 0:
        bb.fatal("fitimage_add_dtbo: Could not locate 'configurations { ... }' block in ITS.")

    # Extract inner content only
    cfg_body = content[cfg_open + 1:cfg_close]

    # Parse existing confs to avoid duplicates and to find base templates
    seen_triples, base_blocks = parse_existing_confs(cfg_body)
    new_conf_texts = []
    conf_index = next_conf_index(content)

    # -------------------------- Build new confs ------------------------------
    kernel_devicetree = d.getVar('KERNEL_DEVICETREE') or ""
    for dtb in kernel_devicetree.split():
        dtb_name = os.path.basename(dtb)
        if not dtb_name.endswith(".dtb"):
            continue  # skip overlays here

        dtb_base = os.path.splitext(dtb_name)[0]
        dtb_token = f'fdt-{dtb_name}'

        # Base DTB-only conf blocks to clone
        # Filter templates that match this DTB token
        base_blocks_for_this = []
        for block, desc in base_blocks:
            fdt_m = re.search(r'^\s*fdt\s*=\s*([^;]+);', block, flags=re.MULTILINE)
            tokens = re.findall(r'"([^"]+)"', fdt_m.group(1)) if fdt_m else []
            if tokens and tokens[0] == dtb_token and len(tokens) == 1:
                base_blocks_for_this.append((block, desc))

        if not base_blocks_for_this:
            bb.note(f"fitimage_add_dtbo: No base DTB-only conf found for {dtb_name}, skipping DTBO variants.")
            continue

        # DTBO sets: allow grouping by ';' or newline
        dtbos_val = d.getVarFlag("KERNEL_TECH_DTBOS", dtb_base) or ""
        group_strs = [g.strip() for g in re.split(r'[;\n]+', dtbos_val) if g.strip()]
        if not group_strs:
            continue

        # Convert each group into a list of "fdt-<dtbo>" tokens (keep only .dtbo files)
        dtbo_sets = []
        for g in group_strs:
            toks = [os.path.basename(x) for x in g.split() if x]
            toks = [x for x in toks if x.endswith(".dtbo")]
            if toks:
                dtbo_sets.append([f"fdt-{x}" for x in toks])

        if not dtbo_sets:
            continue

        # DTBO-set-specific compatible strings, group-aligned by position with dtbo_sets
        raw_dtbo_comp = (d.getVarFlag("FIT_DTB_DTBO_COMPATIBLE", dtb_base) or "").strip()
        comp_groups = [g.strip() for g in re.split(r'[;\n]+', raw_dtbo_comp)] if raw_dtbo_comp else []

        # Fallback base compatibles if no DTBO-specific override is provided
        base_compats = (d.getVarFlag("FIT_DTB_COMPATIBLE", dtb_base) or "").split()

        # Emit new confs: for each base conf, each DTBO set, each compatible in that set
        for (_, description) in base_blocks_for_this:
            for set_idx, dtbo_tokens in enumerate(dtbo_sets):
                # Compatibles for this DTBO set (group-aligned, else fallback)
                if set_idx < len(comp_groups) and comp_groups[set_idx]:
                    dtbo_compats = comp_groups[set_idx].split()  # space-separated inside the group
                else:
                    dtbo_compats = base_compats or [""]  # empty string → omit compatible line

                dtbo_tokens_tuple = tuple(dtbo_tokens)

                for comp in dtbo_compats:
                    triple = (dtb_token, dtbo_tokens_tuple, comp)
                    if triple in seen_triples:
                        # Already present; skip duplicate
                        continue

                    conf_name = f"conf-{conf_index}"
                    conf_index += 1
                    new_conf_texts.append(
                        make_conf_block(conf_name, description, dtb_token, dtbo_tokens, comp)
                    )
                    # Track as seen to avoid duplicates across multiple base_blocks
                    seen_triples.add(triple)

    # ----------------------- Write updated ITS content -----------------------
    if new_conf_texts:
        # IMPORTANT: only replace inner content; preserve braces and avoid extra '};'
        updated_cfg_body = cfg_body.rstrip() + "\n" + "".join(new_conf_texts)
        content = content[:cfg_open + 1] + updated_cfg_body + content[cfg_close:]
        with open(itsfile, 'w') as f:
            f.write(content)
        bb.note("fitimage_add_dtbo: added %d new conf entries for DTBO sets." % len(new_conf_texts))
    else:
        bb.note("fitimage_add_dtbo: no DTBO-based confs to add.")
}




# Generate ITS and FIT image
python fitimage_generate_its() {
    deploy_dir = d.getVar("DEPLOYDIR")
    itsfile = os.path.join(deploy_dir, "fit-image.its")
    fitname = os.path.join(deploy_dir, "fitImage")

    bb.build.exec_func('fitimage_init_rootnode', d)
    bb.build.exec_func('fitimage_add_dtb_section', d)
    root_node = d.getVar("__fit_root_node")
    root_node.fitimage_emit_section_config(d.getVar("FIT_CONF_DEFAULT_DTB"))
    root_node.write_its_file(itsfile)
    bb.build.exec_func('fitimage_modify_its_file', d)
    bb.build.exec_func('fitimage_add_dtbo', d)
    root_node.run_mkimage_assemble(itsfile, fitname)
    root_node.run_mkimage_sign(fitname)
}

do_compile_qcom_fitimage[depends] += "qcom-dtb-metadata:do_deploy"

python do_compile_qcom_fitimage() {
    bb.build.exec_func('fitimage_generate_its', d)
}


do_deploy_qcom_fitimage() {
    install -m 0644 "${DEPLOYDIR}/fitImage" "${DEPLOY_DIR_IMAGE}/fitImage"
    install -m 0644 "${DEPLOYDIR}/fit-image.its" "${DEPLOY_DIR_IMAGE}/fit-image.its"
}
addtask compile_qcom_fitimage after do_deploy
addtask deploy_qcom_fitimage after do_compile_qcom_fitimage do_deploy
