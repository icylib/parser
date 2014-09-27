
import os
import os.path

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
        # TODO: Parse the name to figure out the physical dimensions
        # based on standard package types.


class PackageMapping(object):

    def __init__(self, component, package, pin_mapping):
        self.component = component
        self.package = package
        self.pin_mapping = pin_mapping

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
