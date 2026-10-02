SUMMARY = "Shikra prebuilt boot binaries (SHIKRA_bootbinaries tech package)"
DESCRIPTION = "Fetches the SHIKRA_bootbinaries tech package and stages its binaries"
LICENSE = "CLOSED"

inherit nopackages deploy

INHIBIT_DEFAULT_DEPS = "1"

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(shikra-evk)"
PACKAGE_ARCH = "${MACHINE_ARCH}"

SHIKRA_BOOTBIN_BASE_URL ?= "https://softwarecenter.qualcomm.com/nexus/generic/product/chip/tech-package/SHIKRA_bootbinaries.1.0/shikra_bootbinaries.1.0-test-device-public"
SHIKRA_BOOTBIN_BUILD    ?= "00092"
SHIKRA_BOOTBIN_ZIP      ?= "SHIKRA_bootbinaries_${SHIKRA_BOOTBIN_BUILD}.zip"

SRC_URI = "${SHIKRA_BOOTBIN_BASE_URL}/${SHIKRA_BOOTBIN_BUILD}/${SHIKRA_BOOTBIN_ZIP};name=bootbins;subdir=shikra-bootbins"
SRC_URI[bootbins.sha256sum] = "1428967a1467aee0355923a719116031db60e7c90e57eadc5942dac7d151e26b"

S = "${UNPACKDIR}/shikra-bootbins/SHIKRA_bootbinaries"
SHIKRA_BOOTBIN_DEPLOY ?= "shikra-bootbins"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

SHIKRA_BOOTBIN_DATADIR = "${datadir}/shikra-bootbins"

do_install() {
    install -d ${D}${SHIKRA_BOOTBIN_DATADIR}
    install -m 0644 ${S}/*.bin ${S}/*.elf ${S}/*.mbn ${D}${SHIKRA_BOOTBIN_DATADIR}/
}

do_deploy() {
    install -d ${DEPLOYDIR}/
    install -m 0644 ${D}${SHIKRA_BOOTBIN_DATADIR}/* ${DEPLOYDIR}/
}

addtask deploy after do_install before do_build do_populate_sysroot
