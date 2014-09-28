
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
            out_file.write("$FPLIST\nIC-%s\n$ENDFPLIST\n" % package.name)
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


def export_pcbnew_module(package, out_file):
    from icylib.model import unit
    out_file.write("(module IC-%s\n" % package.name)
    out_file.write("  (at 0 0)\n")
    if package.hole_size is None:
        out_file.write("  (attr smd)\n")

    pad_sets = []
    pad_sets.append(
        [
            package.left_pads,
            (
                0.0 * unit.mm,
                ((len(package.left_pads) - 1) * package.pad_pitch) / -2,
            ),
            (0.0 * unit.mm, package.pad_pitch),
            0.0,
        ]
    )
    if package.row_spacing is not None:
        # Shift the left pads leftwards to center on the middle of the
        # package.
        left_pad_set = pad_sets[0]
        left_pad_set[1] = (package.row_spacing / -2, left_pad_set[1][1])
        # Populate the right pads.
        pad_sets.append(
            [
                package.right_pads,
                (package.row_spacing / 2.0, left_pad_set[1][1]),
                (0.0 * unit.mm, package.pad_pitch),
                0.0,
            ]
        )

    for pad_set in pad_sets:
        next_x = pad_set[1][0]
        next_y = pad_set[1][1]
        for pad_num in pad_set[0]:
            out_file.write("  (pad %i %s %s" % (
                pad_num,
                "thru_hole" if package.hole_size is not None else "smd",
                "rect" if package.hole_size is None else (
                    "rect" if pad_num == 1 else "circle"
                ),
            ))

            out_file.write(" (at %f %f)" % (
                next_x.to(unit.mm).magnitude,
                next_y.to(unit.mm).magnitude,
            ))
            out_file.write(" (size %f %f)" % (
                package.pad_length.to(unit.mm).magnitude,
                package.pad_width.to(unit.mm).magnitude,
            ))

            if package.hole_size is not None:
                out_file.write(" (drill %f)" % (
                    package.hole_size.to(unit.mm).magnitude,
                ))
                out_file.write(" (layers *.Cu *.Mask F.SilkS)")
            else:
                out_file.write(" (layers F.Cu F.Mask F.SilkS)")

            out_file.write(")\n")

            next_x += pad_set[2][0]
            next_y += pad_set[2][1]

    out_file.write(")\n")
