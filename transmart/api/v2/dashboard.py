"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging

import bqplot as plt
import ipywidgets as widgets

from .constraint_widgets import ConceptPicker
from .query_constraints import ObservationConstraint, Queryable
from .hypercube import Hypercube

logger = logging.getLogger(__name__)
debug_view = widgets.Output(layout={'border': '1px solid black'})

_NUMERIC_VALUE = 'numericValue'
_STRING_VALUE = 'stringValue'

ANIMATION_TIME = 400


class Tile:

    def __init__(self, dash, title, concept, study=None):
        self.dash = dash
        self.fake_out = widgets.Output()
        self.selected_subjects = None

        self.concept = concept
        self.study = study

        self.title = title
        self.fig = None
        self.comb = None

        self._build_tile()

    @debug_view.capture()
    def _build_tile(self):
        self.fig = self.create_fig()
        logger.info('Created figure.')
        buttons, btn1, btn2, destroy_btn = self.get_buttons()
        self.comb = widgets.HBox(
            [self.fig, buttons],
            layout={'margin': '0px -20px 0px -18px'}
        )
        destroy_btn.on_click(self.destroyer(self.comb))

        self.fig.layout.height = '350px'
        self.fig.layout.width = '350px'

        self.fig.animation_duration = ANIMATION_TIME
        self.fig.title_style = {'font-size': 'small',
                                'width': '335px',
                                'overflow-text': 'wrap'}
        self.fig.title = self.title

    def destroyer(self, fig_box):
        def remove_fig(btn):
            with self.fake_out:
                self.dash.tiles.remove(self)
                self.dash.remove(fig_box)
        return remove_fig

    def create_fig(self):
        raise NotImplementedError

    def set_values(self, values):
        raise NotImplementedError

    def _calc_selected_subjects(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError

    @property
    def value_type(self):
        raise NotImplementedError

    def get_updates(self):
        subset = self.dash.hypercube.query(concept=self.concept, study=self.study)
        values = subset[self.value_type]
        self.set_values(values)

    def get_buttons(self):
        btn_layout = {
            'width': '35px',
            'height': '35px'
        }

        btn1 = widgets.Button(icon='fa-check', layout=btn_layout)
        btn2 = widgets.Button(icon='fa-link', layout=btn_layout)
        btn3 = widgets.Button(icon='fa-window-close', layout=btn_layout)

        buttons = widgets.VBox([
            btn1, btn2, btn3
        ], layout={'margin': '60px 25px 0px -60px'})

        btn1.layout.width = btn1.layout.height = '35px'

        btn1.on_click(self._calc_selected_subjects)

        return buttons, btn1, btn2, btn3

    @debug_view.capture(clear_output=False)
    def get_fig(self):
        print('Sending figure to front-end.')
        return self.comb


class HistogramTile(Tile):
    value_type = _NUMERIC_VALUE

    @debug_view.capture(clear_output=False)
    def create_fig(self):
        print('Creating figure.')
        scale_x = plt.LinearScale()
        scale_y = plt.LinearScale()
        hist = plt.Hist(sample=[], scales={'sample': scale_x, 'count': scale_y})

        ax_x = plt.Axis(label='Value Bins', scale=scale_x)
        ax_y = plt.Axis(label='Count', scale=scale_y,
                        orientation='vertical', grid_lines='solid')

        selector = plt.interacts.BrushIntervalSelector(
            scale=scale_x, marks=[hist], color='SteelBlue')

        print('Returning figure.')
        return plt.Figure(axes=[ax_x, ax_y], marks=[hist], interaction=selector)

    @debug_view.capture(clear_output=False)
    def set_values(self, values):
        print('Updating values.')
        m = self.fig.marks[0]
        with self.fig.hold_sync():
            m.sample = values

    @debug_view.capture()
    def _calc_selected_subjects(self, *args):
        subset = self.dash.hypercube.query(concept=self.concept, study=self.study, no_filter=True)
        values = subset[self.value_type]

        if len(self.fig.interaction.selected):
            min_, max_ = self.fig.interaction.selected
            selected = values.index[values.between(min_, max_)]
            print(values, min_, max_)
            self.selected_subjects = set(self.dash.hypercube.data.loc[selected, 'patient.id'])

        else:
            self.selected_subjects = None

        print(self.selected_subjects)
        self.dash.hypercube.subject_mask = self.selected_subjects
        self.dash.update(exclude=self)

    def refresh(self):
        """ Seems to resolve problems  with the brush selector. """
        values = self.fig.marks[0].sample
        with self.fig.hold_sync():
            self.set_values([])
            self.set_values(values)


class PieTile(Tile):
    value_type = _STRING_VALUE

    @debug_view.capture(clear_output=False)
    def create_fig(self):
        print('Creating figure.')

        tooltip_widget = plt.Tooltip(fields=['size', 'label'])
        pie = plt.Pie(tooltip=tooltip_widget,
                      interactions={'click': 'select', 'hover': 'tooltip'})
        pie.radius = 100
        print('Returning figure.')
        pie.selected_style = {"opacity": "1", "stroke": "white", "stroke-width": "4"}
        pie.unselected_style = {"opacity": "0.2"}

        return plt.Figure(marks=[pie])

    @debug_view.capture(clear_output=False)
    def set_values(self, values):
        print('Updating values.')

        pie = self.fig.marks[0]
        counts = values.value_counts()

        with self.fig.hold_sync():
            pie.labels = pie.sizes = []
            pie.sizes = counts
            pie.labels = list(counts.index)

    def _calc_selected_subjects(self):
        pass

    def refresh(self):
        pass


class Dashboard:

    def __init__(self, api, patients: Queryable=None):
        self.api = api
        self.tiles = list()
        self.hypercube = Hypercube()

        if isinstance(patients, Queryable):
            self.subject_set_ids = api.create_patient_set(repr(patients), patients).get('id')
        else:
            self.subject_set_ids = None

        self.out = widgets.Box()
        self.out.layout.flex_flow = 'row wrap'

        self.cp = ConceptPicker(self.plotter, api)

    def get(self):
        return widgets.VBox([self.out, self.cp.get()])

    @debug_view.capture()
    def plotter(self, constraints):
        c = ObservationConstraint.from_tree_node(constraints)

        if self.subject_set_ids is not None:
            c.subject_set_id = self.subject_set_ids

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

    def refresh(self):
        with self.out.hold_sync():
            for tile in self.tiles:
                tile.fig.animation_duration = 0
                tile.refresh()
                tile.fig.animation_duration = ANIMATION_TIME

    @property
    def debugger(self):
        return debug_view
