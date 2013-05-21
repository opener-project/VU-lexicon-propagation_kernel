#!/usr/bin/env python 

########################
# List of changes
# 12-Feb-2013 --> added code for generating opener-lmf format
# 21-May-2013
#   + Removed ooption for lemma based output
#   + Included option to check that seeds are not assigned finally with a wrong polarity
#   + Stored again the synset_id in the chain for debugging
########################

import logging
import sys
import codecs
import operator
import getopt
import os
import glob
import shutil
import tempfile

from my_wordnet_lmf import My_wordnet
from my_seeds import My_seeds

class My_synset:
	def __init__(self,my_id):
		self.id = my_id
			
	def set_polarity(self,polarity,chain):
		self.polarity = polarity
		self.chain_relations = chain
		
	def compute_value(self,map_values):
		p = 1
		for relation in self.chain_relations:
			value = map_values[relation]
			p = p * value
		self.value = p / len(self.chain_relations)
		
	def get_inverted_polarity(self):
		if self.polarity.lower() == 'positive':
			return 'negative'
		if self.polarity.lower() == 'negative':
			return 'positive'
		if self.polarity.lower() == 'neutral':
			return 'neutral'
		
	def resolve_synset(self,map_values):
		value = 1
		for relation_and_synset in self.chain_relations:
			relation = relation_and_synset[:relation_and_synset.find('#')]
			value = value * map_values[relation]
		value = value / len(self.chain_relations)
		
		if value == 0:
			final_pol = 'neutral'
		elif value > 0:
			final_pol = self.polarity
		else:
			final_pol = self.get_inverted_polarity()
			value = value * -1		## Converted to positive
			
		##Computing the chain
		final_chain = self.polarity
		for rel in self.chain_relations:
			final_chain += ' -> ' + rel
		
		return final_pol,final_chain,value

	
	def __repr__(self):
		return 'ID:'+self.id+' Pos:'+str(self.pos)+' POL:'+str(self.polarity)+' RELS:'+str(self.chain_relations)
		
		

def load_relations(filename):
	my_rels = {}
	try:
		f = open(filename)
		for line in f:
			relation, value = line.strip().split(' ')
			my_rels[relation] = float(value)
		f.close()
	except Exception as e:
		print>>sys.stderr,'Error opening or reading file',filename
		print>>sys.stderr,str(e)
		sys.exit(-1)
	return my_rels
	
def usage(cmd):
	print 'Script for creating a sentiment polarity lexicon'
	print 'Usage: ',cmd,' parameters'
	print 'Parameters:'
	print '\tRequired:'
	print '\t\t--wn=FILE file with wordnet in LMF format'
	print '\t\t--seed-list=FILE file with list of seeds with polarities'
	print '\t\t--relations=FILE file with relations and weights'
	print '\t\t--out=FILE file to store the results'
	print '\t\t--seed-sense In case your seed list is based on senses and not synsets'
	print '\tOptional:'
	print '\t\t--log=FILE Filename where store the log (default no log)'
	print '\t\t--max-depth=INT Maximum depth in number of relations to expand each synset (default 5) '
	print '\tExample:'
	print '\t\t',cmd,' --wn=cornetto.lmf.xml --seed-list=file_seeds.txt --relations=my_rels.txt'
	
