'''
* Copyright (c) 2015 The Hyve B.V.
* This code is licensed under the GNU General Public License,
* version 3.
* Author: Ruslan Forostianov, Pieter Lukasse
'''

import re
import os.path
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import collections

class Entrez(object):
    
    def __init__(self):
        self._gene_name_id_mappings = None

    def get_gene_id(self, gene_symbol):
        gene_name_id_mappings = self.get_gene_name_id_mappings()
        if gene_symbol in gene_name_id_mappings:
            return gene_name_id_mappings[gene_symbol]
        else:
            return None
    
    def get_kegg_gene_ids(self, gene_symbols):
        return {gs: self.get_kegg_gene_id(gs) for gs in gene_symbols}
    
    def get_gene_name_id_mappings(self):
        if self._gene_name_id_mappings is None:        
            gene_id_mappings_file = "entrez_gene_id.tsv"
            self._gene_name_id_mappings = self._parse_gene_name_id_mappings_file(gene_id_mappings_file)
        return self._gene_name_id_mappings
    
    def _parse_gene_name_id_mappings_file(self, gene_id_mappings_file):
        file_rows = [line.strip().split('\t') for line in open(gene_id_mappings_file)]
        result = {}
        for file_row in file_rows:
            if len(file_row) < 2:
                continue
            gene = file_row[0]
            gid = file_row[1]
            result[gene] = gid
            
        return result
    
class Kegg(object):

    def __init__(self, gene_ids, species_abr = 'hsa'):
        unq_gene_ids = list(set(gene_ids))
        self._gene_pathways_ids = self._get_related_pathways_chunked(unq_gene_ids, species_abr)
        self._pathway_genes_ids = self._get_pathway_gene_ids(self._gene_pathways_ids)
    
    def get_pathways_image_links_by_gene(self, gene_id):
        if gene_id not in self._gene_pathways_ids:
            return []
        gene_pathways_ids = self._gene_pathways_ids[gene_id]
        result = []
        for pathway_id in gene_pathways_ids:
            result.append(self._gene_pathway_image_link(pathway_id, [gene_id]))
        return result
    
    def get_pathways_image_links_by_pathway(self, pathway_id):
        return self._gene_pathway_image_link(pathway_id, self._pathway_genes_ids[pathway_id])
    
    def get_all_pathways_rows(self):
        rows = []
        for pathway in self._pathway_genes_ids:
            rows.append((self.get_pathways_image_links_by_pathway(pathway), len(self._pathway_genes_ids[pathway])))
        return rows
    
    def _gene_pathway_image_link(self, pathway_id, gene_ids):
        return '<a target="_blank" href="http://www.kegg.jp/pathway/{0}+{1}">{0}</a>'.format(pathway_id, '+'.join(gene_ids))

    def _get_pathway_gene_ids(self, gene_pathways_ids):
        rev = collections.defaultdict(list)
        for gene in gene_pathways_ids:
            for pathway in self._gene_pathways_ids[gene]:
                rev[pathway].append(gene)
        return rev

    def chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i:i+n]

    def _get_related_pathways_chunked(self, gene_ids, species_abr):
        gene_ids_chunks = self.chunks(gene_ids, 100)
        result = {}
        for gene_ids_chunk in gene_ids_chunks:
            cr = self._get_related_pathways(gene_ids_chunk, species_abr)
            result.update(cr)
        return result

    def _get_related_pathways(self, gene_ids, species_abr):
        gsids = [species_abr + ':' + str(gene_id) for gene_id in gene_ids]
        url = 'http://rest.kegg.jp/link/pathway/%s' % '+'.join(gsids)
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req)
        gene_pathway_tsv = res.read()
        return self._parse_pathway_content(gene_pathway_tsv)
    
    def _parse_pathway_content(self, tsv):
        gene_pathway = [line.split('\t') for line in tsv.split('\n')]
        result = collections.defaultdict(list)
        for gp in gene_pathway:
            if len(gp) < 2 or gp[0] == '' or gp[1] == '':
                continue
            gene = gp[0].split(':')[1]
            pathway = gp[1].split(':')[1]
            result[gene].append(pathway)
        return result
    
class Uniprot(object):
    
    def _ensure_uniprot_file_is_present(self, uniprot_entrez_kegg_file):
        if not os.path.isfile(uniprot_entrez_kegg_file):
            url = 'http://www.uniprot.org/uniprot/?sort=score&desc=&compress=no&query=homo%20sapiens&fil=&force=no&format=tab&columns=id,genes,database(KEGG)'
            urllib.request.urlretrieve (url, uniprot_entrez_kegg_file)
        return uniprot_entrez_kegg_file
