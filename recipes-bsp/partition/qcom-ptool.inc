HOMEPAGE = "https://github.com/qualcomm-linux/qcom-ptool"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b0a8acd90d872086b279ead88af03369"

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI = "git://github.com/qualcomm-linux/qcom-ptool.git;branch=main;protocol=https"
SRCREV = "d7c0e814a6f1f40469f65c61eae05a553c384566"

SRC_URI += "file://0001-shikra-evk-Add-modified-partition-conf.patch"
