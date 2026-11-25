FILESEXTRAPATHS:prepend := "${THISDIR}/linux-mainline:"

# Removing hamoa camera dtbo
KERNEL_DEVICETREE:remove = "qcom/hamoa-iot-evk-camera-imx577.dtbo"

# Removing bt-uart dtbo
KERNEL_DEVICETREE:remove = "qcom/qcs6490-rb3gen2-industrial-mezzanine-bt-uart.dtbo"

KERNEL_DEVICETREE:remove = "qcom/shikra-cqm-evk-imx577-camera.dtbo"
KERNEL_DEVICETREE:remove = "qcom/shikra-cqm-cqs-evk-hdmi.dtbo"
KERNEL_DEVICETREE:remove = "qcom/shikra-iqs-evk-dlc-panel.dtbo"
KERNEL_DEVICETREE:remove = "qcom/shikra-iqs-evk-lvds-auo,g133han01.dtbo"

COMPATIBLE_MACHINE:qcom = "qcom"

SRC_URI:append:qcom = " file://qcom-bsp.cfg"

#DEPENDS:remove = "python3-dtschema-wrapper-native"

