import logging
import sys
from lxml import etree as ET

class My_wordnet:
  def __init__(self,filename):
      
    self.filename = filename
    self.sense_to_synset_map = {}   ## ['sense'] --> 'synset'
    self.synset_rels = {}       ## ['(synset',pos)] --> {} ==> ['relation'] --> ['target_synset']
    self.pos_for_synset = {}
    self.pos_for_lemma = {}
    
    self.senses_for_lemma = {}  ## ['lemma'] --> set(s1, s2, s3) 
    
    self.possible_pos = set()  ## -->'n','v','a'
    self.lemmas_for_synset = {}
    
    self.load_data()
    
  def get_lemma_senses(self):
    for lemma, senses in self.senses_for_lemma.items():
      yield lemma, senses
      
  def get_lemma_synsets(self):
    for lemma, senses in self.senses_for_lemma.items():
      yield lemma, [self.sense_to_synset_map[sense] for sense in senses]
    

  def sense_to_synset(self,sense):
    return self.sense_to_synset_map.get(sense,'0')
    
  def load_data(self):
    logging.debug('Loading WordNet from '+self.filename)
    
    try:
      tree = ET.parse(self.filename)
    except Exception as e:
      logging.error('Error while parsing wodnet, is valid XML?')
      logging.error(str(e))
      sys.exit(-1)
      
    ## Loading relations
    num_synsets=num_relations=0
    reverse_rels = []
    for synset_ele in tree.findall('Lexicon/Synset'):
      synset_id = synset_ele.get('id')
      
      pos = synset_ele.get('partOfSpeech',None)
      if pos is None:
        if synset_id[-2]=='-':
          pos = synset_id[-1]
        else:
          pos = 'NotGiven'
      self.pos_for_synset[synset_id]=pos
       
      self.possible_pos.add(pos)
      self.synset_rels[synset_id] = {}
      num_synsets += 1
      
      for syn_rel in synset_ele.findall('SynsetRelations/SynsetRelation'):
        synset_target = syn_rel.get('target')
        relation = syn_rel.get('relType')
        if relation in self.synset_rels[synset_id]:
          self.synset_rels[synset_id][relation].append(synset_target)
        else:
          self.synset_rels[synset_id][relation]=[synset_target]
        
        ##Inverse relations
        #if relation=='HAS_HYPERONYM':
        #  if synset_target not in self.synset_rels:
        #    self.synset_rels[synset_target]={}
        #  self.synset_rels[synset_target]['HAS_HYPONYM'] = synset_id
        #elif relation=='HAS_HYPONYM':
        #  if synset_target not in self.synset_rels:
        #    self.synset_rels[synset_target]={}
        #  self.synset_rels[synset_target]['HAS_HYPERONYM'] = synset_id
          
        num_relations += 1
    logging.debug('Loaded '+str(num_relations)+' relations for '+str(num_synsets)+' synsets')
      
    ## Loading mappings from sense to synset
    for lexical_entry in tree.findall('Lexicon/LexicalEntry'):
      lemma_obj = lexical_entry.findall('Lemma')[0]
      lemma = lemma_obj.get('writtenForm','')
      self.pos_for_lemma[lemma] = lemma_obj.get('partOfSpeech','NoGiven')
      self.senses_for_lemma[lemma] = set()
      
      for sense_ele in lexical_entry.findall('Sense'):        
        sense = sense_ele.get('id')
        synset = sense_ele.get('synset')
        if sense != None and synset != None:
          self.sense_to_synset_map[sense]= synset
          self.senses_for_lemma[lemma].add(sense)
          if synset not in self.lemmas_for_synset:
            self.lemmas_for_synset[synset]=[lemma]
          else:
            self.lemmas_for_synset[synset].append(lemma)
            

    logging.debug('Loaded senses for '+str(len(self.senses_for_lemma))+' different words')
    logging.debug('Loaded '+str(len(self.sense_to_synset_map))+' mappings sense --> synset')
        

  def get_pos_for_synset(self,id):
    return self.pos_for_synset.get(id,'Unknown_pos')

  def get_relateds_synset(self,id,relation):
    targets=[]
      
    if id in self.synset_rels:
      if relation in self.synset_rels[id]:
        targets = self.synset_rels[id][relation]
    return targets