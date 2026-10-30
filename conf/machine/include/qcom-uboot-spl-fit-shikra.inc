# Copyright (c) 2026 Qualcomm Innovation Center, Inc. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Qualcomm Shikra U-Boot SPL FIT configuration.
#
# The FIT contains a post-DDR configuration with ARM Trusted Firmware,
# U-Boot and OP-TEE, and optionally a pre-DDR configuration with PMIC, DCB,
# ECC, SHRM and QcLib. board_fit_config_name_match() in the Qualcomm SPL
# selects between them using the configuration description.
#
# Load addresses follow the existing Shikra gen_its.py/template.its layout.

# Marker used by the U-Boot and trusted-firmware-a-qcom recipes.
QCOM_UBOOT_SPL_FIT = "1"

UBOOT_FITIMAGE_ENABLE = "1"

# The XBL takes the SPL flow only with this XBLConfig variant.
QCOM_XBL_CONFIG = "xbl_config.elf"

# The U-Boot recipe rebuilds, annotates and signs this as the TZ/SBL image.
SPL_BINARY = "spl/u-boot-spl.bin"

UBOOT_FIT_DESC = "FIT Image for Vendor Boot Loader"
UBOOT_FIT_ADDRESS_CELLS = "1"

# -------------------------------------------------------------------------
# Post-DDR configuration
# -------------------------------------------------------------------------
#
# BL31 is the firmware the SPL boots; U-Boot and OP-TEE are loaded as
# additional payloads. bl31.bin and tee-raw.bin are staged into each
# per-config build directory by uboot_compile_config:append().

UBOOT_FIT_ARM_TRUSTED_FIRMWARE = "1"
UBOOT_FIT_ARM_TRUSTED_FIRMWARE_LOADADDRESS = "0xA1300000"
UBOOT_FIT_ARM_TRUSTED_FIRMWARE_ENTRYPOINT = "0xA1300000"

UBOOT_FIT_TEE = "1"
UBOOT_FIT_TEE_LOADADDRESS = "0xA1400000"
UBOOT_FIT_TEE_ENTRYPOINT = "0xA1400000"

# u-boot.bin carries the appended U-Boot DTB, so no separate fdt node is
# required.
UBOOT_FIT_UBOOT_IMAGE = "u-boot.bin"
UBOOT_FIT_UBOOT_LOADADDRESS = "0x9F400000"
UBOOT_FIT_UBOOT_ENTRYPOINT = "0x9F400000"

UBOOT_FIT_CONF = "post-ddr-config"
UBOOT_FIT_CONF_DESC = "post-ddr"
UBOOT_FIT_DEFAULT_CONF = "post-ddr-config"

# -------------------------------------------------------------------------
# Pre-DDR configuration
# -------------------------------------------------------------------------
#
# Load addresses are the pre-DDR SRAM memory map per gen_its.py
# RAW_BIN_DEFAULT_ADDR. SHRM and QcLib are ELFs, so their load addresses
# come from the PT_LOAD segments. All of these payloads are deploy-only
# prebuilts staged by uboot_compile_config:append().

QCOM_SHIKRA_FIT_PRE_DDR ?= "1"
UBOOT_FIT_PRE_DDR = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_PRE_DDR_CONF = "pre-ddr-config"
UBOOT_FIT_PRE_DDR_CONF_DESC = "pre-ddr"

UBOOT_FIT_PMIC_COCOS = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_PMIC_COCOS_LOADADDRESS = "0xC294800"

UBOOT_FIT_PMIC_WAILUA = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_PMIC_WAILUA_LOADADDRESS = "0xC2A0400"

UBOOT_FIT_DCB_LP4 = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_DCB_LP4_LOADADDRESS = "0xC2A6400"

UBOOT_FIT_DCB_LP5 = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_DCB_LP5_LOADADDRESS = "0xC2AAC00"

UBOOT_FIT_ECC = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_ECC_LOADADDRESS = "0xC2AF400"

UBOOT_FIT_SHRM = "${QCOM_SHIKRA_FIT_PRE_DDR}"
UBOOT_FIT_QCLIB = "${QCOM_SHIKRA_FIT_PRE_DDR}"
