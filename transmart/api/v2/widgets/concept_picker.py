"""
* Copyright (c) 2015-2017 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
"""

import ipywidgets

from .shared import create_toggle

AGG_NUM = 'numericalValueAggregates'
AGG_CAT = 'categoricalValueAggregates'

MAX_OPTIONS = 100


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

    def __init__(self, target, api, allowed_nodes: set=None):

        self.target = target
        self.api = api
        self.allowed_nodes = allowed_nodes

        nodes = allowed_nodes or self.api.tree_dict.keys()

        self.list_of_default_options = sorted(nodes)
        self.no_filter_len = len(self.list_of_default_options)

        self.result_count = ipywidgets.HTML(
            value=self.result_count_template.format(self.no_filter_len),
            layout={'width': '175px'}
        )
        self.result_text = ipywidgets.HTML(layout={'width': '49%'})

        self.search_bar = self._build_search_bar()
        self.concept_list = self._build_concept_list()

        # Necessary output for Jlab
        out = ipywidgets.Output()

        def confirm_tree_node(btn):
            with out:
                try:
                    node = self.api.tree_dict.get(self.concept_list.value)
                    self.target(node.get('constraint'))
                except ValueError:
                    pass

        self._confirm = ipywidgets.Button(description='Confirm', icon='check')
        self._confirm.on_click(confirm_tree_node)

        self.box_and_picker = ipywidgets.VBox([
            ipywidgets.HBox([self.search_bar, self.result_count, self._confirm]),
            ipywidgets.HBox([self.concept_list, self.result_text])
        ])

        self.concept_picker = ipywidgets.VBox([create_toggle(self.box_and_picker, out), self.box_and_picker])

    def _build_search_bar(self):
        def search_watcher(change):
            x = change.get('new')
            if len(x) > 2:
                self.concept_list.options = self.api.search_tree_node(
                    x,
                    limit=MAX_OPTIONS,
                    allowed_nodes=self.allowed_nodes
                )
                count = len(self.concept_list.options)

                if count == MAX_OPTIONS:
                    count = str(count) + '+'

                self.result_count.value = self.result_count_template.format(count)

            else:
                self.concept_list.options = self.list_of_default_options[:MAX_OPTIONS]
                self.result_count.value = self.result_count_template.format(self.no_filter_len)

        search_bar = ipywidgets.Text(placeholder='Type something')
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

        concept_list = ipywidgets.Select(
            options=self.list_of_default_options[:MAX_OPTIONS],
            rows=10,
            disabled=False,
            continous_update=False,
            layout={'width': '50%'}
        )

        concept_list.observe(concept_list_watcher, 'value')
        return concept_list

    def get(self):
        return self.concept_picker
