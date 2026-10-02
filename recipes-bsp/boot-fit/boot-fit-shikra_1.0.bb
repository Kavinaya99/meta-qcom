SUMMARY = "Shikra boot FIT image"
DESCRIPTION = "Packs bins into a single FIT image (boot_fit.img) using gen_its.py/template.its."
LICENSE = "CLOSED"

inherit deploy nopackages

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(shikra-evk)"

FILESEXTRAPATHS:prepend := "${THISDIR}:"
SRC_URI = "file://fitbins"

S = "${UNPACKDIR}/fitbins"

FIT_BIN_DIR ?= "${STAGING_DATADIR}/shikra-bootbins"

PACKAGE_ARCH = "${MACHINE_ARCH}"

OPTEE_BIN    ?= "${DEPLOY_DIR_IMAGE}/optee-shikra/tee-raw.bin"
TFA_BL31_BIN ?= "${DEPLOY_DIR_IMAGE}/trusted-firmware-a-qcom-shikra/bl31.bin"
UBOOT_BIN    ?= "${DEPLOY_DIR_IMAGE}/u-boot.bin"

DEPENDS = "python3-native dtc-native u-boot-tools-native shikra-bootbins \
           optee-os-qcom-shikra trusted-firmware-a-qcom-shikra u-boot-qcom"

do_compile[depends] += "optee-os-qcom-shikra:do_deploy \
                        trusted-firmware-a-qcom-shikra:do_deploy \
                        u-boot-qcom:do_deploy"

FIT_TEMPLATE    ?= "template.its"
FIT_PMIC_COCOS  ?= "Pmic_Cocos.bin"
FIT_PMIC_WAILUA ?= "Pmic_Wailua.bin"
FIT_DCB_LP4     ?= "900B_7_0100_1_dcb.bin"
FIT_DCB_LP5     ?= "900B_7_0100_0_dcb.bin"
FIT_ECC         ?= "Shikra_LCP.bin"
FIT_SHRM        ?= "shrm.elf"
FIT_QCLIB       ?= "QcLib.elf"
FIT_RPM         ?= "rpm.mbn"

BOOT_FIT_IMAGE  ?= "boot_fit.img"

do_configure[noexec] = "1"

do_compile() {
    cd ${S}

    for f in ${FIT_PMIC_COCOS} ${FIT_PMIC_WAILUA} ${FIT_DCB_LP4} ${FIT_DCB_LP5} \
             ${FIT_ECC} ${FIT_SHRM} ${FIT_QCLIB} ${FIT_RPM}; do
        if [ ! -f "${FIT_BIN_DIR}/$f" ]; then
            bbfatal "Prebuilt binary '$f' not found in ${FIT_BIN_DIR} (check SHIKRA_BOOTBIN_BUILD)"
        fi
        install -m 0644 "${FIT_BIN_DIR}/$f" ${S}/
    done

    for f in "${OPTEE_BIN}" "${TFA_BL31_BIN}" "${UBOOT_BIN}"; do
        if [ ! -f "$f" ]; then
            bbfatal "Required input binary not found: $f"
        fi
        install -m 0644 "$f" ${S}/
    done

    rm -rf ${S}/out
    install -d ${S}/out

    python3 gen_its.py \
        --template         ${FIT_TEMPLATE} \
        --pmic_cocos_path  ${FIT_PMIC_COCOS} \
        --pmic_wailua_path ${FIT_PMIC_WAILUA} \
        --dcb_lp4_path     ${FIT_DCB_LP4} \
        --dcb_lp5_path     ${FIT_DCB_LP5} \
        --ecc_path         ${FIT_ECC} \
        --shrm_path        ${FIT_SHRM} \
        --qclib_path       ${FIT_QCLIB} \
        --tfa_bl31_path    bl31.bin \
        --optee_path       tee-raw.bin \
        --uboot_path       u-boot.bin \
        --rpm_path         ${FIT_RPM} \
        --output           ./out/${BOOT_FIT_IMAGE}

    if [ ! -f ${S}/out/${BOOT_FIT_IMAGE} ]; then
        bbfatal "gen_its.py did not produce ${BOOT_FIT_IMAGE}"
    fi
}

do_install[noexec] = "1"

do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${S}/out/${BOOT_FIT_IMAGE} ${DEPLOYDIR}/${BOOT_FIT_IMAGE}
}

addtask deploy after do_compile before do_build

