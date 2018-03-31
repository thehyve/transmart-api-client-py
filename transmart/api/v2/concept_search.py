from whoosh.qparser import MultifieldParser, FuzzyTermPlugin
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT
import os


class ConceptSearcher:

    def __init__(self, tree_dict):
        self.ix = None
        self.parser = None
        self.__build_whoosh_index(tree_dict)

    def search(self, query_string, limit=50):
        with self.ix.searcher() as searcher:
            query = self.parser.parse(query_string)
            results = searcher.search(query, limit=limit)
            return [r['full_name'] for r in results]

    def __build_whoosh_index(self, tree_dict):

        schema_dir = '/tmp/whoosh/schemas'
        os.makedirs(schema_dir, exist_ok=True)

        schema = Schema(node=TEXT(stored=True),
                        full_name=TEXT(stored=True),
                        path=TEXT(stored=True),
                        type_=TEXT(stored=True),
                        study_id=TEXT(stored=True),
                        name=TEXT(stored=True),
                        metadata=TEXT(stored=True),
                        )
        self.ix = create_in(schema_dir, schema)
        writer = self.ix.writer()

        for key, value in tree_dict.items():
            writer.add_document(
                node=key.replace('\\', ' ').replace('_', ' '),
                path=value.get('conceptPath'),
                full_name=key,
                type_=value.get('type'),
                study_id=str(value.get('studyId')),
                name=str(value.get('name')),
                metadata=str(value.get('metadata'))
            )

        writer.commit()

        self.parser = MultifieldParser(
            ["node", "path", "type_", "study_id", "name", "metadata"],
            schema=self.ix.schema)
        self.parser.add_plugin(FuzzyTermPlugin())
