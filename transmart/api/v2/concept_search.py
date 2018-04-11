import os
from whoosh.fields import Schema, TEXT, NGRAM
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin


class ConceptSearcher:

    def __init__(self, tree_dict, tree_identity):
        self.ix = None
        self.parser = None
        self.id_ = tree_identity
        self._tree_dict = tree_dict
        self.get_schema()

    def search(self, query_string, limit=50):
        with self.ix.searcher() as searcher:
            query = self.parser.parse(query_string)
            results = searcher.search(query, limit=limit,)
            return [r['full_name'] for r in results]

    def get_schema(self):
        user = os.path.expanduser('~')
        schema_dir = os.path.join(user, '.transmart-api-cache', 'schemas', self.id_)
        os.makedirs(schema_dir, exist_ok=True)

        if exists_in(schema_dir):
            self.ix = open_dir(schema_dir)
            print('Existing index cache found. Loaded {} tree nodes. Hooray!'.
                  format(self.ix.doc_count()))

        else:
            print('No valid cache found. Building indexes...')
            self.__build_whoosh_index(schema_dir)

        self.parser = MultifieldParser(
            self.ix.schema.names(),
            schema=self.ix.schema)
        self.parser.add_plugin(FuzzyTermPlugin())

    def __build_whoosh_index(self, schema_dir):

        fields = dict(
            node=TEXT(),
            full_name=TEXT(stored=True),
            path=TEXT(),
            type_=TEXT(),
            study_id=NGRAM(field_boost=10.0),
            name=NGRAM(field_boost=3.0),
            metadata=TEXT(),
        )
        schema = Schema(**fields)
        self.ix = create_in(schema_dir, schema)

        with self.ix.writer(procs=2, multisegment=True, limitmb=512) as writer:
            for key, value in self._tree_dict.items():
                writer.add_document(
                    node=key.replace('\\', ' ').replace('_', ' '),
                    path=value.get('conceptPath'),
                    full_name=key,
                    type_=value.get('type'),
                    study_id=str(value.get('studyId')),
                    name=str(value.get('name')),
                    metadata=str(value.get('metadata'))
                )
