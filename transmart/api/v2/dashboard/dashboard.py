"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging

import ipywidgets as widgets

from ...commons import filter_tree
from ..constraint_widgets import ConceptPicker
from ..query_constraints import ObservationConstraint, Queryable
from .hypercube import Hypercube
from .tiles import HistogramTile, PieTile

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

debug_view = widgets.Output(layout={'border': '1px solid black'})

_NUMERIC_VALUE = 'numericValue'
_STRING_VALUE = 'stringValue'

ANIMATION_TIME = 400


class Dashboard:

    def __init__(self, api, patients: Queryable=None):
        self.api = api
        self.tiles = list()
        self.hypercube = Hypercube()

        if isinstance(patients, Queryable):
            self.subject_set_id = api.create_patient_set(repr(patients), patients).get('id')
            counts = api.get_observations.counts_per_study_and_concept(
                subject_set_id=self.subject_set_id
            )
            self.nodes = filter_tree(api.tree_dict, counts)

        else:
            self.subject_set_id = None
            self.nodes = None

        self.out = widgets.Box()
        self.out.layout.flex_flow = 'row wrap'

        self.cp = ConceptPicker(self.plotter, api, self.nodes)
        self.counter = widgets.IntProgress(
            value=10, min=0, max=10, step=1,
            orientation='horizontal'
        )

    def get(self):
        return widgets.VBox([self.out, self.counter, self.cp.get()])

    @debug_view.capture()
    def plotter(self, constraints):
        c = ObservationConstraint.from_tree_node(constraints)

        if self.subject_set_id is not None:
            c.subject_set_id = self.subject_set_id

        obs = self.api.get_observations(c)
        self.hypercube.add_variable(obs.dataframe)

        name = obs.dataframe['concept.name'][0]

        if _NUMERIC_VALUE in obs.dataframe.columns:
            tile = HistogramTile(self, name, concept=c.concept, study=c.study)
            tile.set_values(obs.dataframe[_NUMERIC_VALUE])

        elif _STRING_VALUE in obs.dataframe.columns:
            tile = PieTile(self, name, concept=c.concept, study=c.study)
            tile.set_values(obs.dataframe[_STRING_VALUE])

        else:
            return

        self.register(tile)

    def register(self, tile):
        self.tiles.append(tile)
        with self.out.hold_sync():
            self.out.children = list(self.out.children) + [tile.get_fig()]

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
