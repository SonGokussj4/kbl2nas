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
        kbl_filepah = Path(sys.argv[2]).resolve()

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

    # pprint(points_dc)

    print("[ DEBUG ] Removing all Cartesian_points...")
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

    print("[ DEBUG ] Creating new Cartesian_points structure modified .nas file")
    # Need to add it into a list that will be reverset so that inserting into XML is 1, 2, 3, not 3, 2, 1
    my_cartes_list = []
    for item, value in points_dc.items():
        value: Point
        pid, ls = value.id_num, value.coords
        # myCartes = ET.SubElement(root, "Cartesian_point", id=f"Cartesian_point_{pid}")
        myCartes = ET.Element("Cartesian_point", id=f"Cartesian_point_{pid}")
        for coord in ls:
            ET.SubElement(myCartes, "Coordinates").text = coord
        my_cartes_list.append(myCartes)

    print("[ DEBUG ] Inserting Cartesian_points into new .PARSED.kbl file, from biggest to lowest")
    # Insert Cartesian_points to the TOP of root
    for myCartes in reversed(my_cartes_list):
        print(f"[ DEBUG ] Writing: {myCartes.get('id')}")
        root.insert(0, myCartes)

    print("[ DEBUG ] Loading CROD lines and parsing them into crod_dc dict...")
    crod_dc = defaultdict(list)
    for line in lines:
        if line.startswith('CROD'):
            cid = int(line[16:24].strip())
            start = int(line[24:32].strip())
            end = int(line[32:40].strip())
            crod_dc[cid].append([start, end])
    # print(crod_dc)

    print("[ DEBUG ] Chaining lists of lists inside crod_dc.values() into crod_dc_chained...")
    crod_dc_chained = {}
    for key, vals in crod_dc.items():
        crod_dc_chained[key] = list(chain(*vals))
    # print(crod_dc_chained)

    print("[ DEBUG ] Making list from crod_dc_chained.values() unique to new dict crod_dc_chained_uniq")
    crod_dc_chained_uniq = {}
    for key, vals in crod_dc_chained.items():
        used = set()
        unique = [x for x in vals if x not in used and (used.add(x) or True)]
        crod_dc_chained_uniq[key] = unique
    # print(crod_dc_chained_uniq)

    print("[ DEBUG ] Removing first and last value from crod_dc_chained_uniq")
    start_end_nodes = {}
    nodes_set = set()
    for key, val in crod_dc_chained_uniq.items():
        start_node, end_node = val[0], val[-1]
        # Extract first and last element into set
        nodes_set.add(start_node)
        nodes_set.add(end_node)
        # Make dictionary of these couples
        start_end_nodes[key] = [f'Cartesian_point_{start_node}', f'Cartesian_point_{end_node}']
        # Delete first element and last element
        crod_dc_chained_uniq[key] = crod_dc_chained_uniq[key][1:-1]

    # print("crod_dc_chained_uniq:", crod_dc_chained_uniq)
    # print("nodes_set:", nodes_set)
    # print("DEBUG: start_end_nodes:", start_end_nodes)
    node_dc = {}
    for idx, node_num in enumerate(sorted(nodes_set), 1):
        node_dc[f'Node_{idx}'] = f'Cartesian_point_{node_num}'
    # print("DEBUG: node_dc:", node_dc)

    print("[ DEBUG ] Modifying 'Node' elements within .kbl file")
    # Modify 'Node'
    cart_to_node_dc = {}
    for node in root.findall('Node'):
        cartesian_point = node.find('Cartesian_point')
        cartesian_point: ET.Element
        print(f"[ DEBUG ]   {node.get('id')}: {node_dc[node.get('id')]}")
        cartesian_point.text = node_dc[node.get('id')]
        cart_to_node_dc[node_dc[node.get('id')]] = node.get('id')

    # print("DEBUG: cart_to_node_dc:", cart_to_node_dc)

    print("[ DEBUG ] Iterating over .kbl segments and modifying 'start_node', 'end_node' and 'Control_points'")
    # For each 'Segment' Modify 'Center_curve - Control_points', 'End_node' and 'Start_node'
    for segment, (key, vals) in zip(root.findall('Segment'), crod_dc_chained_uniq.items()):
        print(f"[ DEBUG ] {segment.get('id')}")
        segment_num = segment.get('id').split('_')[-1]

        # Modify 'Start_node'
        print(f"[ DEBUG ]   Modifying 'start_node' = {cart_to_node_dc[start_end_nodes[key][0]]}")
        start_node = segment.find('Start_node')
        start_node.text = str(cart_to_node_dc[start_end_nodes[key][0]])

        # Modify 'End_node'
        print(f"[ DEBUG ]   Modifying 'end_node' = {cart_to_node_dc[start_end_nodes[key][1]]}")
        end_node = segment.find('End_node')
        end_node.text = str(cart_to_node_dc[start_end_nodes[key][1]])

        # Modify 'Center_curve'
        print(f"[ DEBUG ]   Modifying 'Center_curve' = {vals}")
        full_text = ' '.join([f'Cartesian_point_{val}' for val in vals])
        center_curve = segment.find('Center_curve')
        control_points = center_curve.find('Control_points')
        control_points.text = full_text

    print(f"[ DEBUG ] Copying etree into new .PARSED.kbl file: '{outfile}'")
    # res = prettify(root)
    res = indent(root)
    tree.write(outfile)

    print("[ DEBUG ] Fixing xml <ns0: --> <kbl: first 3 lines and list line within '.PARSED.kbl'. Reasons: unknown...")
    with open(outfile, 'r') as f:
        xml_lines = [line.replace('ns0', 'kbl') if 'ns0' in line else line for line in f.readlines()]
    with open(outfile, 'w') as f:
        f.writelines(xml_lines)

    print("[ INFO ] DONE")

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


def main():
    DEBUG = False

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
