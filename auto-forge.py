# When you open a new fontforge template, go to File > Execute Script, and run everything between # ---- #

# ------------------------------------------------------------------------------------- #

import fontforge
import os

font = fontforge.font()  # create new .sfd
svg_folder = "/path/to/svg/folder"

for file in os.listdir(svg_folder):
    dec_val = int(file.split('.')[0].split("DEC")[1])  # gets the decimal value within the svg file's name
    
    if dec_val > 0:  # fontforge disallows adding a glyph for the NULL position.
        glyph = font.createChar(dec_val, chr(dec_val))
        glyph.importOutlines(f"{svg_folder}\\{file}")

# ------------------------------------------------------------------------------------- #

# Once this script executes, you should have made another font .sfd file containing all the svgs in their correct
# places. Now, select all of them using CTRL+A, and then go to Metrics and select Auto Width with the defaults.
# This should now give them nice spacings between each other during testing.
# On that note, during my own testing when going to Metrics > New Metrics Window, I found the space to be too short
# by default, so I changed it manually to a width of 400; purely eyeballing it here, I thought this value felt right.

# To convert to TTC, the EM had to be a power of 2. This font's EM was originally 1000, however, by going to 
# Element > Font Info > General, I changed this to 1024 using the dropdown. Fontforge would then auto transform 
# everything appropriately.

