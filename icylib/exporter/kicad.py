
import math


def export_eeschema_library(components, out_file):
    out_file.write("EESchema-LIBRARY Version 2.3\n")
    out_file.write("#encoding utf-8\n")
    for component in components:
        for package_mapping in component.package_mappings:
            package = package_mapping.package
            full_name = "-".join((component.name, package.name))
            full_caption = "%s(%s)" % (component.name, package.name)
            sides = [
                [
                    (
                        component.pin_groups.top_power,
                        component.pin_groups.left,
                        component.pin_groups.bottom_power,
                    ),
                    [], # pins
                    0, # max label length
                    0, # x coord
                    "R", # direction
                ],
                [
                    (
                        component.pin_groups.right,
                    ),
                    [], # pins
                    0, # max label length
                    0, # x coord
                    "L", # direction
                ]
            ]
            # Plan the layout
            for side in sides:
                pin_group_categories = side[0]
                pins = side[1]
                max_label_length = 0
                for pin_group_category in pin_group_categories:
                    for pin_group in pin_group_category:
                        if len(pins) > 0 and pins[-1] is not None:
                            pins.append(None)  # Leave a blank
                        for pin in pin_group:
                            if not package_mapping.has_pin(pin):
                                continue
                            pins.append(pin)
                            plain_label = pin.label.replace("~", "")
                            if len(plain_label) > max_label_length:
                                max_label_length = len(plain_label)
                side[2] = max_label_length
                # Clean up trailing None that may have resulted from pins that
                # are not available on the current package.
                if len(pins) > 0 and pins[-1] is None:
                    pins.pop()

            # If the left side is shorter than the right side then
            # we need to move the bottom power pins down to the bottom
            # of the row.
            if len(sides[0][1]) < len(sides[1][1]) and None in sides[0][1]:
                move_from = len(sides[0][1]) - 1
                move_to = len(sides[1][1]) - 1
                sides[0][1].extend([None] * (move_to - move_from))
                while True:
                    if sides[0][1][move_from] is None:
                        break
                    sides[0][1][move_to] = sides[0][1][move_from]
                    sides[0][1][move_from] = None
                    move_to -= 1
                    move_from -= 1

            max_rows = max(len(sides[0][1]), len(sides[1][0]))

            width = (sides[0][2] * 50) + (sides[1][2] * 50) + 150
            if width < (len(full_caption) * 60):
                width = len(full_caption) * 60
            height = max_rows * 100 + 100

            # Make sure width is a round grid increment.
            # (it might not be if we grew out the width to fit the
            # component caption)
            width = int(math.ceil(float(width / 50)) * 50)

            sides[1][3] = width

            out_file.write("DEF %s IC 0 40 Y Y 1 F N\n" % full_name)
            out_file.write("F0 \"IC\" %i %i 60 H V L CNN\n" % (
                0, height + 50,
            ))
            out_file.write("F1 \"%s\" %i %i 60 H V R CNN\n" % (
                full_caption,
                width, -50,
            ))
            out_file.write("DRAW\n")
            # Outline Rectangle
            out_file.write("S 0 0 %i %i 0 0 0 N\n" % (width, height))
            # Pins
            pin_length = 300
            for side in sides:
                pins = side[1]
                direction = side[4]
                xpos = side[3] + (pin_length if direction == "L" else -pin_length)
                ypos = height - 100
                for pin in pins:
                    if pin is not None:
                        pad_num = package_mapping.pad_number_for_pin(pin)
                        # TODO: The hard-coded "B" on the end should
                        # actually be set based on the pin's ERC type.
                        # input I, output O, bidirectional B, W powerIn, w powerOut
                        out_file.write("X %s %i %i %i %i %s 50 50 1 1 B\n" % (
                            pin.label,
                            pad_num,
                            xpos,
                            ypos,
                            pin_length,
                            direction,
                        ))
                    ypos = ypos - 100
            out_file.write("ENDDRAW\n")
            out_file.write("ENDDEF\n")
    out_file.write("# End Library\n")


def export_eeschema_doclib(components, out_file):
    out_file.write("EESchema-DOCLIB Version 2.0\n")
    out_file.write("#\n")
    for component in components:
        out_file.write("$CMP %s\n" % component.name)
        out_file.write("D %s\n" % component.description)
        out_file.write("$ENDCMP %s\n" % component.name)
    out_file.write("#\n")
    out_file.write("#End Doc Library\n")
