import sys

import ipywidgets as widgets
from functools import wraps
from ipywidgets import VBox, HBox

AGG_NUM = 'numericalValueAggregates'
AGG_CAT = 'categoricalValueAggregates'


def yield_for_change(widget, attribute):
    """Pause a generator to wait for a widget change event.

    This is a decorator for a generator function which pauses the generator on yield
    until the given widget attribute changes. The new value of the attribute is
    sent to the generator and is the value of the yield.
    """
    def f(iterator):
        @wraps(iterator)
        def inner():
            i = iterator()

            def next_i(change):
                try:
                    i.send(change.new)
                except StopIteration as e:
                    widget.unobserve(next_i, attribute)
            widget.observe(next_i, attribute)
            # start the generator
            next(i)
        return inner
    return f


def widget_on(widget):
    widget.layout.visibility = 'initial'
    widget.layout.max_height = None


def widget_off(widget):
    widget.layout.visibility = 'hidden'
    widget.layout.max_height = '0'


class ConceptPicker:

    result_count_template = 'Number of entries: {}'
    table_template = """
    <div class="rendered_html" style="width: 95%;">

        <table border="1" class="dataframe" style="width: 100%;">
            <colgroup>
                <col style="width: 20%">
                <col style="width: 80%">
            </colgroup>

            <tr>
                <td>Name</td>
                <td><b>{name}</b></td>
            </tr>
            <tr>
                <td>Path</td>
                <td><small>{path}</small></td>
            </tr>
            <tr>
                <td>Type</td>
                <td>{type_}</td>
            </tr>
            <tr>
                <td>Study ID</td>
                <td>{study_id}</td>
            </tr>
            <tr>
                <td>Metadata</td>
                <td>{metadata}</td>
            </tr>
        </table>
    </div>
    """

    def __init__(self, target, api):

        self.target = target
        self.api = api

        list_of_default_options = sorted(self.api.tree_dict.keys())
        no_filter_len = len(list_of_default_options)

        self.search_bar = widgets.Text(
            placeholder='Type something',
            disabled=False
        )

        self.result_count = widgets.HTML(
            value=self.result_count_template.format(no_filter_len)
        )

        self.concept_list = widgets.Select(
            options=list_of_default_options,
            rows=10,
            disabled=False,
            layout={'width': '95%'}
        )

        self.result_text = widgets.HTML()

        @yield_for_change(self.concept_list, 'value')
        def concept_list_watcher():
            for _ in range(sys.maxsize ** 10):
                x = yield
                if x:
                    node = self.api.tree_dict.get(x)
                    self.target(node.get('conceptCode'))

                    d = {
                        'path': node.get('conceptPath'),
                        'type_': node.get('type'),
                        'study_id': node.get('studyId'),
                        'name': node.get('name'),
                        'metadata': node.get('metadata')
                    }

                    self.result_text.value = self.table_template.format(**d)

        @yield_for_change(self.search_bar, 'value')
        def search_watcher():
            for _ in range(sys.maxsize ** 10):
                x = yield
                if len(x) > 2:
                    self.concept_list.options = self.api.search_tree_node(x, limit=100)
                    self.result_count.value = self.result_count_template.format(len(self.concept_list.options))

                else:
                    self.concept_list.options = list_of_default_options
                    self.result_count.value = self.result_count_template.format(no_filter_len)

        concept_list_watcher()
        search_watcher()

        self.concept_picker = VBox([
                HBox([self.search_bar, self.result_count]),
                self.concept_list,
                self.result_text])

    def get(self):
        return self.concept_picker


class ConstraintWidget:

    def __init__(self, observation_constraint):
        self.constraint = observation_constraint

        self.numeric_range = widgets.FloatRangeSlider(
            value=(5.5, 7.5),
            min=0.0,
            max=10.0,
            step=0.1,
            description='Value range:',
            orientation='horizontal',
            # readout=True,
            readout_format='.2f',
        )

        @yield_for_change(self.numeric_range, 'value')
        def numeric_range_watcher():
            for i in range(sys.maxsize ** 10):
                x = yield
                if len(x) == 2:
                    self.constraint.min_value = x[0]
                    self.constraint.max_value = x[1]

        self.categorical_select = widgets.SelectMultiple(
            options=[],
            description='Values',
        )

        @yield_for_change(self.categorical_select, 'value')
        def categorical_select_watcher():
            for i in range(sys.maxsize ** 10):
                x = yield
                if len(x):
                    self.constraint.trial_visit = list(x)
                else:
                    self.constraint.trial_visit = None

        numeric_range_watcher()
        categorical_select_watcher()

        self.start_date_since = widgets.DatePicker(
            description='Start date:',
            disabled=False
        )

        self.start_date_before = widgets.DatePicker(
            description='through',
            disabled=False
        )

        self.constraint_details = VBox([
            self.numeric_range,
            self.categorical_select,
            HBox([self.start_date_since, self.start_date_before])
        ])

        self.set_initial()

    def set_initial(self):
        widget_off(self.numeric_range)
        widget_off(self.categorical_select)

    def set_numerical(self):
        widget_off(self.categorical_select)
        widget_on(self.numeric_range)

    def set_categorical(self):
        widget_on(self.categorical_select)
        widget_off(self.numeric_range)

    def update_from_aggregates(self, aggregates):
        if aggregates.get(AGG_CAT):
            agg = aggregates.get(AGG_CAT)
            self.categorical_select.value = tuple()
            self.categorical_select.options = {'{} ({})'.format(k, v): k for k, v in agg['valueCounts'].items()}
            self.set_categorical()

        elif aggregates.get(AGG_NUM):
            agg = aggregates.get(AGG_NUM)
            min_, max_ = (agg.get('min'), agg.get('max'))
            self.numeric_range.max = float('Inf')
            self.numeric_range.value = (self.numeric_range.min, self.numeric_range.max) = (min_, max_)
            self.set_numerical()

        else:
            self.set_initial()

    def get(self):
        return self.constraint_details
