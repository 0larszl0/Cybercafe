from typing import List, Tuple, Set
from PIL import Image
import numpy as np
import svgwrite
from shapely.geometry import Polygon
import os


def create_bitmap(glyph: bytes) -> List[List[int]]:
    """
    Takes the 16B in the glyph and converts each byte into a list containing each bit in that byte.
    This ultimately creates lists containing each bit for each byte.
    i.e. converts the 16B into a list of lists of bits--
    [
        [0, 0, 0, 0, 0, 0, 0, 0],
                   .
                 (+12)
                   .
        [0, 0, 0, 0, 0, 0, 0, 0]
    ]
    :return: List[List[int]]
    """
    return [list(map(int, list(format(byte, "#010b")[2:]))) for byte in glyph]


class Glyph:
    def __init__(self, raw_glyph: bytes, mult = 255):  # mult is just used to make "on" values clearer when debugging.
        self.__glyph_data = np.array(create_bitmap(raw_glyph), dtype=np.uint8) * mult
        print(self.__glyph_data)

        self.__realtime_glyph = [[f"{'':3}" for __ in range(self.__glyph_data.shape[1])] for _ in range(self.__glyph_data.shape[0])]

        self.__glyph_box_coords = []

    def scan_down(self) -> List[List[Tuple[int, int]]]:
        """
        Scanning down the glyph data in a cross fashion, take the following for instance:
        [[  0   0   0]
         [  1   1   0]
         [  0   0   1]]
        And say we're investigating (1, 1), the algorithm will be utilising the following data:
        [[  -   0   -]
         [  1   X   0]
         [  -   0   -]]
        As the top of the currently investigated position is 0, we record the top part of an imaginary rectangle around
        X, so, the algorithm would record (1, 1)  ->  (2, 1) and vice versa.
        However, as the left has 1, it won't record (1, 1)  ->  (1, 2) nor vice versa.
        But for the right, it'd record (2, 1)  ->  (2, 2) and vice versa... etc.

        After all these connections are recorded, the algorithm will trace around each until there is no more
        coordinates to trace around.

        Once all the paths are found, the algorithm will optimise the findings to remove "runs" like:
            [(0, 1), (0, 2), (0, 3), (0, 4)]
        to be:
            [(0, 1), (0,4)]

        :return: List[List[Tuple[int, int]]]
        """

        flattened_data = self.__glyph_data.flatten()
        y_shape, x_shape = self.__glyph_data.shape

        coordinates = {}

        for i, val in enumerate(flattened_data):
            y = i // x_shape
            x = i % x_shape

            if not self.__glyph_data[y][x]:  # the current value being scanned is empty
                continue  # skip past

            # - Ensure a bucket for any coordinate that may need it
            coordinates[(x, y)], coordinates[(x + 1, y)], coordinates[(x, y + 1)], coordinates[(x + 1, y + 1)] = (
                coordinates.get((x, y), []),
                coordinates.get((x + 1, y), []),
                coordinates.get((x, y + 1), []),
                coordinates.get((x + 1, y + 1), [])
            )

            # -- Record...
            # - Top when...
            # either you're at the first row OR when the value above the current is empty
            if y == 0 or not self.__glyph_data[y - 1][x]:
                coordinates[(x, y)].append((x + 1, y))  # top left records connection with top right
                coordinates[(x + 1, y)].append((x, y))  # and vice versa

                self.__realtime_glyph[y][x] = self.__realtime_glyph[y][x].replace(' ', '‾')  # fill with the roof character

            # - Bottom when...
            # either you're at the last row OR when the value under the current is empty
            if y == y_shape - 1 or not self.__glyph_data[y + 1][x]:
                coordinates[(x, y + 1)].append((x + 1, y + 1))  # bottom left records connection with bottom right
                coordinates[(x + 1, y + 1)].append((x, y + 1))  # and vice versa

                self.__realtime_glyph[y][x] = self.__realtime_glyph[y][x].replace(' ', '_')  # if roof character not there, fill with _
                if self.__realtime_glyph[y][x][0] == '‾':  # if the top has already been recorded
                    self.__realtime_glyph[y][x] = '\033[4m' + self.__realtime_glyph[y][x] + '\033[0m'  # underline that segment to show the bottom of the square

            # - Left when
            # either you're at the first column OR when the value on the left is empty
            if x == 0 or not self.__glyph_data[y][x - 1]:
                coordinates[(x, y)].append((x, y + 1))  # top left records connection with bottom left
                coordinates[(x, y + 1)].append((x, y))  # and vice versa

                # - Remove the first character from the glyph visualisation string
                if self.__realtime_glyph[y][x][0] == '\033':  # when an ansii code has been added
                    self.__realtime_glyph[y][x] = ' ' + self.__realtime_glyph[y][x][:4] + self.__realtime_glyph[y][x][5:]

                # [1:] Removes that first character in the event of no ansii code, ansii code condition above handles this, hence the ' ' at the start. The ' ' is just something the below code will get rid of
                self.__realtime_glyph[y][x] = '|' + self.__realtime_glyph[y][x][1:]

            # - Right when
            # either you're at the last column OR when the value on the right is empty
            if x == x_shape - 1 or not self.__glyph_data[y][x + 1]:
                coordinates[(x + 1, y)].append((x + 1, y + 1))  # top right records connection with bottom right
                coordinates[(x + 1, y + 1)].append((x + 1, y))  # and vice versa

                # - Remove the last character from the glyph visualisation string
                if '\033' in self.__realtime_glyph[y][x][:2]:
                    self.__realtime_glyph[y][x] = self.__realtime_glyph[y][x][:-5] + self.__realtime_glyph[y][x][-4:] + ' '

                # [:-1] Removes the last character in the visual glyph, as the above condition for ansii codes does that for its condition, we deliberately remove the placed redundancy-- (the space)
                self.__realtime_glyph[y][x] = self.__realtime_glyph[y][x][:-1] + '|'

            print('\n'.join(map(lambda cols: ''.join(cols), self.__realtime_glyph)), end="\r")

        print()
        print(coordinates)

        if not coordinates:
            return []

        # -- Create a path from the recorded connections
        # - Start at the highest and leftmost point per trace, while first filtering out those that don't have any unvisited coords left; there value is []

        start = min(filter(lambda kee: coordinates[kee] != [], coordinates.keys()), key=lambda coord: coord[1])
        routes = [[start, coordinates[start].pop(0)]]
        coordinates[routes[-1][-1]].remove(routes[-1][-2])  # remove the coordinate we're moving from, from the set of connections available-- ensures the algorithm doesn't go back on itself.

        while any(coordinates.values()):  # stops when all the coordinates have been passed through, in other words, when all the values are empty sets
            if routes[-1][-1] == routes[-1][0]:  # Checks if we've reached the start again
                # - Find new start value
                start = min(filter(lambda kee: coordinates[kee] != [], coordinates.keys()), key=lambda coord: coord[1])
                print(start)

                # for key, value in coordinates.items():
                #     if value:  # if value is not an empty set
                #         start = key
                #         break

                # - Create a new path
                routes.append([start, coordinates[start].pop(0)])
                coordinates[routes[-1][-1]].remove(routes[-1][-2])

            routes[-1].append(coordinates[routes[-1][-1]].pop(0))
            coordinates[routes[-1][-1]].remove(routes[-1][-2])

        # -- Optimise the routes found
        # - Remove all runs: [(2, 2), (2, 3), (1, 3)] check if the difference of element 2 and 0 has any zeros, if not keep element 1
        print(f"Unoptimised routes:\n{'\n'.join([f'{i+1}. {str(route)}' for i, route in enumerate(routes)])}\n")
        print("Optimised routes:")

        for x in range(len(routes)):
            routes[x] = [routes[x][0]] + [routes[x][i] for i in range(1, len(routes[x]) - 1) if all((
                routes[x][i - 1][0] - routes[x][i + 1][0],
                routes[x][i - 1][1] - routes[x][i + 1][1]
            ))] + [routes[x][-1]]

            print(f"{x+1}. {str(routes[x])}")

        return routes

    @staticmethod
    def find_holes(routes: List[List[Tuple[int, int]]]) -> Set:
        """
        Determine which route from the ones found from scan_down() is inside another, and if it is, mark as a hole.
        :param List[List[Tuple[int, int]]] routes: All the traces around the glyph.
        :return: Set, the indices in routes that are holes
        """
        if not routes:  # when there are no traces, i.e. when the glyph is blank
            return set()

        # - Convert each route into its own polygon
        polygons = [Polygon(route) for route in routes]
        polygons_len = len(polygons)

        # - Find any trace that is inside another (becomes a hole)
        # Order shouldn't really matter, as any hole should be cut out.
        hole_inds = set()
        for i in range(polygons_len):
            if i in hole_inds:  # if the index has already been seen/contained by another path
                continue  # skip over it- in this case it's irrelevant to know if a hole is in a hole; this algorithm doesn't apply the oddeven rule.

            for j in range(polygons_len):
                if i != j and polygons[i].contains(polygons[j]):
                    hole_inds.add(j)

        return hole_inds


