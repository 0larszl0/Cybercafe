# Cybercafe
This is a restoration project for the old linux console font: 'cybercafe.fnt'.
### .fnt
```
cybercafe.fnt is a VGA raw bitmap which represents each character with a bit pattern, i.e.
001100          11 
010010         1  1
011110  -->    1111
010010         1  1
turns out to look like an A

Depending on .fnt file, different heights are given.
This height can be found by dividing the total number of bytes in the file by 256.
Three most common file sizes are: 2048, 3584, 4096, that have glyph dimensions: 8x8, 8x14, 8x16 respectively.
So, if font_height is 16, dimensions 8x16 means 16 lots of 8bytes, so we split the byte(/raw) contents by the height to get elements of size 16.
```
### Font-Tracing Algorithm
```
After many enumerations of different ways to get each coordinate to connect the best way a "scan-down"
approach was ultimately defined as the best.
Before beginning it is **paramount** to visualise each bit in a glyph as a square, take the following:
[[  0   0   0]
 [  1   1   0]
 [  0   0   0]]
The indices of both 1s are (0, 1) and (1, 1).
Now imagine a box around each of them, so (0, 1) would be the top left (tl) of the leftmost 1, so: 
(1, 1) is the top right (tr) for it, (0, 2) is the bottom left (bl), and (1, 2) is the bottom right (br).
While for the middle 1, (1, 1) is the tl, (2, 1) is the tr, (1, 2) is the bl and (2, 2) is the br

The ultimate goal is to get an algorithm to accurately go across the coordinate space and make valid connections.

The best solution I've been able to devise applies a cross (+) like pattern across each bit of the glyph.
Let's use this example:
[[  0   0   0]
 [  1   1   0]
 [  0   0   1]]
 
Say we've iterated to position (1, 1), the centre.
We're only interested in the top, bottom, left, and right positions surrounding it, anything else is disregarded
[[  -   0   -]
 [  1   X   0]
 [  -   0   -]]

Let's start at the top. Imagine the top values of position X aka (1, 1) as (1, 1)--tl and (2, 1)--tr.
As the top value is 0, that means there is no connection to another piece, and as a result, we can record
the information that (1, 1) connects with (2, 1) and (2, 1) connects with (1, 1).
This is the same with the bottom, the value is 0, so the bl and br can be recorded to connect with one another.
So, (1, 2) and (2, 2) connect with each other.
Now, let's look at the right, this is also 0. So, a similar principle happens, imagine the borders of the square of X,
the corners that would connect here would be the tr and br-- (2, 1) and (2, 2).
However, the left handside is a bit different, because there's 1 there visualise two squares touching:
 ___ ___
|   | X |
 ‾‾‾ ‾‾‾
The left edge of X is touching the right of the other square, so we don't want to record this connection if we want 
the outline of this shape.
 
This process iterates across all values were the X lands on 1, if it lands on 0 like in:
[[  -   -   0]
 [  -   1   X]
 [  -   -   1]]
We skip it.

Additionally, if we're at a situation where one part of the cross gets consumed by a wall:
[[  0   -   -]  
 [  X   1   -]
 [  0   -   -]]
or 
[[  -   -   -]
 [  -   -   0]
 [  -   0   X]]

Those parts edges of the square should automatically be recorded, for the first case above,
we would want to still record the left edge of the square of X, so coords (0, 1) and (0, 2) would record a connection with
one another. Whereas the other case would record both the right and bottom side of the square, so (3, 2) and (3, 3) would
connect with each other.

Now once, all these coordinates are together, it's a matter of creating routes out of them.
And after that optimising the routes.
Say a route would be [(0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (1, 1), (0, 1)]
The optimal form would be [(0, 1), (0, 2), (2, 2), (2, 1), (0, 1)]
so essentially making:
+___+___+               +_______+
|       |   --into-->   |       |
+‾‾‾+‾‾‾+               +‾‾‾‾‾‾‾+

After this it's a matter of identifying if the other route:
[(2, 2), (2, 3), (3, 3), (3, 2), (2, 2)]
is inside the above one.

(Note that the routes in the example, are not outputted from the algorithm, but as my own example.)
```

#### Full code requirements
numpy >= 2.3.3 \
pillow >= 11.3.0 \
shapely >= 2.1.2 \
svgwrite >= 1.4.3 

### Distribution Note
```commandline
From alter@cybercafe.com.ua Thu Jun 29 03:35:34 2000

I have created the font.
I think that it is font of the 21st century.
First time it looks unusual.
But later any other font looks wrong.

I made symbols from 0x20..0x7f|0xf0..0xff  only.
But I could made complete fonts.

{
Distribution policy.
Such my font allowed to distribution in any form, and in any way.
Such font have to be distributed only with this distribution policy
and following information about the author.
(It could be added somewhere in documentation or like a separate file.)
Note: The entries, which was made with this font,
is not an objects of this distribution policy.

Information about author:
handle: "the Alternative" or "Alt"
real name: M[y|ee|i][|k]ha[i|j]lo M[ee|y|i]t[|h]ro[f|v]ano[w|v].
borned in Kyiv/Ukraine in 21.XI.1976.
email: alter@cybercafe.com.ua
}

---
Since "alt" is a symbol encoding, I called this font cybercafe -- aeb

```
