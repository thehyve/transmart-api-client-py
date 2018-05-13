"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import logging

import abc
import bqplot as plt
import ipywidgets as widgets
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

debug_view = widgets.Output(layout={'border': '1px solid black'})


class CombinedPlot(abc.ABC):

    def __init__(self, t1, t2, dash):
        self.t1 = t1
        self.t2 = t2
        self.dash = dash
        self.df = None
        self.mark = None
        self.fig = None

        self.create_fig()
        self.get_updates()

    def get_fig(self):
        return self.fig

    @abc.abstractmethod
    def create_fig(self):
        pass

    @abc.abstractmethod
    def get_updates(self):
        pass

    def refresh(self):
        pass


class ScatterPlot(CombinedPlot):

    @staticmethod
    def get_values(tile):
        df = tile.dash.hypercube.query(study=tile.study, concept=tile.concept)
        non_empty = pd.notnull(df.numericValue)
        df = df.loc[non_empty, ['patient.id', 'numericValue']]
        return df

    def get_updates(self):
        mask = self.dash.hypercube.subject_mask

        if mask is not None:
            filter_ = self.df['patient.id'].isin(mask)
        else:
            filter_ = self.df.index

        with self.fig.hold_sync():
            self.mark.x = self.df.loc[filter_, 'numericValue_x']
            self.mark.y = self.df.loc[filter_, 'numericValue_y']

    def create_fig(self):
        t1_values = self.get_values(self.t1)
        t2_values = self.get_values(self.t2)
        self.df = t1_values.merge(t2_values, how='inner', on='patient.id')

        sc_x = plt.LinearScale()
        sc_y = plt.LinearScale()

        self.mark = plt.Scatter(scales={'x': sc_x, 'y': sc_y}, default_size=16)

        ax_x = plt.Axis(scale=sc_x, label=self.t1.title)
        ax_y = plt.Axis(scale=sc_y, label=self.t2.title, orientation='vertical')
        self.fig = plt.Figure(marks=[self.mark], axes=[ax_x, ax_y])

