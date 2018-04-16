import math
from datetime import datetime

import arrow
import ipywidgets as widgets
from IPython.display import HTML, display
from ipywidgets import VBox, HBox

AGG_NUM = 'numericalValueAggregates'
AGG_CAT = 'categoricalValueAggregates'

MAX_OPTIONS = 100
CONCEPT_DELAY = 2
DEFAULT_VISIT = [{'relTimeLabel': 'General', 'id': 0}]


def widget_on(widget):
    widget.disabled = False
    widget.layout.visibility = 'initial'
    widget.layout.max_height = None


def widget_off(widget):
    widget.layout.visibility = 'hidden'
    widget.layout.max_height = '0'


def toggle_visibility(widget):
    if widget.layout.max_height == '0':
        widget_on(widget)
    else:
        widget_off(widget)


def create_toggle(widget, out):
    def toggle(btn):
        btn.description = 'Show' if btn.description == 'Hide' else 'Hide'
        with out:
            toggle_visibility(widget)

    toggle_btn = widgets.Button(description='Hide')
    toggle_btn.on_click(toggle)
    return toggle_btn


class ConceptPicker:

    result_count_template = 'Number of entries: {}'
    table_template = """
    <div class="rendered_html jp-RenderedHTMLCommon" style="width: 95%;">

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
            value=self.result_count_template.format(self.no_filter_len),
            layout={'width': '175px'}
        )
        self.result_text = widgets.HTML()

        self.search_bar = self._build_search_bar()
        self.concept_list = self._build_concept_list()

        # Necessary output for Jlab
        out = widgets.Output()

        def confirm_tree_node(btn):
            with out:
                try:
                    node = self.api.tree_dict.get(self.concept_list.value)
                    self.target(node.get('constraint'))
                except ValueError:
                    pass

        self._confirm = widgets.Button(description='Confirm', icon='check')
        self._confirm.on_click(confirm_tree_node)

        self.box_and_picker = VBox([
            HBox([self.search_bar, self.result_count, self._confirm]),
            self.concept_list,
            self.result_text])

        self.concept_picker = VBox([create_toggle(self.box_and_picker, out), self.box_and_picker])

    def _build_search_bar(self):
        def search_watcher(change):
            x = change.get('new')
            if len(x) > 2:
                self.concept_list.options = self.api.search_tree_node(x, limit=MAX_OPTIONS)
                count = len(self.concept_list.options)

                if count == MAX_OPTIONS:
                    count = str(count) + '+'

                self.result_count.value = self.result_count_template.format(count)

            else:
                self.concept_list.options = self.list_of_default_options[:MAX_OPTIONS]
                self.result_count.value = self.result_count_template.format(self.no_filter_len)

        search_bar = widgets.Text(placeholder='Type something')
        search_bar.observe(search_watcher, 'value')
        return search_bar

    def _build_concept_list(self):
        def concept_list_watcher(change):
            x = change.get('new')
            if x:
                node = self.api.tree_dict.get(x)
                metadata = dict(node.get('metadata', {}))
                d = {
                    'path': node.get('conceptPath'),
                    'type_': node.get('type'),
                    'study_id': node.get('studyId'),
                    'name': node.get('name'),
                    'metadata': '<br> '.join(['{}: {}'.format(k, v) for k, v in metadata.items()])
                }

                self.result_text.value = self.table_template.format(**d)

        concept_list = widgets.Select(
            options=self.list_of_default_options[:MAX_OPTIONS],
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
        self.categorical_select.layout.width = '450px'
        self.trial_visit_select = self._build_list_selector('trial_visit', 'Visits')

        def update_date_attr(attr, *args):
            def observer(change):
                try:
                    date = change.get('new')
                    for func in args:
                        date = func(date)

                except AttributeError:
                    date = None

                setattr(self.constraint, attr, date)
            return observer, 'value'

        self.date_value_min = widgets.DatePicker(
            description='After:')

        self.date_value_max = widgets.DatePicker(
            description='before:',
            style={'description_width': '50px'})

        self.date_value_min.observe(*update_date_attr('min_date_value', lambda x: str(x)))
        self.date_value_max.observe(*update_date_attr('max_date_value', lambda x: str(x)))

        self.date_value_box = HBox([self.date_value_min, self.date_value_max])

        self.start_date_since = widgets.DatePicker(
            disabled=True,
            description='Start date:')

        self.start_date_before = widgets.DatePicker(
            description='through',
            disabled=True,
            style={'description_width': '50px'})

        self.start_date_since.observe(*update_date_attr('min_start_date', lambda x: x.isoformat()))
        self.start_date_before.observe(*update_date_attr('max_start_date', lambda x: x.isoformat()))
        self.start_date_box = HBox([self.start_date_since, self.start_date_before])

        self.detail_fields = VBox([
            self.numeric_range,
            self.categorical_select,
            self.date_value_box,
            self.trial_visit_select,
            self.start_date_box
        ])

        # Necessary output for Jlab
        self.out = widgets.Output()

        self.obs_repr = widgets.HTML()

        self.constraint_details = VBox([
            HBox([
                create_toggle(self.detail_fields, self.out),
                self.obs_repr,
                self.out]),
            self.detail_fields])

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

    def disable_all(self):
        for child in self.detail_fields.children:
            child.disabled = True

    def set_initial(self):
        widget_off(self.numeric_range)
        widget_off(self.categorical_select)
        widget_off(self.date_value_min)
        widget_off(self.date_value_max)
        self.update_trial_visits(DEFAULT_VISIT)

    def set_numerical(self):
        self.set_initial()
        widget_on(self.numeric_range)

    def set_categorical(self):
        self.set_initial()
        widget_on(self.categorical_select)

    def set_date(self):
        self.set_initial()
        widget_on(self.date_value_min)
        widget_on(self.date_value_max)

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
            min_, max_ = (agg.get('min'), agg.get('max'))

            # We have to guess whether we are dealing with dates or normal values
            # as the mechanism is entirely the same for both. Although we want
            # to show a different widget.
            is_date = max_ >= 1e12  # latest date after 2001-09-09

            if not is_date:
                w = self.numeric_range

                w.max = float('Inf')
                w.min, w.max = (min_, max_)
                w.value = (min_, max_)
                self.set_numerical()

            else:
                self.date_value_min.value = datetime.utcfromtimestamp(min_ // 1000).date()
                self.date_value_max.value = datetime.utcfromtimestamp(max_ // 1000).date()
                self.set_date()
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
        w1.disabled = w2.disabled = len(dates) < 2

        w1.value = min(dates, default=None)
        w2.value = max(dates, default=None)

    def update_obs_repr(self):
        self.obs_repr.value = '<div style="font-family:monospace;font-size:smaller;">{}</div>'.\
            format(repr(self.constraint))

    def get(self):
        with self.out:
            display(HTML(self.html_style))
        return self.constraint_details
