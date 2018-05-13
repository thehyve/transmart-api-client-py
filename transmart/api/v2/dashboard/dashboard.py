"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging

import ipywidgets as widgets

from .hypercube import Hypercube
from .single_tiles import HistogramTile, PieTile, ANIMATION_TIME, NUMERIC_VALUE, STRING_VALUE
from .double_tiles import CombinedPlot, ScatterPlot

from ..widgets import ConceptPicker
from ..constraints import ObservationConstraint, Queryable
from ...commons import filter_tree

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

debug_view = widgets.Output(layout={'border': '1px solid black'})


class Dashboard:

    def __init__(self, api, patients: Queryable=None):
        self.api = api
        self.tiles = list()
        self.hypercube = Hypercube()
        self.__linked_tile = None

        if isinstance(patients, Queryable):
            self.subject_set_id = api.create_patient_set(repr(patients), patients).get('id')
            counts = api.observations.counts_per_study_and_concept(
                subject_set_id=self.subject_set_id
            )
            self.nodes = filter_tree(api.tree_dict, counts)

        else:
            self.subject_set_id = None
            self.nodes = None

        self.out = widgets.Box()
        self.out.layout.flex_flow = 'row wrap'

        self.combination_out = widgets.Box()
        self.combination_out.layout.flex_flow = 'row wrap'

        self.cp = ConceptPicker(self.plotter, api, self.nodes)
        self.counter = widgets.IntProgress(
            value=10, min=0, max=10, step=1,
            orientation='horizontal'
        )

    def get(self):
        return widgets.VBox([self.out, self.counter, self.combination_out, self.cp.get()])

    @debug_view.capture()
    def plotter(self, constraints):
        """
        Add a new tile to dashboard by providing tree node constraints.

        :param constraints: constraints from tree node (concepts and study)
        """
        c = ObservationConstraint.from_tree_node(constraints)

        if self.subject_set_id is not None:
            c.subject_set_id = self.subject_set_id

        obs = self.api.observations(c)
        self.hypercube.add_variable(obs.dataframe)

        name = obs.dataframe['concept.name'][0]

        if NUMERIC_VALUE in obs.dataframe.columns:
            tile = HistogramTile(self, name, concept=c.concept, study=c.study)
            tile.set_values(obs.dataframe[NUMERIC_VALUE])

        elif STRING_VALUE in obs.dataframe.columns:
            tile = PieTile(self, name, concept=c.concept, study=c.study)
            tile.set_values(obs.dataframe[STRING_VALUE])

        else:
            return

        self.register(tile)

    @debug_view.capture()
    def link_plotter(self, t1, t2):
        """
        Combine two tiles and add a new plot to the dashboard.
        """
        if isinstance(t1, HistogramTile) and isinstance(t2, HistogramTile):
            tile = ScatterPlot(t1, t2, self)

        else:
            raise ValueError('Combination of tiles not supported.')

        self.register(tile)

    @property
    def linked_tile(self):
        return self.__linked_tile

    @linked_tile.setter
    @debug_view.capture()
    def linked_tile(self, tile):
        logger.info('Set tile link: {}'.format(tile))
        if isinstance(tile, (PieTile, HistogramTile)):
            for t in self.tiles:
                try:
                    t.link_btn.button_style = ''
                except AttributeError:
                    pass

            if self.linked_tile is not None:
                self.link_plotter(self.linked_tile, tile)
                self.__linked_tile = None

            else:
                self.__linked_tile = tile
                tile.link_btn.button_style = 'info'

        elif tile is None:
            self.__linked_tile = None

        else:
            raise ValueError('Expected Tile object.')

    def register(self, tile):
        self.tiles.append(tile)

        if isinstance(tile, CombinedPlot):
            box = self.combination_out
        else:
            box = self.out

        with box.hold_sync():
            box.children = list(box.children) + [tile.get_fig()]

        self.refresh()

    def remove(self, tile):
        tmp = list(self.out.children)
        tmp.remove(tile)
        with self.out.hold_sync():
            self.out.children = tmp

        self.refresh()

    def update(self, exclude=None):
        for tile in self.tiles:
            if tile is exclude:
                continue

            tile.get_updates()

        with self.counter.hold_sync():
            self.counter.max = self.hypercube.total_subjects
            self.counter.value = self.hypercube.total_subjects

            if self.hypercube.subject_mask is not None:
                self.counter.value = len(self.hypercube.subject_mask)

            self.counter.description = '{}/{}'.format(self.counter.value, self.counter.max)

    def refresh(self):
        for tile in self.tiles:
            tile.fig.animation_duration = 0
            tile.refresh()
            tile.fig.animation_duration = ANIMATION_TIME

    @property
    def debugger(self):
        return debug_view