if __name__ == '__main__':
	logging.basicConfig(stream=sys.stderr,format='%(asctime)s - %(levelname)s - %(message)s',level=logging.DEBUG)
	seed_list_file = None
	wn_file = None
	relations_file = None
	log_file = None
	out_file = None
	seed_sense = False
	max_depth = 5
	try:
		opts, args = getopt.getopt(sys.argv[1:],"h",["seed-list=","wn=","relations=","out=","log=","max-depth=","seed-sense"])
		for opt, arg in opts:
			if opt == "--seed-list":
				seed_list_file = arg
			elif opt == '--wn':
				wn_file = arg
			elif opt == '--relations':
				relations_file = arg
			elif opt == '--log':
				log_file = arg
			elif opt == '--out':
				out_file = arg
			elif opt == '--seed-sense':
				seed_sense = True
			elif opt == '--max-depth':
				max_depth = int(arg)
			elif opt == '-h':
				usage(sys.argv[0])
				sys.exit(0)
	except getopt.GetoptError, e:
		print 'ERROR: ',str(e)
		print
		usage(sys.argv[0])
		sys.exit(-1)


		
	if wn_file == None:
		print>>sys.stderr,'Wornet file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	if seed_list_file == None:
		print>>sys.stderr,'Seed list required'
		usage(sys.argv[0])
		sys.exit(-1)

	if relations_file == None:
		print>>sys.stderr,'Relations file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	if out_file == None:
		print>>sys.stderr,'Output file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	logging.debug('Settings for this run')
	logging.debug('Seed list filename '+str(seed_list_file))
	logging.debug('Wordnet: '+str(wn_file))
	logging.debug('Relations file: '+str(relations_file))
	logging.debug('Log filename: '+str(log_file))
	logging.debug('Output filename: '+str(out_file))
	logging.debug('Seed list is senses (not synsets): '+str(seed_sense))
	logging.debug('Maximum depth in number of relations: '+str(max_depth))
	
	my_wn = My_wordnet(wn_file)
	my_seeds = My_seeds(seed_list_file)
	my_relations = load_relations(relations_file)
	
	
	value_for_direct = 5 + sum(my_relations.values())
	my_relations['direct'] = value_for_direct
	
	logging.debug('Max depth: '+str(max_depth))
	
	temp_folder = tempfile.mkdtemp()
	logging.debug('Created tmp folder '+temp_folder)

	
	
	## STEP 1 Propagate seed polarity to synsets:
	for cnt, (synset, polarity, pos) in enumerate(my_seeds):
				
		if cnt % max(1,int(5 * my_seeds.length() / 100)) == 0 :
			logging.debug('Processed '+str(cnt)+' seeds of '+str(my_seeds.length()))
		already_tagged = []
		already_visited = set()
		## FIRST seed
		
		if seed_sense: # Map the sense to synset:
			synset = my_wn.sense_to_synset(synset)
		
		new_syn = My_synset(synset)
		new_syn.set_polarity(polarity,['direct#'+synset])

		already_tagged.append(new_syn)
		
		keep_looping = True
		while keep_looping:
			keep_looping = False
			for source_synset in already_tagged:
				if source_synset.id not in already_visited:
					already_visited.add(source_synset.id)
					for relation in my_relations.keys():	##For each relation type:
						## Get the synset related through this relation
						targets_synset = my_wn.get_relateds_synset(source_synset.id,relation)	
						for target_synset in targets_synset:
							new_chain_relation = source_synset.chain_relations[:]
							new_chain_relation.append(relation+'#'+target_synset)
							new_synset = My_synset(target_synset)
							new_synset.set_polarity(source_synset.polarity,new_chain_relation)
							already_tagged.append(new_synset)
							depth = len(new_chain_relation)
							if depth >= max_depth:
								already_visited.add(target_synset)	## For not explore it later...
							else:
								keep_looping = True
		## NEXT SEED
		
		for synset in already_tagged:
			filename = os.path.join(temp_folder,synset.id)
			f = open(filename,'a')
			f.write(synset.polarity+'\t'+'\t'.join(synset.chain_relations)+'\n')
			f.close()
		del already_tagged
		del already_visited
			
	## The final step is to resolve each synset with all the posible chains:
	log = None
	if log_file!=None:
	  log = codecs.open(log_file,'w',encoding='utf-8')
	
	final_solutions = {}
	logging.debug('Resolving synsets')

	total_synsets = len(glob.glob(os.path.join(temp_folder,'*')))
	for cnt, filename in enumerate(glob.glob(os.path.join(temp_folder,'*'))):
		
		## Load all the info for the synset
		synset_id = filename[filename.rfind('/')+1:]
		
		## To avoid seed changing of polarity because of different paths
		seed_polarity = my_seeds.get_polarity(synset_id)
		if seed_polarity is not None:	#It's a seed!
			final_solutions[synset_id]=(seed_polarity,value_for_direct)
			continue
		
		f = open(filename)
		possible_chains = []
		for line in f:
			fields = line.strip().split()
			polarity = fields[0]
			relations = fields[1:]
			new_synset = My_synset(synset_id)
			new_synset.set_polarity(polarity,relations)
			possible_chains.append(new_synset)
		f.close()
			
				
		if cnt % max(int(10 * total_synsets / 100),1) == 0 :
			logging.debug('Resolved '+str(cnt)+' synsets of '+str(total_synsets))

		if log!=None: print>>log,'Resolving synset :',synset_id
		
		options_for_synset = []
		for my_synset in possible_chains:
			final_pol,final_chain,value = my_synset.resolve_synset(my_relations)
			options_for_synset.append((final_pol,final_chain,value))
		options_for_synset.sort(key=operator.itemgetter(2),reverse=True)
		
		if log!=None:
			for fp, fc, fv in options_for_synset:
				print>>log,'	Pol:',fp
				print>>log,'	Val:',fv
				print>>log,'	Rel:',fc
				print>>log,'	'+'='*100
			
		best_value = options_for_synset[0][2]
		num_pos = num_neg = num_neu = 0
		for fp,fc,fv in options_for_synset:
			if fv == best_value:
				if fp =='positive': num_pos+=1
				elif fp=='negative': num_neg+=1
				elif fp=='neutral': num_neu+=1
			else:
				break
		if log!=None:
			print>>log, '	Num_pos:',num_pos
			print>>log, '	Num neg:',num_neg
			print>>log, '	Num neu:',num_neu
			final_pol=''
		
		if num_neu > num_pos and num_neu > num_neg:
			final_pol = 'neutral'
		else:
			if num_pos > num_neg:	final_pol = 'positive'
			elif num_neg > num_pos: final_pol = 'negative'
			else: final_pol = 'neutral'
			
		if log!=None:
			print>>log,'	Final_pol:',final_pol, best_value
			print>>log,'	'+'**'*100
			print>>log,'	'+'**'*100
			
		final_solutions[synset_id]=(final_pol,best_value)
				
	f = codecs.open(out_file,'w','utf-8')

	
	data = []
	maxim = -1
	n = 0
	
	# Generating the output at synset level
	for synset, (polarity, value) in final_solutions.items():
		pos = my_wn.get_pos_for_synset(synset)
		lemmas_for_synset = my_wn.lemmas_for_synset.get(synset, [])					
		if value >= maxim:
			maxim = value
		data.append((synset, pos, polarity, value, ','.join(lemmas_for_synset)))

	
	for synset,pos,pol,value,lemmas in data:
		print>>f,synset+';'+pos+';'+pol+';'+str(value/maxim)+';'+lemmas+';-1'
	f.close()
			
	logging.debug('Output in file '+out_file)

	if log!=None: log.close()
		
		
	if True:
		shutil.rmtree(temp_folder)
	logging.debug('Deleted temp folder '+temp_folder)
				
