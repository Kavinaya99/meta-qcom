require optee-os-qcom.inc

OPTEEMACHINE = "qcom-shikra"

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(qcom)"

OPTEE_DEPLOY = "optee-shikra"

# Use Shikra branch
SRC_URI = "git://github.com/qualcomm-linux/optee_os.git;protocol=https;name=optee;branch=early/hwe/shikra"
SRCREV_optee = "9331448bf79d42bf7b5b4b537970fb87dd778b13"
