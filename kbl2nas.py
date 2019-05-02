#!/expSW/SOFTWARE/python371/bin/python3
import sys
from pathlib import Path
from pprint import pprint
import xml.etree.ElementTree as ET
from collections import defaultdict
from xml.dom import minidom
from itertools import chain


class Point:
    """Cartesian Point.

    point_id ... Cartesian_point_46
    coords_list ... [-100, 65.43325, 14.556]
    """

    def __init__(self, point_id, coords_list):
        super(Point, self).__init__()
        self.coords = coords_list
        self._point_id = point_id

    @property
    def id(self):
        return self._point_id

    @property
    def id_num(self):
        return int(self._point_id.split('_')[-1])

    @property
    def x(self):
        return round(float(self.coords[0]), 4)

    @property
    def y(self):
        return round(float(self.coords[1]), 4)

    @property
    def z(self):
        return round(float(self.coords[2]), 4)


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
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


def kbl2nas(DEBUG):
    """Cable to Nas, 1 Argument neded (.kbl file)."""
    if DEBUG:
        filepath = Path(__file__).parent.resolve() / 'examples' / '190305-export.10mm.kbl'
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

    points = [Point(point.get('id'), [coord.text for coord in point.findall('Coordinates')])
              for point in root.findall('Cartesian_point')]

    for point in points:
        print(f"{'GRID': <8}{point.id_num: >8}{point.x: >16}{point.y: >8}{point.z: >8}")
        lines.append(f"{'GRID': <8}{point.id_num: >8}{point.x: >16}{point.y: >8}{point.z: >8}\n")

    cidx = 1
    for idx, segment in enumerate(root.findall('Segment'), 1):
        start_node = segment.find('Start_node').text
        end_node = segment.find('End_node').text

        control_points = segment.find('Center_curve').find('Control_points').text.split()
        control_points = [nodes_dict.get(start_node), *control_points, nodes_dict.get(end_node)]

        for point_start, point_end in zip(control_points[0:-1], control_points[1:]):
            point_start_num = point_start.split('_')[-1]
            point_end_num = point_end.split('_')[-1]
            print(f"{'CROD': <8}{cidx: >8}{idx: >8}{point_start_num: >8}{point_end_num: >8}")
            lines.append(f"{'CROD': <8}{cidx: >8}{idx: >8}{point_start_num: >8}{point_end_num: >8}\n")

            cidx += 1

    for idx, control_points in enumerate(root.findall('Segment/Center_curve/Control_points'), 1):
        print(f"{'PROD': <8}{idx: >8}{idx: >8}{'50.': >8}{'0.': >8}")
        lines.append(f"{'PROD': <8}{idx: >8}{idx: >8}{'50.': >8}{'0.': >8}\n")

    for idx, center_curve in enumerate(root.findall('Segment/Center_curve'), 1):
        print(f"$ANSA_NAME_COMMENT;{idx};PROD;{center_curve.get('id')};;NO;NO;NO;")
        lines.append(f"$ANSA_NAME_COMMENT;{idx};PROD;{center_curve.get('id')};;NO;NO;NO;\n")

    # Write into a file
    with open(outfile, 'w') as f:
        f.writelines(lines)


def nas2kbl(DEBUG):
    """Nas to Cable, 2 arguments needed (.nas, .kbl)."""
    print("Hej hou...")

    if DEBUG:
        nas_filepath = Path(__file__).parent.resolve() / 'examples' / '190305-export.10mm_EDIT_DK_all.nas'
        kbl_filepah = Path(__file__).parent.resolve() / 'examples' / '190305-export.10mm.kbl'
    else:
        nas_filepath = Path(sys.argv[1]).resolve()
        kbl_filepah = Path(sys.argv[1]).resolve()

    # Acquire NAS file
    # nas_filepath = Path(sys.argv[1]).resolve()
    if nas_filepath.suffix != '.nas':
        print("Not NAS file!!!")
        sys.exit(1)

    # Acquire KBL file
    # kbl_filepah = Path(sys.argv[2]).resolve()
    if kbl_filepah.suffix != '.kbl':
        print("Not KBL file!!!")
        sys.exit(1)

    outfile = f'{kbl_filepah.parent}/{kbl_filepah.stem}.PARSED.kbl'

    if DEBUG:
        print("DEBUG: nas_filepath:", nas_filepath)
    if DEBUG:
        print("DEBUG: kbl_filepah:", kbl_filepah)
    if DEBUG:
        print("DEBUG: outfile:", outfile)

    # Load ETREE
    # with open(kbl_filepah, 'rt') as f:
    #     tree = ET.parse(f)
    #     root = tree.getroot()

    tree = ET.parse(kbl_filepah)
    root = tree.getroot()

    # print(prettify(root))

    res = ET.tostring(root, encoding="utf-8", method="xml").decode('utf-8')
    print(res)

    with open(nas_filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines()]

    # points = []
    # points_dc = defaultdict(list)
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

    # ADD Cartesian Points
    for cartes_point in root.findall('Cartesian_point'):
        root.remove(cartes_point)
        # print(f"id: {cartes_point.get('id')}")
        # id_num = cartes_point.get('id').split('_')[-1]
        # if id_num in points_dc.keys():
        #     print("Point is there, delete")
        #     root.remove(cartes_point)
        # else:
        #     print("point not there, let it be...")




def main():
    DEBUG = True

    if DEBUG:
        nas2kbl(DEBUG)

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
