require optee-os-qcom.inc

OPTEEMACHINE = "qcom-shikra"

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(qcom)"

OPTEE_DEPLOY = "optee-shikra"

# Use Shikra branch
SRC_URI = "git://github.com/qualcomm-linux/optee_os.git;protocol=https;name=optee;branch=early/hwe/shikra"
SRCREV_optee = "08b68eef2b1ee3a6be9642efca8583fd0be15b16"

FILESEXTRAPATHS:prepend := "${THISDIR}:"
SRC_URI += " \
    file://0001-core-pta-qcom-pas-Allow-fw_base-init-for-non-relocat.patch \
    file://0002-plat-qcom-shikra-enable-CDSP-LMCU-PAS-support.patch \
    file://0003-plat-qcom-shikra-remove-LMCU-PAS-support.patch \
    file://0004-pta-qcom-pas-validate-controller-window-base.patch \
    file://0005-pta-qcom-pas-Remove-processor-reset-from-bring-up.patch \
    file://0006-clk-qcom-add-reusable-Spark-PLL-helper-and-LMCU-cloc.patch \
    file://0007-clk-qcom-shikra-add-Turing-Q6-and-LMCU-PIL-clock-bri.patch \
    file://0008-pta-qcom-pas-shikra-add-LMCU-firmware-bring-up.patch \
    file://0009-pta-qcom-pas-shikra-add-aperture-mapping-for-CDSP-an.patch \
    file://0010-core-pta-qcom-Fix-missing-type-enum.patch \
"
