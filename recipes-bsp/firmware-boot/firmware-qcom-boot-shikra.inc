DESCRIPTION = "QCOM NHLOS Firmware for Qualcomm Shikra-EVK platform"
LICENSE = "CLOSED"

BOOTBINARIES = "SHIKRA_bootbinaries"

FILESEXTRAPATHS:prepend := "${THISDIR}/:"
SHIKRA_FW_ZIP ?= "SHIKRA_bootbinaries.zip"
SRC_URI = "file://${SHIKRA_FW_ZIP}"

QCOM_BOOT_IMG_SUBDIR = "shikra"

include firmware-qcom-boot-common.inc

do_deploy:append() {
    for bootdir in ${QCOM_BOOT_BINARY_DIRS}; do
        [ -d "${bootdir}/fit-elf" ] || continue

        install -d ${DEPLOYDIR}/${QCOM_BOOT_IMG_SUBDIR}/fit-elf
        find "${bootdir}/fit-elf" -maxdepth 1 -type f -exec install -m 0644 {} ${DEPLOYDIR}/${QCOM_BOOT_IMG_SUBDIR}/fit-elf \;
    done
}
