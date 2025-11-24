SUMMARY = "Build qcom-metadata.dtb from vendored qcom-dtb-metadata"

LICENSE = "BSD-3-Clause-Clear"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=2998c54c288b081076c9af987bdf4838"

inherit deploy

SRC_URI = "git://github.com/qualcomm-linux/qcom-dtb-metadata.git;branch=main;protocol=https"

SRCREV = "793450654d87b0702b0e79f47e6ea66d4a89edbf"

DEPENDS = "dtc-native"

do_compile() {
    oe_runmake
}

do_deploy() {
    install -d ${DEPLOY_DIR_IMAGE}
    install -m 0644 ${S}/qcom-metadata.dtb ${DEPLOY_DIR_IMAGE}/qcom-metadata.dtb
}
addtask deploy after do_compile before do_build
