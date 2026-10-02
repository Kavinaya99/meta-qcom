SUMMARY = "Shikra prebuilt boot binaries (SHIKRA_bootbinaries tech package)"
DESCRIPTION = "Fetches the SHIKRA_bootbinaries tech package and stages its binaries"
LICENSE = "CLOSED"

inherit nopackages

INHIBIT_DEFAULT_DEPS = "1"

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(shikra-evk)"
PACKAGE_ARCH = "${MACHINE_ARCH}"

SHIKRA_BOOTBIN_BASE_URL ?= "https://softwarecenter.qualcomm.com/nexus/generic/product/chip/tech-package/SHIKRA_bootbinaries.1.0/shikra_bootbinaries.1.0-test-device-public"
SHIKRA_BOOTBIN_BUILD    ?= "00089"
SHIKRA_BOOTBIN_ZIP      ?= "SHIKRA_bootbinaries_${SHIKRA_BOOTBIN_BUILD}.zip"

SRC_URI = "${SHIKRA_BOOTBIN_BASE_URL}/${SHIKRA_BOOTBIN_BUILD}/${SHIKRA_BOOTBIN_ZIP};name=bootbins;subdir=shikra-bootbins"
SRC_URI[bootbins.sha256sum] = "76aed9ac15830b909a39064c88457aebacaa604366bd9ad4d8fc2958b0deb3a5"

S = "${UNPACKDIR}/shikra-bootbins/SHIKRA_bootbinaries"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

SHIKRA_BOOTBIN_DATADIR = "${datadir}/shikra-bootbins"

do_install() {
    install -d ${D}${SHIKRA_BOOTBIN_DATADIR}
    install -m 0644 ${S}/*.bin ${S}/*.elf ${S}/*.mbn ${D}${SHIKRA_BOOTBIN_DATADIR}/
}

# ${datadir} is in the default SYSROOT_DIRS, so the bins land in
# ${STAGING_DATADIR}/shikra-bootbins for DEPENDS consumers.
