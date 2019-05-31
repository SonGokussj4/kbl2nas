#!/expSW/SOFTWARE/python371/bin/python3
import sys
from pathlib import Path
from pprint import pprint
import xml.etree.ElementTree as ET
from collections import defaultdict
from xml.dom import minidom
from itertools import chain

DEBUG_PRINT = True


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def indent(elem, level=0, hor='    ', ver='\n'):
    i = ver + level * hor
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + hor
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1, hor, ver)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class Comments:

    grids = []


class Segments:

    segments = []

    def add(self, segment):
        self.segments.append(segment)


class CenterCurve:
    """[summary]

    [description]
    """

    idCounter = 0

    def __init__(self, center_curve):
        CenterCurve.idCounter += 1
        self.num = CenterCurve.idCounter
        self.center_curve = center_curve
        self.control_points = self.center_curve.find('Control_points').text.split()

    @property
    def id(self):
        return self.center_curve.get('id')


class Segment:
    """Segment class for manipulating itself and child instances of Center_Curves and Points.

    num: Number depending on the global Segment counter
    id: Segment id from .kbl
    start_node: Segment Start_node text
    end_node: Segment End_node text
    center_curves: List of CenterCurve() Class instances within Segment
    center_curves_ids: List of Center_Curves ids
    """

    idCounter = 0

    def __init__(self, segment, nodes_dict):
        Segment.idCounter += 1
        self.segment = segment
        self.num = Segment.idCounter
        self.nodes_dict = nodes_dict
        self.id = segment.get('id')
        self.start_node = segment.find('Start_node').text
        self.end_node = segment.find('End_node').text
        self.center_curves = [CenterCurve(curve) for curve in self.segment.findall('Center_curve')]
        self.center_curves_ids = [c.id for c in self.center_curves]
        self._add_start_node()
        self._add_end_node()
        self._add_connecting_control_points()

    def _add_start_node(self):
        """Insert Segment's StartNode [GRID] to 1st position of 1st Center_curve's Control_Points list.

        Additionaly add comment to Point if it's Start_node. If it has already comment, append."""
        self.center_curves[0].control_points.insert(0, self.nodes_dict.get(self.start_node))
        for point in Points.points:
            if point.id == self.nodes_dict.get(self.start_node):
                if point.comment == "":
                    point.comment = f"{self.start_node} [start]"
                else:
                    point.comment = f"{self.start_node} [start], {point.comment}"

    def _add_end_node(self):
        """Insert Segment's EndNode [GRID] to last position of last Center_curve's Control_Points list.

        Additionaly add comment to Point if it's End_node. If it has already comment, append."""
        self.center_curves[-1].control_points.append(self.nodes_dict.get(self.end_node))
        for point in Points.points:
            if point.id == self.nodes_dict.get(self.end_node):
                if point.comment == "":
                    point.comment = f"{self.end_node} [end]"
                else:
                    point.comment = f"{point.comment}, {self.end_node} [end]"


    def _add_connecting_control_points(self):
        """Add connnecting control point to beginning of each center_curve.

        Example:
            Center_curve_01 = [20, 21, 22, 23]
            Center_curve_02 = [24, 25, 26, 27]
            Center_curve_03 = [28.29]

            add_connecting_control_points()

            Center_curve_01 = [20, 21, 22, 23]
            Center_curve_02 = [23, 24, 25, 26, 27]
            Center_curve_03 = [27. 28, 29]
        """
        for prev_curve, next_curve in zip(self.center_curves[0:-1], self.center_curves[1:]):
            next_curve.control_points.insert(0, prev_curve.control_points[-1])


class Points:

    points = []

    def add(self, point):
        self.points.append(point)

    def get_num_from_id(self, point_id):
        """Get_num_from_id("Cartesian_point_28") --> 28."""
        for point in self.points:
            if point.id == point_id:
                return point.num
        return None

    def get_id_from_num(self, point_num):
        """Get_id_from_num(28) --> "Cartesian_point_28"."""
        for point in self.points:
            if point.num == point_num:
                return point.id
        return None