class FntConverter:
    def __init__(self, fnt_path: str, charset_size: int):
        # Depending on .fnt file, different heights are given.
        # This height can be found by dividing the total number of bytes in the file by 256.
        # Three most common file sizes are: 2048, 3584, 4096, that have glyph dimensions: 8x8, 8x14, 8x16 respectively.
        self.__font_height = os.path.getsize(fnt_path) // charset_size
        self.__charset_size = charset_size

        # Read each byte from font file
        with open(fnt_path, "rb") as file:
            raw_contents = file.read()

        # splits the raw bytes up into groups of size equivalent to self.__font_height
        # say, font_height is 16, so 8x16 means 16 lots of 8bytes, so we split the byte(/raw) contents by the height to get elements of size 16.
        # For instance say, '\x00\x00\x00\x00\x00\x008lll8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x008lll8\x00\x00\x00\x00\x00'
        # is the first 32. With height 16 you'd split like:
        # ['\x00\x00\x00\x00\x00\x008lll8\x00\x00\x00\x00\x00', '\x00\x00\x00\x00\x00\x008lll8\x00\x00\x00\x00\x00']
        self.__glyphs = [raw_contents[i: i + self.__font_height] for i in range(0, len(raw_contents), self.__font_height)]

    def visualise_raw_glyph(self, ascii_dec: int, sign: str = '&') -> str:
        """
        Visualise a character in raw format.
        :param int ascii_dec: The decimal value of the character, on the ascii table, to show.
        :param str sign: The character to show inplace of '1'.
        :return: str
        """
        return '\n'.join([format(byte, "#010b")[2:] for byte in self.__glyphs[ascii_dec]]).replace('0', ' ').replace('1', sign)

    def create_bitmaps(self, dir_path: str = "Bitmaps/") -> None:
        """
        Creates bitmaps from each glyph.
        :param str dir_path: The directory to store each bitmap.
        :return: None
        """
        for i, glyph in enumerate(self.__glyphs):
            bitmap_data = np.array(create_bitmap(glyph), dtype=np.uint8) * 255  # * 255 here makes everything into the 0-255 colour range

            bitmap_img = Image.fromarray(bitmap_data)
            bitmap_img.save(f"{dir_path}/Char{i}.pbm")

    def draw_svg(self, routes: List[List[Tuple[int, int]]], holes: Set, char_dec: int) -> None:
        """
        Using the routes that construct the glyph and the knowledge of which are holes, generate a svg out of it.
        :param List[List[Tuple[int, int]]] routes: A list of lists of coordinates that when connected together form an outline of a shape.
        :param Set holes: A set of indices corresponding to the routes in the routes param that are holes. (disregards the parent of a hole)
        :param int char_dec: The ASCII decimal value of the character we are creating.
        :return: None, but this creates an image
        """
        # viewBox specifies the original coordinate space the glyph would be mapped to; the size tells the svgwriter how much each dimension should be scaled up by
        drawing = svgwrite.Drawing(f"SVGs/Char-DEC{char_dec}.svg", viewBox=f"0 0 8 {self.__font_height}", size=(1000, int((self.__font_height / 8) * 1000)))

        # Fontforge doesn't handle masks, hence nonzero fill rule must be applied, note that for any shape inside a
        # shape must be drawn in the opposite direction for it to be known as a hole.

        full_svg_path = ""

        for i, route in enumerate(routes):
            if i in holes:
                route = route[::-1]

            full_svg_path += f"M {route[0][0]} {route[0][1]} L " + ' '.join([f"{x} {y}" for x, y in route[1:-1]]) + " Z "

        if full_svg_path:
            path = drawing.path(d=full_svg_path[:-1], fill="black", fill_rule="nonzero")
            drawing.add(path)

        drawing.save()


    def create_svgs(self):
        for dec in range(self.__charset_size):
            glyph = Glyph(self.__glyphs[dec])

            glyph_routes = glyph.scan_down()
            glyph_holes = glyph.find_holes(glyph_routes)
            print(f"\nHoles: {glyph_holes}")

            self.draw_svg(glyph_routes, glyph_holes, dec)

        # - Below is to test for a single character

        # glyph = Glyph(self.__glyphs[79])
        #
        # glyph_routes = glyph.scan_down()
        # glyph_holes = glyph.find_holes(glyph_routes)
        # print(glyph_holes)
        #
        # self.draw_svg(glyph_routes, glyph_holes, 79)


if __name__ == "__main__":
    converter = FntConverter("cybercafe.fnt", 256)
    # print(converter.visualise_raw_glyph(79))

    converter.create_svgs()
