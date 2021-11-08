from collections import OrderedDict

from . import bge_common


class Realtime(bge_common.CommonClass):
    args = OrderedDict([
        ("property_name", "prop"),
        ("freq_from", 50),
        ("freq_to", 200),
        ("factor", 1.0),
        ("add", 0.0),
    ])

    def _start(self, args):
        for key in args.keys():
            setattr(self, key, args[key])

    def update(self):
        val = self.driver(
            self.freq_from,
            self.freq_to
        ) * self.factor + self.add
        self.object[self.property_name] = val
        # scene = bge.logic.getCurrentScene()
        # if val>2:
        #     scene.addObject('Torus', self.object, 1.0)