class Point:
    """Cartesian Point class manipulating.

    Init Args:
        point_id <str> = Cartesian_point_46
        coords_list <list> = [-100, 65.43325, 14.556]

    id: return Cartesian_Point id
    x: return x coord
    y: return y coord
    z: return z coord
    """

    idCounter = 0

    def __init__(self, point_id, coords_list):
        self.coords = coords_list
        self._point_id = point_id
        Point.idCounter += 1
        self.num = Point.idCounter
        self.comment = ""

    @property
    def id(self):
        return self._point_id

    @property
    def x(self):
        num = round(float(self.coords[0]), 5)
        return str(num)[0:8]

    @property
    def y(self):
        num = round(float(self.coords[1]), 5)
        return str(num)[0:8]

    @property
    def z(self):
        num = round(float(self.coords[2]), 5)
        return str(num)[0:8]

    def __repr__(self):
        return f"{self.__class__.__name__}(id: {self.id}; num: {self.num}; [{self.x}, {self.y}, {self.z}])"


def kbl2nas(DEBUG):
    """Cable to Nas, 1 Argument neded (.kbl file)."""
    if DEBUG:
        filepath = Path(__file__).parent.resolve() / 'examples' / 'TEST_VELKY.kbl'
        # filepath = Path(__file__).parent.resolve() / 'examples' / '190305-export.10mm.kbl'
    else:
        filepath = Path(sys.argv[1]).resolve()

    if filepath.suffix != '.kbl':
        print("Not KBL file!!!")
        sys.exit(1)

    outfile = f'{filepath.parent}/{filepath.stem}.nas'

    # Load ETREE
    with open(filepath, 'rt') as f:
        tree = ET.parse(f)
        root = tree.getroot()

    # Get nodes that will be added to existing 'Control points' (start, end)
    nodes_dict = {node.get('id'): node.find('Cartesian_point').text for node in root.findall('Node')}

    # Here will be appended all future lines
    lines = []

    # =============
    # GRID
    # =============
    points = [Point(point.get('id'), [coord.text for coord in point.findall('Coordinates')])
              for point in root.findall('Cartesian_point')]
    clsPoints = Points()
    for point in points:
        clsPoints.add(point)
        line_text = f"{'GRID': <8}{point.num: >8}{point.x: >16}{point.y: >8}{point.z: >8}"
        if DEBUG_PRINT is True: print(line_text)
        lines.append(f"{line_text}\n")

    # =============
    # CROD
    # =============
    clsSegments = Segments()
    idx = 1
    for item in root.findall('Segment'):
        segment = Segment(item, nodes_dict)
        clsSegments.add(segment)

        for center_curve in segment.center_curves:
            for p_start, p_end in zip(center_curve.control_points[0:-1], center_curve.control_points[1:]):
                p_start_num = clsPoints.get_num_from_id(p_start)
                p_end_num = clsPoints.get_num_from_id(p_end)
                line_text = f"{'CROD': <8}{idx: >8}{center_curve.num: >8}{p_start_num: >8}{p_end_num: >8}"
                if DEBUG_PRINT is True: print(line_text)
                lines.append(f"{line_text}\n")
                idx += 1

    # =============
    # PROD
    # =============
    for segment in clsSegments.segments:
        for curve in segment.center_curves:
            line_text = f"{'PROD': <8}{curve.num: >8}{segment.num: >8}{'50.': >8}{'0.': >8}"
            if DEBUG_PRINT is True: print(line_text)
            lines.append(f"{line_text}\n")

    # ==========================
    # ANSA_NAME_COMMENT - PROD
    # ==========================
    for segment in Segments.segments:
        for center_curve in segment.center_curves:
            cp_text = ', '.join(center_curve.control_points)
            line_text = f"$ANSA_NAME_COMMENT;{center_curve.num};PROD;{center_curve.id};{cp_text};NO;NO;NO;"
            if DEBUG_PRINT is True: print(line_text)
            lines.append(f"{line_text}\n")

    # ==========================
    # ANSA_NAME_COMMENT - GRID
    # ==========================
    for point in points:
        line_text = f"$ANSA_NAME_COMMENT;{point.num};GRID;{point.id};{point.comment};NO;NO;NO;"
        if DEBUG_PRINT is True: print(line_text)
        lines.append(f"{line_text}\n")

    # ==========================
    # ANSA_NAME_COMMENT - MAT1
    # ==========================
    for segment in clsSegments.segments:
        line_text = f"$ANSA_NAME_COMMENT;{segment.num};MAT1;{segment.id};;YES;NO;NO;"
        # line_text = f"$ANSA_NAME_COMMENT;{idx};GRID;{grid.get('id')};;NO;NO;NO;"
        if DEBUG_PRINT is True: print(line_text)
        lines.append(f"{line_text}\n")

    # Write into a file
    with open(outfile, 'w') as f:
        f.writelines(lines)


