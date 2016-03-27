# A script that strips unwanted files

# Delete all binary files marked as executables
find . -path ./debian -prune -o -path ./third_party/icu/source -prune -o -path ./third_party/liblouis/src/tables -prune -o -path ./components/dom_distiller/core/data/distillable_page_model.bin -prune -o -path ./components/dom_distiller/core/data/distillable_page_model_new.bin -prune -o -path ./third_party/skia/resources -prune -o -path ./third_party/deqp/src/data -prune -o -type f -not \( -empty \) -not \( -name "*.ttf" -o -name "*.png" -o -name "*.jpg" -o -name "*.webp" -o -name "*.gif" -o -name "*.ico" -o -name "*.mp3" -o -name "*.wav" -o -name "*.icns" -o -name "*.woff" -o -name "*.woff2" -o -name "*Makefile" -o -name "*makefile" -o -name "*.xcf" -o -name "*.cur" -o -name "*.pdf" -o -name "*.ai" -o -name "*.h" -o -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.mk" -o -name "*.bmp" -o -name "*.py" -o -name "*.xml" -o -name "*.html" -o -name "*.js" -o -name "*.json" -o -name "*.txt" -o -name "*.TXT" \) -not \( -exec grep -Iq . {} \; \) -print | xargs -L1 -I{} rm {}

# Remove some unnecessary google code
rm -r ./google_apis
rm -r ./google_update

rm -r ./components/browser_sync
rm ./components/browser_sync.gypi
rm ./components/browser_sync_strings.grdp

rm -r ./components/cloud_devices
rm ./components/cloud_devices.gypi

rm -r ./components/copresence
rm ./components/copresence.gypi

rm -r ./components/drive
rm ./components/drive.gypi

rm -r ./components/gcm_driver
rm ./components/gcm_driver.gypi

rm -r ./components/google
rm ./components/google.gypi

rm -r ./components/search
rm ./components/search.gypi

rm -r ./components/search_engines
rm ./components/search_engines.gypi

rm -r ./components/search_provider_logos
rm ./components/search_provider_logos.gypi

rm -r ./components/signin
rm ./components/signin.gypi

exit 0;
