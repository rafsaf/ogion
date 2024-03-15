#########################################################################
# 7ZIP DOWNLOAD FOR ARM64 AND AMD64
#
# https://www.7-zip.org/download.html
#########################################################################
#!/bin/sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

AMD64_DIR="$SCRIPT_DIR/../ogion/bin/7zip/amd64"
AMD64_7ZZ="$AMD64_DIR/7zz"

ARM64_DIR="$SCRIPT_DIR/../ogion/bin/7zip/arm64"
ARM64_7ZZ="$ARM64_DIR/7zz"

if [ -f "$AMD64_7ZZ" ]
then
  echo "$AMD64_7ZZ exists"
else
  mkdir -p $AMD64_DIR
  cd $AMD64_DIR
  wget --quiet "https://www.7-zip.org/a/7z2301-linux-x64.tar.xz"
  tar -xf "7z2301-linux-x64.tar.xz"
  rm -f "7z2301-linux-x64.tar.xz"
fi

if [ -f "$ARM64_7ZZ" ]
then
  echo "$ARM64_7ZZ exists"
else
  mkdir -p $ARM64_DIR
  cd $ARM64_DIR
  wget --quiet "https://www.7-zip.org/a/7z2301-linux-arm64.tar.xz"
  tar -xf "7z2301-linux-arm64.tar.xz"
  rm -f "7z2301-linux-arm64.tar.xz"
fi