def nas2kbl(DEBUG):
    """Nas to Cable, 2 arguments needed (.nas, .kbl)."""
    print("Hej hou...")

    if DEBUG:
        nas_filepath = Path(__file__).parent.resolve() / 'examples' / 'TEST_VELKY.nas'
        kbl_filepah = Path(__file__).parent.resolve() / 'examples' / 'TEST_VELKY.kbl'
    else:
        nas_filepath = Path(sys.argv[1]).resolve()
        kbl_filepah = Path(sys.argv[2]).resolve()

    check_correct_suffix(nas_filepath, kbl_filepah)

    outfile = f'{kbl_filepah.parent}/{kbl_filepah.stem}.PARSED.kbl'

    print("[ DEBUG ] nas_filepath:", nas_filepath)
    print("[ DEBUG ] kbl_filepah:", kbl_filepah)
    print("[ DEBUG ] outfile:", outfile)

    # Load ETREE
    # with open(kbl_filepah, 'rt') as f:
    #     tree = ET.parse(f)
    #     root = tree.getroot()

    print("[ DEBUG ] Parsing etree...")
    tree = ET.parse(kbl_filepah)
    root = tree.getroot()

    # BETTER NICER ETREE
    # res = ET.tostring(root, encoding="utf-8", method="xml").decode('utf-8')
    # print(res)

    print("[ DEBUG ] Reading lines from 'nas_filepath'")
    with open(nas_filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines()]


    print("[ DEBUG ] Loading GRID lines and parsing them into Point() Class")
    points_dc = {}
    for line in lines:
        if line.startswith('GRID'):
            pid_num = line[8:16].strip()
            pid = f'Cartesian_point_{pid_num}'
            px = line[24:32].strip()
            py = line[32:40].strip()
            pz = line[40:48].strip()
            # points.append(Point(pid, [px, py, pz]))
            points_dc[pid_num] = Point(pid, [px, py, pz])

    pprint(points_dc)

    # print("[ DEBUG ] Removing all Cartesian_points...")
    # # ADD Cartesian Points
    # for cartes_point in root.findall('Cartesian_point'):
    #     root.remove(cartes_point)
    #     # print(f"id: {cartes_point.get('id')}")
    #     # id_num = cartes_point.get('id').split('_')[-1]
    #     # if id_num in points_dc.keys():
    #     #     print("Point is there, delete")
    #     #     root.remove(cartes_point)
    #     # else:
    #     #     print("point not there, let it be...")

    # print("[ DEBUG ] Creating new Cartesian_points structure modified .nas file")
    # # Need to add it into a list that will be reverset so that inserting into XML is 1, 2, 3, not 3, 2, 1
    # my_cartes_list = []
    # for item, value in points_dc.items():
    #     value: Point
    #     pid, ls = value.id_num, value.coords
    #     # myCartes = ET.SubElement(root, "Cartesian_point", id=f"Cartesian_point_{pid}")
    #     myCartes = ET.Element("Cartesian_point", id=f"Cartesian_point_{pid}")
    #     for coord in ls:
    #         ET.SubElement(myCartes, "Coordinates").text = coord
    #     my_cartes_list.append(myCartes)

    # print("[ DEBUG ] Inserting Cartesian_points into new .PARSED.kbl file, from biggest to lowest")
    # # Insert Cartesian_points to the TOP of root
    # for myCartes in reversed(my_cartes_list):
    #     print(f"[ DEBUG ] Writing: {myCartes.get('id')}")
    #     root.insert(0, myCartes)

    # print("[ DEBUG ] Loading CROD lines and parsing them into crod_dc dict...")
    # crod_dc = defaultdict(list)
    # for line in lines:
    #     if line.startswith('CROD'):
    #         cid = int(line[16:24].strip())
    #         start = int(line[24:32].strip())
    #         end = int(line[32:40].strip())
    #         crod_dc[cid].append([start, end])
    # # print(crod_dc)

    # print("[ DEBUG ] Chaining lists of lists inside crod_dc.values() into crod_dc_chained...")
    # crod_dc_chained = {}
    # for key, vals in crod_dc.items():
    #     crod_dc_chained[key] = list(chain(*vals))
    # # print(crod_dc_chained)

    # print("[ DEBUG ] Making list from crod_dc_chained.values() unique to new dict crod_dc_chained_uniq")
    # crod_dc_chained_uniq = {}
    # for key, vals in crod_dc_chained.items():
    #     used = set()
    #     unique = [x for x in vals if x not in used and (used.add(x) or True)]
    #     crod_dc_chained_uniq[key] = unique
    # # print(crod_dc_chained_uniq)

    # print("[ DEBUG ] Removing first and last value from crod_dc_chained_uniq")
    # start_end_nodes = {}
    # nodes_set = set()
    # for key, val in crod_dc_chained_uniq.items():
    #     start_node, end_node = val[0], val[-1]
    #     # Extract first and last element into set
    #     nodes_set.add(start_node)
    #     nodes_set.add(end_node)
    #     # Make dictionary of these couples
    #     start_end_nodes[key] = [f'Cartesian_point_{start_node}', f'Cartesian_point_{end_node}']
    #     # Delete first element and last element
    #     crod_dc_chained_uniq[key] = crod_dc_chained_uniq[key][1:-1]

    # # print("crod_dc_chained_uniq:", crod_dc_chained_uniq)
    # # print("nodes_set:", nodes_set)
    # # print("DEBUG: start_end_nodes:", start_end_nodes)
    # node_dc = {}
    # for idx, node_num in enumerate(sorted(nodes_set), 1):
    #     node_dc[f'Node_{idx}'] = f'Cartesian_point_{node_num}'
    # # print("DEBUG: node_dc:", node_dc)

    # print("[ DEBUG ] Modifying 'Node' elements within .kbl file")
    # # Modify 'Node'
    # cart_to_node_dc = {}
    # for node in root.findall('Node'):
    #     cartesian_point = node.find('Cartesian_point')
    #     cartesian_point: ET.Element
    #     print(f"[ DEBUG ]   {node.get('id')}: {node_dc[node.get('id')]}")
    #     cartesian_point.text = node_dc[node.get('id')]
    #     cart_to_node_dc[node_dc[node.get('id')]] = node.get('id')

    # # print("DEBUG: cart_to_node_dc:", cart_to_node_dc)

    # print("[ DEBUG ] Iterating over .kbl segments and modifying 'start_node', 'end_node' and 'Control_points'")
    # # For each 'Segment' Modify 'Center_curve - Control_points', 'End_node' and 'Start_node'
    # for segment, (key, vals) in zip(root.findall('Segment'), crod_dc_chained_uniq.items()):
    #     print(f"[ DEBUG ] {segment.get('id')}")
    #     segment_num = segment.get('id').split('_')[-1]

    #     # Modify 'Start_node'
    #     print(f"[ DEBUG ]   Modifying 'start_node' = {cart_to_node_dc[start_end_nodes[key][0]]}")
    #     start_node = segment.find('Start_node')
    #     start_node.text = str(cart_to_node_dc[start_end_nodes[key][0]])

    #     # Modify 'End_node'
    #     print(f"[ DEBUG ]   Modifying 'end_node' = {cart_to_node_dc[start_end_nodes[key][1]]}")
    #     end_node = segment.find('End_node')
    #     end_node.text = str(cart_to_node_dc[start_end_nodes[key][1]])

    #     # Modify 'Center_curve'
    #     print(f"[ DEBUG ]   Modifying 'Center_curve' = {vals}")
    #     full_text = ' '.join([f'Cartesian_point_{val}' for val in vals])
    #     center_curve = segment.find('Center_curve')
    #     control_points = center_curve.find('Control_points')
    #     control_points.text = full_text

    # print(f"[ DEBUG ] Copying etree into new .PARSED.kbl file: '{outfile}'")
    # # res = prettify(root)
    # res = indent(root)
    # tree.write(outfile)

    # print("[ DEBUG ] Fixing xml <ns0: --> <kbl: first 3 lines and list line within '.PARSED.kbl'. Reasons: unknown...")
    # with open(outfile, 'r') as f:
    #     xml_lines = [line.replace('ns0', 'kbl') if 'ns0' in line else line for line in f.readlines()]
    # with open(outfile, 'w') as f:
    #     f.writelines(xml_lines)

    # print("[ INFO ] DONE")











    ## Testing MENU
    # from pimento import menu
    # result = menu(
    #     ['Yes', 'No'],
    #     pre_prompt='Available options:',
    #     post_prompt='Do you want to continue? [{}]: ',
    #     default_index=0,
    #     indexed=True,
    #     insensitive=True,
    #     fuzzy=True
    # )
    # print("DEBUG: result:", result)

    # ## https://github.com/kamik423/cutie
    # import cutie
    # if not cutie.prompt_yes_or_no("Are you want continuing?", enter_empty_confirms=True):
    #     exit()

    # names = [
    #     'Normalni odpovedi:',
    #     'Yes',
    #     'No',
    #     'Divne odpovedi:',
    #     'Very much indeed',
    #     'Whoooo, NONONO',
    # ]
    # captions = [0, 3]
    # name = names[
    #     cutie.select(names, caption_indices=captions, selected_index=0)]
    # # cutie.select(names, selected_index=0)]
    # print(f"You just pressed: {name}")
    # age = cutie.get_number(
    #     'What is your age?',
    #     min_value=0,
    #     max_value=30,
    #     allow_float=False)
    # print(f"Your age: {age}")
    # quest = cutie.secure_input('Secretos Passwordos: ')
    # print(f"Ha, I've got you pass: {quest}")


def check_correct_suffix(nas_file, kbl_file):
    """Check if nas_file has .nas suffix and kbl_file has .kbl suffix, end otherwise."""
    if nas_file.suffix != '.nas':
        print("Not NAS file!!!")
        sys.exit(1)
    if kbl_file.suffix != '.kbl':
        print("Not KBL file!!!")
        sys.exit(1)
    return 0


def main():
    DEBUG = True

    if DEBUG:
        kbl2nas(DEBUG)
        # nas2kbl(DEBUG)

    if not DEBUG and len(sys.argv) == 1:
        print("No arguments...")
        sys.exit(1)

    elif not DEBUG and len(sys.argv) == 2:
        kbl2nas(DEBUG)

    elif not DEBUG and len(sys.argv) == 3:
        nas2kbl(DEBUG)

    elif not DEBUG and len(sys.argv) > 3:
        print("Wrong number of arguments...")
        sys.exit(1)


if __name__ == '__main__':
    main()
