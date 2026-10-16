import importlib.machinery
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader("wmbluetooth", os.path.join(ROOT, "wmbluetooth"))
_spec = importlib.util.spec_from_loader("wmbluetooth", _loader)
wm = importlib.util.module_from_spec(_spec)
_loader.exec_module(wm)

ADAPTER, DEVICE, BATTERY = wm.ADAPTER, wm.DEVICE, wm.BATTERY


def objects(*devices, powered=True):
    result = {"/org/bluez": {}, "/org/bluez/hci0": {ADAPTER: {"Powered": powered}}}
    for mac, props, battery in devices:
        path = "/org/bluez/hci0/dev_" + mac.replace(":", "_")
        result[path] = {DEVICE: props}
        if battery is not None:
            result[path][BATTERY] = {"Percentage": battery}
    return result


def device(name, connected, battery=None, **extra):
    return {"name": name, "connected": connected, "battery": battery, "path": "", "mac": "", **extra}


def state(devices, powered=True, available=True):
    return {"available": available, "powered": powered, "devices": devices}


def pixels(surface):
    return bytes(surface.get_data())


class ParseTests(unittest.TestCase):
    def test_mac_from_path(self):
        self.assertEqual(wm.mac_from_path("/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"), "AA:BB:CC:DD:EE:FF")

    def test_no_adapter(self):
        self.assertFalse(wm.parse_objects({"/org/bluez": {}})["available"])

    def test_powered_flag(self):
        self.assertTrue(wm.parse_objects(objects(powered=True))["powered"])
        self.assertFalse(wm.parse_objects(objects(powered=False))["powered"])

    def test_devices_battery_and_order(self):
        parsed = wm.parse_objects(objects(
            ("AA:00:00:00:00:02", {"Alias": "Zed", "Paired": True, "Connected": False}, None),
            ("AA:00:00:00:00:01", {"Alias": "Pods", "Paired": True, "Connected": True}, 82),
        ))
        names = [(d["name"], d["connected"], d["battery"]) for d in parsed["devices"]]
        self.assertEqual(names, [("Pods", True, 82), ("Zed", False, None)])   # connected devices first
        self.assertEqual(parsed["devices"][0]["mac"], "AA:00:00:00:00:01")

    def test_unpaired_unconnected_devices_are_ignored(self):
        parsed = wm.parse_objects(objects(("AA:00:00:00:00:03", {"Alias": "Neighbour", "Paired": False,
                                                                  "Connected": False}, None)))
        self.assertEqual(parsed["devices"], [])

    def test_name_falls_back_to_mac(self):
        parsed = wm.parse_objects(objects(("AA:00:00:00:00:04", {"Paired": True, "Connected": True}, None)))
        self.assertEqual(parsed["devices"][0]["name"], "AA:00:00:00:00:04")


class RenderTests(unittest.TestCase):
    def test_size(self):
        surface = wm.render(state([]))
        self.assertEqual((surface.get_width(), surface.get_height()), (58, 58))

    def test_states_look_different(self):
        shots = {
            "none": pixels(wm.render(state([device("Mouse", False)]))),
            "one": pixels(wm.render(state([device("Pods", True, 80)]))),
            "low": pixels(wm.render(state([device("Pods", True, 10)]))),
            "off": pixels(wm.render(state([], powered=False))),
            "gone": pixels(wm.render(state([], available=False))),
        }
        self.assertEqual(len(set(shots.values())), len(shots))

    def test_many_devices_do_not_crash(self):
        wm.render(state([device(f"Device number {i}", True, i * 10) for i in range(9)]))

    def test_connected_count_is_drawn(self):
        one = pixels(wm.render(state([device("A", True, 50)])))
        two = pixels(wm.render(state([device("A", True, 50), device("B", True, 50)])))
        self.assertNotEqual(one, two)

    def test_seven_segment_digits_differ(self):
        import cairo
        shots = set()
        for value in [None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 16)
            wm.seven_segment(cairo.Context(surface), 1, 1, 8, 14, value, wm.TEAL, wm.GHOST)
            shots.add(bytes(surface.get_data()))
        self.assertEqual(len(shots), 11)

    def test_long_name_is_fitted(self):
        import cairo
        cr = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 64, 64))
        fitted = wm.fit_name(cr, "Sony WH-1000XM5 Wireless", 30)
        self.assertLessEqual(cr.text_extents(fitted).x_advance, 30)
        self.assertTrue(fitted.startswith("Sony"))


if __name__ == "__main__":
    unittest.main()
