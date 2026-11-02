# Copyright (c) 2026 Qualcomm Innovation Center, Inc. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Qualcomm extension of uboot-sign.bbclass for SPL boot flows.
#
# uboot-sign.bbclass emits the uboot, fdt, atf and tee image nodes and a
# single configuration. Qualcomm SPL flows also need the pre-DDR payloads
# and a second configuration. 
#
inherit uboot-sign

# PMIC configuration data.
UBOOT_FIT_PMIC_COCOS ?= "0"
UBOOT_FIT_PMIC_COCOS_IMAGE ?= "pmic_cocos.bin"
UBOOT_FIT_PMIC_COCOS_OS ?= "elf"
UBOOT_FIT_PMIC_COCOS_ENTRYPOINT ?= "${UBOOT_FIT_PMIC_COCOS_LOADADDRESS}"

UBOOT_FIT_PMIC_WAILUA ?= "0"
UBOOT_FIT_PMIC_WAILUA_IMAGE ?= "pmic_wailua.bin"
UBOOT_FIT_PMIC_WAILUA_OS ?= ""
UBOOT_FIT_PMIC_WAILUA_ENTRYPOINT ?= "${UBOOT_FIT_PMIC_WAILUA_LOADADDRESS}"

# DDR configuration blocks.
UBOOT_FIT_DCB_LP4 ?= "0"
UBOOT_FIT_DCB_LP4_IMAGE ?= "dcb_lp4.bin"
UBOOT_FIT_DCB_LP4_OS ?= ""
UBOOT_FIT_DCB_LP4_ENTRYPOINT ?= "${UBOOT_FIT_DCB_LP4_LOADADDRESS}"

UBOOT_FIT_DCB_LP5 ?= "0"
UBOOT_FIT_DCB_LP5_IMAGE ?= "dcb_lp5.bin"
UBOOT_FIT_DCB_LP5_OS ?= ""
UBOOT_FIT_DCB_LP5_ENTRYPOINT ?= "${UBOOT_FIT_DCB_LP5_LOADADDRESS}"

# DDR ECC configuration data.
UBOOT_FIT_ECC ?= "0"
UBOOT_FIT_ECC_IMAGE ?= "ecc.bin"
UBOOT_FIT_ECC_OS ?= ""
UBOOT_FIT_ECC_ENTRYPOINT ?= "${UBOOT_FIT_ECC_LOADADDRESS}"

# SHRM firmware 
UBOOT_FIT_SHRM ?= "0"
UBOOT_FIT_SHRM_IMAGE ?= "shrm.elf"
UBOOT_FIT_SHRM_ARCH ?= "riscv"
UBOOT_FIT_SHRM_OS ?= ""
UBOOT_FIT_SHRM_MAX_SEGMENTS ?= "2"

UBOOT_FIT_QCLIB ?= "0"
UBOOT_FIT_QCLIB_IMAGE ?= "QcLib.elf"
UBOOT_FIT_QCLIB_ARCH ?= "${UBOOT_ARCH}"
UBOOT_FIT_QCLIB_OS ?= "elf"
UBOOT_FIT_QCLIB_MAX_SEGMENTS ?= "2"

# RPM firmware.
UBOOT_FIT_RPM ?= "0"
UBOOT_FIT_RPM_IMAGE ?= "rpm.mbn"
UBOOT_FIT_RPM_ARCH ?= "${UBOOT_ARCH}"
UBOOT_FIT_RPM_OS ?= ""
UBOOT_FIT_RPM_MAX_SEGMENTS ?= "2"

# Image file used for the uboot node. Upstream always pairs the no-DTB
# binary with a separate fdt node. Qualcomm SPL flows boot the combined
# binary, which already carries the appended DTB, so no fdt node is
# emitted.
UBOOT_FIT_UBOOT_IMAGE ?= "${UBOOT_BINARY}"

# Pre-DDR configuration.
UBOOT_FIT_PRE_DDR ?= "0"
UBOOT_FIT_PRE_DDR_CONF ?= "pre-ddr-config"
UBOOT_FIT_PRE_DDR_CONF_DESC ?= "pre-ddr"

UBOOT_FIT_CONF ?= "conf"
UBOOT_FIT_DEFAULT_CONF ?= "${UBOOT_FIT_CONF}"

python() {
    for payload in ('PMIC_COCOS', 'PMIC_WAILUA', 'DCB_LP4', 'DCB_LP5', 'ECC'):
        if d.getVar('UBOOT_FIT_%s' % payload) != '1':
            continue
        if not d.getVar('UBOOT_FIT_%s_LOADADDRESS' % payload):
            bb.fatal("UBOOT_FIT_%s is enabled but "
                     "UBOOT_FIT_%s_LOADADDRESS is empty" % (payload, payload))

    if d.getVar('UBOOT_FITIMAGE_ENABLE') != '1':
        bb.fatal("uboot-qcom-sign requires UBOOT_FITIMAGE_ENABLE = \"1\"")
}

