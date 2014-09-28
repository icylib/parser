
import os
import os.path
import pint


unit = pint.UnitRegistry()


class Library(object):

    def __init__(self, base_dir):
        self.base_dir = base_dir

    @property
    def components_dir(self):
        return os.path.join(self.base_dir, "components")

    @property
    def component_manufacturers(self):
        for code in os.listdir(self.components_dir):
            manufacturer_dir = os.path.join(self.components_dir, code)
            if os.path.isdir(manufacturer_dir):
                yield Manufacturer(self, code, manufacturer_dir)

    @property
    def components(self):
        for manufacturer in self.component_manufacturers:
            for component in manufacturer.components:
                yield component


class Manufacturer(object):

    def __init__(self, library, code, base_dir):
        self.base_dir = base_dir
        self.code = code
        self.library = library

    @property
    def components(self):
        for filename in os.listdir(self.base_dir):
            if filename[-5:] != ".json":
                continue
            name = filename[:-5]
            f = open(os.path.join(self.base_dir, filename), 'r')
            yield Component.from_file(self, name, f)


class Component(object):

    def __init__(self, manufacturer, name, json_dict):
        self.name = name
        self.json_dict = json_dict
        self.manufacturer = manufacturer
        pins_dict = self.json_dict.get("pins", {})
        self.pin_groups = ComponentPinGroups(self, pins_dict)

    @classmethod
    def from_file(cls, manufacturer, name, f):
        import json
        return Component(manufacturer, name, json.load(f))

    @property
    def description(self):
        return self.json_dict.get("description")

    @property
    def datasheet_url(self):
        return self.json_dict.get("datasheetUrl")

    @property
    def package_mappings(self):
        packages_dict = self.json_dict.get("packages", {})
        for name, mapping_dict in packages_dict.iteritems():
            package = Package(name)
            yield PackageMapping(self, package, mapping_dict)

    def __repr__(self):
        return "<icylib.Component %s %s>" % (
            self.manufacturer.code,
            self.name,
        )


class ComponentPinGroups(object):

    def __init__(self, component, pins_dict):
        self.component = component
        self.pins_dict = pins_dict

        pins = {}

        # Build a mapping of pin label to pin object ahead of time,
        # so callers can access pins both by name and by browsing
        # the groups.
        category_names = ("topPower", "bottomPower", "left", "right")
        for category_name in category_names:
            if category_name not in pins_dict:
                continue

            pin_groups = pins_dict[category_name]
            for pin_group in pin_groups:
                for i, pin_dict in enumerate(pin_group):
                    pin = ComponentPin(component, pin_group[i])
                    pin_group[i] = pin
                    pins[pin.label] = pin

    @property
    def top_power(self):
        return self.pins_dict.get("topPower", [])

    @property
    def bottom_power(self):
        return self.pins_dict.get("bottomPower", [])

    @property
    def left(self):
        return self.pins_dict.get("left", [])

    @property
    def right(self):
        return self.pins_dict.get("right", [])


class ComponentPin(object):

    def __init__(self, component, pin_dict):
        self.component = component
        self.pin_dict = pin_dict

    @property
    def label(self):
        return self.pin_dict.get("label")

    @property
    def erc_type(self):
        return ErcType.by_code(self.pin_dict.get("ercType"))

    def __repr__(self):
        return "<icylib.ComponentPin %s>" % self.label


class Package(object):

    def __init__(self, name):
        self.name = name
        name_parts = name.split("-")
        family = name_parts[0]

        num_sides = None
        self.hole_size = None  # stays None for surface mount
        self.top_dent = False  # show the "dimple" at the top of the silkscreen
        self.pin_1_marker = False  # show the dot next to pin 1
        self.row_spacing = None # Only set for two-sided packages

        if family == "DIP":
            if len(name_parts) == 2:
                name_parts.append("300")
            if len(name_parts) == 3:
                self.pad_count = int(name_parts[1])
                self.hole_size = 32 * unit.mil
                self.pad_width = 55 * unit.mil
                self.pad_length = 55 * unit.mil
                self.pad_pitch = 100 * unit.mil
                self.row_spacing = int(name_parts[2]) * unit.mil
                self.top_dent = True
                num_sides = 2
            else:
                raise Exception("Invalid DIP package specification")
        elif family == "SIP":
            if len(name_parts) == 2:
                self.pad_count = int(name_parts[1])
                self.hole_size = 32 * unit.mil
                self.pad_width = 55 * unit.mil
                self.pad_length = 55 * unit.mil
                self.pad_pitch = 100 * unit.mil
                num_sides = 1
            else:
                raise Exception("Invalid SIP package specification")
        elif family == "SO":
            if len(name_parts) == 2:
                name_parts.append("N")
            if len(name_parts) == 3:

                if name_parts[2] == "N":
                    name_parts[2] = "5.4"
                elif name_parts[2] == "W":
                    name_parts[2] = "9.3"

                self.pad_count = int(name_parts[1])
                self.pad_width = 0.60 * unit.mm
                self.pad_length = 1.55 * unit.mm
                self.pad_pitch = 50 * unit.mil
                self.row_spacing = float(name_parts[2]) * unit.mm
                self.top_dent = True
                num_sides = 2
            else:
                raise Exception("Invalid SO package specification")
        elif family in ("QFP", "TQFP"):
            if len(name_parts) == 3:
                self.pad_count = int(name_parts[1])
                self.pad_pitch = float(name_parts[2]) * unit.mm
                self.pin_1_marker = True
                num_sides = 4
            else:
                raise Exception("Invalid QFP package specification")
        else:
            raise Exception("Unsupported package family '%s'" % family)

        if self.pad_count % num_sides != 0:
            raise Exception("%s pin count must be divisible by %i" % (
                family, num_sides,
            ))

        pads_each_side = self.pad_count / num_sides
        self.left_pads = range(1, pads_each_side + 1)
        if num_sides == 1:
            self.right_pads = None
            self.top_pads = None
            self.bottom_pads = None
        elif num_sides == 2:
            self.right_pads = range(pads_each_side * 2, pads_each_side, -1)
            self.top_pads = None
            self.bottom_pads = None
        elif num_sides == 4:
            self.bottom_pads = range(
                pads_each_side + 1, (pads_each_side * 2) + 1
            )
            self.right_pads = range(
                pads_each_side * 3, (pads_each_side * 2), -1,
            )
            self.top_pads = range(
                pads_each_side * 4, (pads_each_side * 3), -1,
            )
        else:
            raise Exception("Can't make a %i-sided package" % num_sides)


class PackageMapping(object):

    def __init__(self, component, package, mapping_dict):
        self.component = component
        self.package = package
        self.pin_mapping = mapping_dict.get("pads", [])
        self.pad_mapping = {
            label: i + 1 for i, label in enumerate(self.pin_mapping)
        }

    def has_pin(self, pin):
        return pin.label in self.pad_mapping

    def pad_number_for_pin(self, pin):
        return self.pad_mapping[pin.label]

    def __repr__(self):
        return "<icylib.PackageMapping %s %r>" % (
            self.package.name,
            self.pin_mapping,
        )


class ErcType(object):

    by_code = {
        None: None
    }

    def __init__(self, code):
        self.code = code
        ErcType.by_code[code] = self


ErcType.power_in = ErcType("powerIn")
ErcType.power_out = ErcType("powerOut")
ErcType.input = ErcType("input")
ErcType.output = ErcType("output")
ErcType.bidirectional = ErcType("bidirectional")
# TODO: more of these
