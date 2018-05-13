import time

import os
import shutil
from whoosh.fields import Schema, TEXT, NGRAM, NGRAMWORDS
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin

user = os.path.expanduser('~')
cache_dir = os.path.join(user, '.transmart-api-cache', 'schemas')


def clear_cache():
    print('Removing cached indexes at: {!r}'.format(cache_dir))
    shutil.rmtree(cache_dir)


class ConceptSearcher:

    def __init__(self, tree_dict, tree_identity):
        self.ix = None
        self.parser = None
        self.id_ = tree_identity
        self._tree_dict = tree_dict
        self.get_schema()

    def search(self, query_string, limit=50, allowed_nodes: set=None):
        with self.ix.searcher() as searcher:
            query = self.parser.parse(query_string)

            if allowed_nodes is not None:
                allowed_nodes = {
                    doc_num for doc, doc_num
                    in zip(searcher.documents(), searcher.document_numbers())
                    if doc.get('fullname') in allowed_nodes
                }

            results = searcher.search(query, limit=limit, filter=allowed_nodes)
            return [r['fullname'] for r in results]

    def get_schema(self):
        schema_dir = os.path.join(cache_dir, self.id_)
        os.makedirs(schema_dir, exist_ok=True)

        if exists_in(schema_dir) and open_dir(schema_dir).doc_count() != 0:
            self.ix = open_dir(schema_dir)
            print('Existing index cache found. Loaded {} tree nodes. Hooray!'.
                  format(self.ix.doc_count()))

        else:
            print('No valid cache found. Building indexes...')
            now = time.time()
            self.__build_whoosh_index(schema_dir)
            print('Finished in {:.2f} seconds'.format(time.time() - now))

        self.parser = MultifieldParser(
            self.ix.schema.names(),
            schema=self.ix.schema)
        self.parser.add_plugin(FuzzyTermPlugin())

    def __build_whoosh_index(self, schema_dir):

        fields = dict(
            node=TEXT(),
            fullname=TEXT(stored=True),
            path=TEXT(),
            type=NGRAM(minsize=4),
            study=NGRAM(field_boost=10.0),
            name=NGRAMWORDS(minsize=3, field_boost=3.0),
            metadata=NGRAMWORDS(minsize=3),
        )
        schema = Schema(**fields)
        self.ix = create_in(schema_dir, schema)

        with self.ix.writer(procs=2, multisegment=True, limitmb=512) as writer:
            for key, value in self._tree_dict.items():
                writer.add_document(
                    node=key.replace('\\', ' ').replace('_', ' '),
                    path=value.get('conceptPath'),
                    fullname=key,
                    type=value.get('type'),
                    study=str(value.get('studyId')),
                    name=str(value.get('name')),
                    metadata=str(value.get('metadata'))
                )
