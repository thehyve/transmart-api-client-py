"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging

import bqplot as plt
import ipywidgets as widgets

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

    def _calc_selected_subjects(self, *args):
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
            'width': '25px',
            'height': '25px',
            'padding': '0px'
        }

        btn1 = widgets.Button(icon='fa-check', layout=btn_layout)
        btn2 = widgets.Button(icon='fa-link', layout=btn_layout)
        btn3 = widgets.Button(icon='fa-window-close', layout=btn_layout)

        buttons = widgets.VBox([
            btn1, btn2, btn3
        ], layout={'margin': '60px 25px 0px -60px'})

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

        logger.info('Returning figure.JOCHEMJOCHEM')
        return plt.Figure(axes=[ax_x, ax_y], marks=[hist], interaction=selector)

    @debug_view.capture(clear_output=False)
    def set_values(self, values):
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
            self.selected_subjects = set(self.dash.hypercube.data.loc[selected, 'patient.id'])

        else:
            self.selected_subjects = None

        self.dash.hypercube.subject_mask = self.selected_subjects
        self.dash.update(exclude=self)

    @debug_view.capture()
    def refresh(self, *args):
        """ Seems to resolve problems with the brush selector. """
        values = self.fig.marks[0].sample

        with self.fig.hold_sync():
            self.set_values([])  # TODO better way to make brush selector reliable.
            self.set_values(values)

        self.fig.interaction.reset()
        self.fig.interaction.selected = []
        print('Selected: ', self.fig.interaction.selected)


class PieTile(Tile):
    value_type = _STRING_VALUE

    @debug_view.capture(clear_output=False)
    def create_fig(self, *args):
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
        pie = self.fig.marks[0]
        counts = values.value_counts()

        with self.fig.hold_sync():
            pie.labels = pie.sizes = []
            pie.sizes = counts
            pie.labels = list(counts.index)

    @debug_view.capture()
    def _calc_selected_subjects(self, *args):
        subset = self.dash.hypercube.query(concept=self.concept, study=self.study, no_filter=True)
        values = subset[self.value_type]

        pie = self.fig.marks[0]
        if pie.selected is not None:
            labels = {pie.labels[i] for i in pie.selected}
            print(labels)
            selected = values.index[values.isin(labels)]
            print(selected)
            self.selected_subjects = set(self.dash.hypercube.data.loc[selected, 'patient.id'])

        else:
            self.selected_subjects = None

        self.dash.hypercube.subject_mask = self.selected_subjects
        self.dash.update(exclude=self)

    def refresh(self):
        self.fig.marks[0].selected = None

