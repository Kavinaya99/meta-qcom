require recipes-security/optee/optee-os.inc

PV = "4.11.0-qcom-20261030+git"

SRC_TAG = "tag=qcom-next-4.11-20261030"
SRC_URI = "git://github.com/qualcomm-linux/optee_os.git;protocol=https;name=optee;nobranch=1;${SRC_TAG}"
SRCREV_optee = "7087bd740178eb548584e70df62d0c3e613f8daa"


# Copy of do_deploy from meta-arm until we get it fixed to support configurable deploy dir
OPTEE_DEPLOY ?= "optee"
do_deploy() {
    install -d ${DEPLOYDIR}/${MLPREFIX}${OPTEE_DEPLOY}
    install -m 644 ${D}${nonarch_base_libdir}/firmware/* ${DEPLOYDIR}/${MLPREFIX}${OPTEE_DEPLOY}

    install -d ${DEPLOYDIR}/${MLPREFIX}${OPTEE_DEPLOY}/ta
    install -m 644 ${B}/ta/*/*.elf ${DEPLOYDIR}/${MLPREFIX}${OPTEE_DEPLOY}/ta
}
