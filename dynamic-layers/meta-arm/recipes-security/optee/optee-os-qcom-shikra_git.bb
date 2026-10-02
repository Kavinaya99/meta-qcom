require optee-os-qcom.inc

OPTEEMACHINE = "qcom-shikra"

COMPATIBLE_MACHINE = "^$"
COMPATIBLE_MACHINE:aarch64 = "(qcom)"

OPTEE_DEPLOY = "optee-shikra"

# Use Shikra branch
SRC_URI = "git://github.com/qualcomm-linux/optee_os.git;protocol=https;name=optee;branch=early/hwe/shikra"
SRCREV_optee = "ad89d7eb0edb89beb606ae5017e7a820c6fca617"
