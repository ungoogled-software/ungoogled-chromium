# A script that strips unwanted files

# Delete unneeded directories
rm -rf ./native_client
rm -rf ./native_client_sdk
rm -rf ./out
rm -rf ./buildtools
rm -rf ./build/linux/debian_wheezy_amd64-sysroot
rm -rf ./third_party/webgl/src/conformance-suites
rm -rf ./build/android
rm -rf ./sql/test
rm -rf ./components/test
rm -rf ./chrome/test
rm -rf ./chrome/app/test_data
rm -rf ./extensions/test
rm -rf ./ios
rm -rf ./android_webview
rm -rf ./chromeos
rm -rf ./chrome/browser/resources/chromeos
rm -rf ./third_party/webgl/src/sdk/tests
rm -rf ./third_party/webgl/src/sdk/demos

# Delete all binary files marked as executables
find . -path ./debian -prune -o -path ./third_party/icu/source -prune -o -path ./third_party/liblouis/src/tables -prune -o -type f -not \( -empty \) -not \( -name "*.ttf" -o -name "*.png" -o -name "*.jpg" -o -name "*.webp" -o -name "*.gif" -o -name "*.ico" -o -name "*.mp3" -o -name "*.wav" -o -name "*.icns" -o -name "*.woff" -o -name "*.woff2" -o -name "Makefile" -o -name "*.xcf" -o -name "*.cur" -o -name "*.pdf" -o -name "*.ai" -o -name "*.h" -o -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.mk" -o -name "*.bmp" -o -name "*.py" -o -name "*.xml" \) -not \( -exec grep -Iq . {} \; \) -print | xargs -L1 -I{} rm {}
