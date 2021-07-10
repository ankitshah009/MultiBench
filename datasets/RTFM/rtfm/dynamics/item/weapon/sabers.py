# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from .base_weapon import Weapon
from ... import dice as D, material as M


class BaseSaber(Weapon):
    pass


class SilverSaber(BaseSaber):

    def __init__(self):
        super().__init__('silver saber', weight=40, damage=D.Dice.from_str('d8'), material=M.Silver, hit=0)
