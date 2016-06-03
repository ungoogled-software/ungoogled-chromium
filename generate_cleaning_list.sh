# A script that prints files to be removed

# Delete all binary files
find . -path ./debian -prune \
    -o -path ./components/dom_distiller/core/data/distillable_page_model.bin -prune \
    -o -path ./components/dom_distiller/core/data/distillable_page_model_new.bin -prune \
    -o -path ./components/dom_distiller/core/data/long_page_model.bin -prune \
    -o -type f -not \( -empty \) -not \( -name "*.ttf" \
        -o -name "*.png" \
        -o -name "*.jpg" \
        -o -name "*.webp" \
        -o -name "*.gif" \
        -o -name "*.ico" \
        -o -name "*.mp3" \
        -o -name "*.wav" \
        -o -name "*.icns" \
        -o -name "*.woff" \
        -o -name "*.woff2" \
        -o -name "*Makefile" \
        -o -name "*makefile" \
        -o -name "*.xcf" \
        -o -name "*.cur" \
        -o -name "*.pdf" \
        -o -name "*.ai" \
        -o -name "*.h" \
        -o -name "*.c" \
        -o -name "*.cpp" \
        -o -name "*.cc" \
        -o -name "*.mk" \
        -o -name "*.bmp" \
        -o -name "*.py" \
        -o -name "*.xml" \
        -o -name "*.html" \
        -o -name "*.js" \
        -o -name "*.json" \
        -o -name "*.txt" \
        -o -name "*.TXT" \) \
    -not \( -exec grep -Iq . {} \; \) -printf '%P\n'

# Delete domain_reliability files
find ./components/domain_reliability/baked_in_configs/ -type f -printf '%P\n'
