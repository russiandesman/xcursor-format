# xcursor-format

Library to work with XCursor files

# xcursor_theme_leftifier

Take cursor theme you like (look at /usr/share/icons/), make it left hand friendly.

Usage:

```
xcursor_theme_leftifier.py --input=/usr/share/icons/DMZ-Black --output=test
```

Advanced usage (when you know exactly which cursors need to be flipped and not satisfied with automation results):

```
xcursor_theme_leftifier.py --input=/usr/share/icons/DMZ-Black --output=test --files=left_ptr,left_ptr_watch
```

# xcur2png

Drop-in replacement for great and misterious xcur2png (https://github.com/eworm-de/xcur2png)

Usage:

```
xcur2png --show-hot --outdir=test /usr/share/icons/DMZ-Black/cursors/cross
```
