#!/usr/bin/python3
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


class Point:
    """Cartesian Point."""

    def __init__(self, point_id, coords_list):
        super(Point, self).__init__()
        self.coords = coords_list
        self.point_id = point_id

    @property
    def id(self):
        return self.point_id

    @property
    def id_num(self):
        return self.point_id.split('_')[-1]

    @property
    def x(self):
        return round(float(self.coords[0]), 4)

    @property
    def y(self):
        return round(float(self.coords[1]), 4)

    @property
    def z(self):
        return round(float(self.coords[2]), 4)


def main():
    DEBUG = False
    if DEBUG:
        filepath = '/ST/Evektor/UZIV/JVERNER/PROJEKTY/UZIV/DKRUTILEK/2019-03-28_KBL2NAS/190305-export.10mm.kbl'
        filepath = Path(filepath).resolve()
    else:
        filepath = Path(sys.argv[1]).resolve()
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


if __name__ == '__main__':
    main()