# Create a ITS file for the pmic_cocos
uboot_fitimage_pmic_cocos() {
	cat << EOF >> ${UBOOT_ITS}
		pmic_cocos {
			description = "pmic_cocos";
			data = /incbin/("${UBOOT_FIT_PMIC_COCOS_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
EOF
	if [ -n "${UBOOT_FIT_PMIC_COCOS_OS}" ] ; then
		echo "			os = \"${UBOOT_FIT_PMIC_COCOS_OS}\";" >> ${UBOOT_ITS}
	fi
	cat << EOF >> ${UBOOT_ITS}
			load = <${UBOOT_FIT_PMIC_COCOS_LOADADDRESS}>;
			entry = <${UBOOT_FIT_PMIC_COCOS_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the pmic_wailua
uboot_fitimage_pmic_wailua() {
	cat << EOF >> ${UBOOT_ITS}
		pmic_wailua {
			description = "pmic_wailua";
			data = /incbin/("${UBOOT_FIT_PMIC_WAILUA_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
EOF
	if [ -n "${UBOOT_FIT_PMIC_WAILUA_OS}" ] ; then
		echo "			os = \"${UBOOT_FIT_PMIC_WAILUA_OS}\";" >> ${UBOOT_ITS}
	fi
	cat << EOF >> ${UBOOT_ITS}
			load = <${UBOOT_FIT_PMIC_WAILUA_LOADADDRESS}>;
			entry = <${UBOOT_FIT_PMIC_WAILUA_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the dcb_lp4
uboot_fitimage_dcb_lp4() {
	cat << EOF >> ${UBOOT_ITS}
		dcb_lp4 {
			description = "dcb_lp4";
			data = /incbin/("${UBOOT_FIT_DCB_LP4_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
EOF
	if [ -n "${UBOOT_FIT_DCB_LP4_OS}" ] ; then
		echo "			os = \"${UBOOT_FIT_DCB_LP4_OS}\";" >> ${UBOOT_ITS}
	fi
	cat << EOF >> ${UBOOT_ITS}
			load = <${UBOOT_FIT_DCB_LP4_LOADADDRESS}>;
			entry = <${UBOOT_FIT_DCB_LP4_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the dcb_lp5
uboot_fitimage_dcb_lp5() {
	cat << EOF >> ${UBOOT_ITS}
		dcb_lp5 {
			description = "dcb_lp5";
			data = /incbin/("${UBOOT_FIT_DCB_LP5_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
EOF
	if [ -n "${UBOOT_FIT_DCB_LP5_OS}" ] ; then
		echo "			os = \"${UBOOT_FIT_DCB_LP5_OS}\";" >> ${UBOOT_ITS}
	fi
	cat << EOF >> ${UBOOT_ITS}
			load = <${UBOOT_FIT_DCB_LP5_LOADADDRESS}>;
			entry = <${UBOOT_FIT_DCB_LP5_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the ecc
uboot_fitimage_ecc() {
	cat << EOF >> ${UBOOT_ITS}
		ecc {
			description = "ecc";
			data = /incbin/("${UBOOT_FIT_ECC_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
EOF
	if [ -n "${UBOOT_FIT_ECC_OS}" ] ; then
		echo "			os = \"${UBOOT_FIT_ECC_OS}\";" >> ${UBOOT_ITS}
	fi
	cat << EOF >> ${UBOOT_ITS}
			load = <${UBOOT_FIT_ECC_LOADADDRESS}>;
			entry = <${UBOOT_FIT_ECC_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Split an ELF payload into one image node per PT_LOAD segment.
#
#   $1 node name prefix
#   $2 ELF file
#   $3 arch property
#   $4 os property, emitted on the first node only, may be empty
#   $5 maximum permitted number of PT_LOAD segments
#   $6 entry rule, first_only or own_load, defaults to first_only
#
# Each non-empty PT_LOAD segment is extracted to
# <prefix>_<N>_load_segment.bin using its p_offset and p_filesz.
#
# The node load address is p_paddr. The ELF entry point is expressed in the
# virtual address space, so it is translated into the physical address
# space using the segment that contains it. The translated entry point is
# emitted on the first node only.
#
# The node load address is p_paddr. The ELF entry point is expressed in the
# virtual address space, so it is translated into the physical address
# space using the segment that contains it, and is emitted on the first
# node only, which is where the SPL enters the payload.
#
# Under the own_load entry rule the translated entry point is not used at
# all: every node is given an entry property equal to its own load
# address, for a payload whose segments are entered individually.
#
# Appends the generated node names to conf_pre_loadables, or to
# conf_loadables under the own_load entry rule, which only the post-DDR
# payloads use.
uboot_fitimage_elf() {
	elf_name="$1"
	elf_file="$2"
	elf_arch="$3"
	elf_os="$4"
	elf_max="$5"
	elf_rule="$6"

	if [ -z "${elf_rule}" ] ; then
		elf_rule="first_only"
	fi

	if [ ! -e "${elf_file}" ] ; then
		bbfatal "${elf_file} is missing; the recipe must stage it before do_uboot_assemble_fitimage"
	fi

	# Remove the segments of a previous build so that a payload with fewer
	# segments cannot leave stale files behind.
	rm -f ${elf_name}_*_load_segment.bin

	elf_entry=$(${READELF} -hW "${elf_file}" | awk '/Entry point address:/ { print $NF }')
	if [ -z "${elf_entry}" ] ; then
		bbfatal "could not read the entry point of ${elf_file}"
	fi

	# All arithmetic is done here, because the BitBake shell parser does
	# not accept arithmetic expansion. One record per non-empty PT_LOAD
	# segment, as index:offset:filesz:memsz:load:entry with the decimal
	# values first and the formatted addresses last.
	#
	# The ELF entry point is expressed in the virtual address space, so it
	# is translated into the physical address space using the segment that
	# contains it.
	${READELF} -lW "${elf_file}" | awk -v entry="${elf_entry}" 'BEGIN { n = 0 } $1 == "LOAD" { off[n] = strtonum($2); va[n] = strtonum($3); pa[n] = strtonum($4); fs[n] = strtonum($5); ms[n] = strtonum($6); n = n + 1 } END { e = strtonum(entry); ep = -1; for (i = 0; i < n; i = i + 1) { if (fs[i] == 0 && ms[i] == 0) continue; if (ep < 0 && e >= va[i] && e < va[i] + ms[i]) ep = pa[i] + e - va[i] } if (ep < 0) { printf "entry-not-in-pt-load\n" > "/dev/stderr"; ep = e } idx = 0; for (i = 0; i < n; i = i + 1) { if (fs[i] == 0 && ms[i] == 0) continue; idx = idx + 1; printf "%d:%d:%d:%d:0x%X:0x%X\n", idx, off[i], fs[i], ms[i], pa[i], ep } }' > ${elf_name}.segments

	elf_count=$(wc -l < ${elf_name}.segments)
	if [ "${elf_count}" -eq 0 ] ; then
		bbfatal "${elf_file} has no non-empty PT_LOAD segments"
	fi
	if [ "${elf_count}" -gt "${elf_max}" ] ; then
		bbfatal "${elf_file} has ${elf_count} PT_LOAD segments, more than the permitted ${elf_max}"
	fi

	for elf_record in $(cat ${elf_name}.segments) ; do
		elf_index=$(echo ${elf_record} | cut -d: -f1)
		elf_offset=$(echo ${elf_record} | cut -d: -f2)
		elf_filesz=$(echo ${elf_record} | cut -d: -f3)
		elf_memsz=$(echo ${elf_record} | cut -d: -f4)
		elf_load=$(echo ${elf_record} | cut -d: -f5)
		elf_entry_paddr=$(echo ${elf_record} | cut -d: -f6)

		if [ "${elf_memsz}" -lt "${elf_filesz}" ] ; then
			bbfatal "${elf_file} segment ${elf_index} has p_memsz smaller than p_filesz"
		fi

		elf_segment="${elf_name}_${elf_index}_load_segment.bin"
		dd if="${elf_file}" of="${elf_segment}" bs=1M iflag=skip_bytes,count_bytes skip=${elf_offset} count=${elf_filesz} status=none

		printf '\t\t%s_%s {\n' "${elf_name}" "${elf_index}" >> ${UBOOT_ITS}
		printf '\t\t\tdescription = "%s%s";\n' "${elf_name}" "${elf_index}" >> ${UBOOT_ITS}
		printf '\t\t\tdata = /incbin/("%s");\n' "${elf_segment}" >> ${UBOOT_ITS}
		printf '\t\t\ttype = "firmware";\n' >> ${UBOOT_ITS}
		printf '\t\t\tarch = "%s";\n' "${elf_arch}" >> ${UBOOT_ITS}
		if [ "${elf_index}" -eq 1 ] && [ -n "${elf_os}" ] ; then
			printf '\t\t\tos = "%s";\n' "${elf_os}" >> ${UBOOT_ITS}
		fi
		printf '\t\t\tload = <%s>;\n' "${elf_load}" >> ${UBOOT_ITS}
		if [ "${elf_rule}" = "own_load" ] ; then
			printf '\t\t\tentry = <%s>;\n' "${elf_load}" >> ${UBOOT_ITS}
		elif [ "${elf_index}" -eq 1 ] ; then
			printf '\t\t\tentry = <%s>;\n' "${elf_entry_paddr}" >> ${UBOOT_ITS}
		fi
		printf '\t\t\tcompression = "none";\n' >> ${UBOOT_ITS}
		printf '\t\t};\n' >> ${UBOOT_ITS}

		if [ "${elf_rule}" = "own_load" ] ; then
			conf_loadables="${conf_loadables} ${elf_name}_${elf_index}"
		else
			conf_pre_loadables="${conf_pre_loadables} ${elf_name}_${elf_index}"
		fi
	done

	rm -f ${elf_name}.segments
}

# Create a ITS file for the shrm
uboot_fitimage_shrm() {
	uboot_fitimage_elf \
		shrm \
		"${UBOOT_FIT_SHRM_IMAGE}" \
		"${UBOOT_FIT_SHRM_ARCH}" \
		"${UBOOT_FIT_SHRM_OS}" \
		"${UBOOT_FIT_SHRM_MAX_SEGMENTS}"
}

# Create a ITS file for the qclib
uboot_fitimage_qclib() {
	uboot_fitimage_elf \
		qclib \
		"${UBOOT_FIT_QCLIB_IMAGE}" \
		"${UBOOT_FIT_QCLIB_ARCH}" \
		"${UBOOT_FIT_QCLIB_OS}" \
		"${UBOOT_FIT_QCLIB_MAX_SEGMENTS}"
}

# Create a ITS file for the rpm
uboot_fitimage_rpm() {
	uboot_fitimage_elf \
		rpm \
		"${UBOOT_FIT_RPM_IMAGE}" \
		"${UBOOT_FIT_RPM_ARCH}" \
		"${UBOOT_FIT_RPM_OS}" \
		"${UBOOT_FIT_RPM_MAX_SEGMENTS}" \
		own_load
}

# Create a ITS file for the tfa_bl31
#
# This is uboot_fitimage_atf() from uboot-sign.bbclass with the node name
# changed to the name the Qualcomm SPL flow expects.
uboot_fitimage_tfa_bl31() {
	cat << EOF >> ${UBOOT_ITS}
		tfa_bl31 {
			description = "ARM Trusted Firmware";
			data = /incbin/("${UBOOT_FIT_ARM_TRUSTED_FIRMWARE_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
			os = "arm-trusted-firmware";
			load = <${UBOOT_FIT_ARM_TRUSTED_FIRMWARE_LOADADDRESS}>;
			entry = <${UBOOT_FIT_ARM_TRUSTED_FIRMWARE_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the uboot
#
# This is the uboot node of the upstream uboot_fitimage_assemble(), moved
# into its own function so that the pre-DDR nodes can be emitted first.
uboot_fitimage_uboot() {
	cat << EOF >> ${UBOOT_ITS}
		uboot {
			description = "U-Boot image";
			data = /incbin/("${UBOOT_FIT_UBOOT_IMAGE}");
			type = "standalone";
			arch = "${UBOOT_ARCH}";
			os = "u-boot";
			load = <${UBOOT_FIT_UBOOT_LOADADDRESS}>;
			entry = <${UBOOT_FIT_UBOOT_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# Create a ITS file for the optee
#
# This is uboot_fitimage_tee() from uboot-sign.bbclass with the node name
# and the image type changed. The Qualcomm SPL loads OP-TEE as a firmware
# payload rather than through the FIT tee image type.
uboot_fitimage_optee() {
	cat << EOF >> ${UBOOT_ITS}
		optee {
			description = "Trusted Execution Environment";
			data = /incbin/("${UBOOT_FIT_TEE_IMAGE}");
			type = "firmware";
			arch = "${UBOOT_ARCH}";
			os = "tee";
			load = <${UBOOT_FIT_TEE_LOADADDRESS}>;
			entry = <${UBOOT_FIT_TEE_ENTRYPOINT}>;
			compression = "none";
		};
EOF
}

# This overrides uboot_fitimage_assemble() from uboot-sign.bbclass.
uboot_fitimage_assemble() {
	conf_loadables="uboot"
	conf_pre_loadables=""
	conf_firmware=""

	rm -f ${UBOOT_ITS} ${UBOOT_FITIMAGE_BINARY}

	cat << EOF >> ${UBOOT_ITS}
/dts-v1/;

/ {
	description = "${UBOOT_FIT_DESC}";
	#address-cells = <${UBOOT_FIT_ADDRESS_CELLS}>;

	images {
EOF

	if [ "${UBOOT_FIT_PRE_DDR}" = "1" ] ; then
		if [ "${UBOOT_FIT_PMIC_COCOS}" = "1" ] ; then
			conf_pre_loadables="${conf_pre_loadables} pmic_cocos"
			uboot_fitimage_pmic_cocos
		fi

		if [ "${UBOOT_FIT_PMIC_WAILUA}" = "1" ] ; then
			conf_pre_loadables="${conf_pre_loadables} pmic_wailua"
			uboot_fitimage_pmic_wailua
		fi

		if [ "${UBOOT_FIT_DCB_LP4}" = "1" ] ; then
			conf_pre_loadables="${conf_pre_loadables} dcb_lp4"
			uboot_fitimage_dcb_lp4
		fi

		if [ "${UBOOT_FIT_DCB_LP5}" = "1" ] ; then
			conf_pre_loadables="${conf_pre_loadables} dcb_lp5"
			uboot_fitimage_dcb_lp5
		fi

		if [ "${UBOOT_FIT_ECC}" = "1" ] ; then
			conf_pre_loadables="${conf_pre_loadables} ecc"
			uboot_fitimage_ecc
		fi

		# These append to conf_pre_loadables themselves, one entry per
		# generated PT_LOAD segment node.
		if [ "${UBOOT_FIT_SHRM}" = "1" ] ; then
			uboot_fitimage_shrm
		fi

		if [ "${UBOOT_FIT_QCLIB}" = "1" ] ; then
			uboot_fitimage_qclib
		fi
	fi

	if [ "${UBOOT_FIT_ARM_TRUSTED_FIRMWARE}" = "1" ] ; then
		if [ "${UBOOT_FIT_CONF_FIRMWARE}" != "tfa_bl31" ] ; then
			conf_loadables="tfa_bl31 ${conf_loadables}"
		fi
		uboot_fitimage_tfa_bl31
	fi

	if [ "${UBOOT_FIT_RPM}" = "1" ] ; then
		uboot_fitimage_rpm
	fi

	uboot_fitimage_uboot

	if [ "${UBOOT_FIT_TEE}" = "1" ] ; then
		conf_loadables="${conf_loadables} optee"
		uboot_fitimage_optee
	fi

	if [ -n "${UBOOT_FIT_USER_SETTINGS}" ] ; then
		printf "%b" "${UBOOT_FIT_USER_SETTINGS}" >> ${UBOOT_ITS}
	fi

	if [ -n "${UBOOT_FIT_CONF_FIRMWARE}" ] ; then
		conf_firmware="firmware = \"${UBOOT_FIT_CONF_FIRMWARE}\";"
	fi

	conf_loadables=$(echo ${conf_loadables} | sed 's/[^ ][^ ]*/"&"/g; s/ /, /g')
	conf_pre_loadables=$(echo ${conf_pre_loadables} | sed 's/[^ ][^ ]*/"&"/g; s/ /, /g')

	if [ -n "${UBOOT_FIT_CONF_USER_LOADABLES}" ] ; then
		conf_loadables="${conf_loadables}${UBOOT_FIT_CONF_USER_LOADABLES}"
	fi

	cat << EOF >> ${UBOOT_ITS}
	};

	configurations {
		default = "${UBOOT_FIT_DEFAULT_CONF}";
EOF

	if [ "${UBOOT_FIT_PRE_DDR}" = "1" ] ; then
		cat << EOF >> ${UBOOT_ITS}
		${UBOOT_FIT_PRE_DDR_CONF} {
			description = "${UBOOT_FIT_PRE_DDR_CONF_DESC}";
			loadables = ${conf_pre_loadables};
		};
EOF
	fi

	cat << EOF >> ${UBOOT_ITS}
		${UBOOT_FIT_CONF} {
			description = "${UBOOT_FIT_CONF_DESC}";
			${conf_firmware}
			loadables = ${conf_loadables};
		};
	};
};
EOF

	#
	# Assemble the U-boot FIT image
	#
	bbnote "mkimage: ${UBOOT_MKIMAGE} -E -f ${UBOOT_ITS} ${UBOOT_FITIMAGE_BINARY}"
	${UBOOT_MKIMAGE} \
		-E \
		-f ${UBOOT_ITS} \
		${UBOOT_FITIMAGE_BINARY}
}
