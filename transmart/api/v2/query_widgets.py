import math

import ipywidgets as widgets
from IPython.display import HTML, display
from ipywidgets import VBox, HBox, Box
import arrow


AGG_NUM = 'numericalValueAggregates'
AGG_CAT = 'categoricalValueAggregates'


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

        self.list_of_default_options = sorted(self.api.tree_dict.keys())
        self.no_filter_len = len(self.list_of_default_options)

        self.result_count = widgets.HTML(
            value=self.result_count_template.format(self.no_filter_len)
        )
        self.result_text = widgets.HTML()

        self.search_bar = self._build_search_bar()
        self.concept_list = self._build_concept_list()

        self.concept_picker = VBox([
                HBox([self.search_bar, self.result_count]),
                self.concept_list,
                self.result_text])

    def _build_search_bar(self):
        def search_watcher(change):
            x = change.get('new')
            if len(x) > 2:
                self.concept_list.options = self.api.search_tree_node(x, limit=100)
                self.result_count.value = self.result_count_template.format(len(self.concept_list.options))

            else:
                self.concept_list.options = self.list_of_default_options
                self.result_count.value = self.result_count_template.format(self.no_filter_len)

        search_bar = widgets.Text(placeholder='Type something')
        search_bar.observe(search_watcher, 'value')
        return search_bar

    def _build_concept_list(self):
        def concept_list_watcher(change):
            x = change.get('new')
            if x:
                node = self.api.tree_dict.get(x)
                try:
                    self.target(node.get('constraint'))
                except ValueError:
                    pass

                d = {
                    'path': node.get('conceptPath'),
                    'type_': node.get('type'),
                    'study_id': node.get('studyId'),
                    'name': node.get('name'),
                    'metadata': node.get('metadata')
                }

                self.result_text.value = self.table_template.format(**d)

        concept_list = widgets.Select(
            options=self.list_of_default_options,
            rows=10,
            disabled=False,
            continous_update=False,
            layout={'width': '95%'}
        )

        concept_list.observe(concept_list_watcher, 'value')
        return concept_list

    def get(self):
        return self.concept_picker


class ConstraintWidget:

    html_style = """
        <style>
            .widget-readout {
                width: 210px;
            }
            .widget-readout .overflow {
                width: 210px;
            }
            .widget-hslider .slider-container{
                max-width: 35%;
            }
        </style>
        """

    def __init__(self, observation_constraint):
        self.constraint = observation_constraint
        self.numeric_range = self._build_numeric_range()
        self.categorical_select = self._build_list_selector('value_list', 'Values')
        self.trial_visit_select = self._build_list_selector('trial_visit', 'Visits')

        def update_date_attr(attr):
            def observer(change):
                try:
                    date = change.get('new').isoformat()
                except AttributeError:
                    date = None
                setattr(self.constraint, attr, date)
            return observer, 'value'

        self.start_date_since = widgets.DatePicker(
            description='Start date:')

        self.start_date_before = widgets.DatePicker(
            description='through',
            style={'description_width': '50px'})

        self.start_date_since.observe(*update_date_attr('min_start_date'))
        self.start_date_before.observe(*update_date_attr('max_start_date'))
        self.start_date_box = HBox([self.start_date_since, self.start_date_before])

        self.constraint_details = VBox([
            self.numeric_range,
            self.categorical_select,
            self.trial_visit_select,
            self.start_date_box
        ], layout={'height': '225px'})

        self.set_initial()

    def _build_numeric_range(self):
        def numeric_range_watcher(change):
            x = change.get('new')
            min_ = x[0] if not math.isclose(x[0], numeric_range.min) else None
            max_ = x[1] if not math.isclose(x[1], numeric_range.max) else None
            self.constraint.min_value = min_
            self.constraint.max_value = max_

        numeric_range = widgets.FloatRangeSlider(
            value=(5.5, 7.5),
            min=0.0,
            max=10.0,
            step=0.1,
            description='Value range:',
            orientation='horizontal',
            readout=True,
            readout_format='.2f',
            layout={'width': '95%'}
        )

        numeric_range.observe(numeric_range_watcher, 'value')
        return numeric_range

    def _build_list_selector(self, target, description):
        def watcher(change):
            x = list(change.get('new')) or None
            setattr(self.constraint, target, x)

        w = widgets.SelectMultiple(
            options=[],
            description=description)

        w.observe(watcher, 'value')
        return w

    def set_initial(self):
        widget_off(self.numeric_range)
        widget_off(self.categorical_select)
        # widget_off(self.start_date_box)

    def set_numerical(self):
        widget_off(self.categorical_select)
        widget_on(self.numeric_range)

    def set_categorical(self):
        widget_on(self.categorical_select)
        widget_off(self.numeric_range)

    def update_from_aggregates(self, aggregates):
        if aggregates.get(AGG_CAT):
            agg = aggregates.get(AGG_CAT)
            w = self.categorical_select

            w.value = tuple()
            w.options = {'{} ({})'.format(k, v): k for k, v in agg['valueCounts'].items()}
            w.rows = min(len(w.options) + 1, 5)
            self.set_categorical()

        elif aggregates.get(AGG_NUM):
            agg = aggregates.get(AGG_NUM)
            w = self.numeric_range
            min_, max_ = (agg.get('min'), agg.get('max'))

            w.max = float('Inf')
            w.min, w.max = (min_, max_)
            w.value = (min_, max_)
            self.set_numerical()

        else:
            self.set_initial()

    def update_trial_visits(self, visits):
        w = self.trial_visit_select
        options = []
        for tv in visits:
            label = tv.get('relTimeLabel')

            if tv.get('relTime') or tv.get('relTimeUnit'):
                label += ' ({} {})'.format(tv.get('relTime'), tv.get('relTimeUnit'))

            options.append(
                (label, tv.get('id'))
            )

        w.options = sorted(options)
        w.rows = min(len(options) + 1, 5)
        w.disabled = len(options) == 1

    def update_start_time(self, dates):
        dates = [arrow.get(d).date() for d in dates if not d.startswith('000')]
        w1 = self.start_date_since
        w2 = self.start_date_before
        w1.value = min(dates, default=None)
        w2.value = max(dates, default=None)
        w1.disabled = w2.disabled = len(dates) < 2

    def get(self):
        display(HTML(self.html_style))
        return self.constraint_details
