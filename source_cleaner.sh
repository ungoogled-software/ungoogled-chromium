# A script that strips unwanted files

# Delete all binary files marked as executables
find . -path ./debian -prune -o -path ./third_party/icu/source -prune -o -path ./third_party/liblouis/src/tables -prune -o -path ./components/dom_distiller/core/data/distillable_page_model.bin -prune -o -type f -not \( -empty \) -not \( -name "*.ttf" -o -name "*.png" -o -name "*.jpg" -o -name "*.webp" -o -name "*.gif" -o -name "*.ico" -o -name "*.mp3" -o -name "*.wav" -o -name "*.icns" -o -name "*.woff" -o -name "*.woff2" -o -name "Makefile" -o -name "*.xcf" -o -name "*.cur" -o -name "*.pdf" -o -name "*.ai" -o -name "*.h" -o -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.mk" -o -name "*.bmp" -o -name "*.py" -o -name "*.xml" \) -not \( -exec grep -Iq . {} \; \) -print | xargs -L1 -I{} rm {}

# Add blank files required for building
touch chrome/test/data/webui/i18n_process_css_test.html
