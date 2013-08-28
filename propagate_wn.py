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
from random import shuffle
from collections import defaultdict
import operator

from my_wordnet_lmf import My_wordnet
from my_seeds import My_seeds

def get_training_test(list_of_seeds, num_folds):
	synsets_for_polarity = {}
	fic = open(list_of_seeds, 'r')
	for line in fic:
		synset_id, polarity, pos = line.strip().split('/')
		if polarity not in synsets_for_polarity:
			synsets_for_polarity[polarity] = []
		synsets_for_polarity[polarity].append((synset_id, pos))
	fic.close()
	
	# Randomizing
	for key in synsets_for_polarity.keys():
		shuffle(synsets_for_polarity[key])	 	
		
	
	for k in xrange(num_folds):
		train = []
		eval = []
		for polarity, items in synsets_for_polarity.items():
		  aux_train = [(polarity, synset_id, pos) for i, (synset_id, pos) in enumerate(items) if i % num_folds != k ]
		  aux_eval = [(polarity, synset_id, pos) for i, (synset_id, pos) in enumerate(items) if i % num_folds == k ]
		  train.extend(aux_train)
		  eval.extend(aux_eval)
		yield train, eval
		
		
	
	
	

class My_synset:
	def __init__(self, my_id):
		self.id = my_id
			
	def set_polarity(self, polarity, chain):
		self.polarity = polarity
		self.chain_relations = chain
		
	def compute_value(self, map_values):
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
		
	def resolve_synset(self, map_values):
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
			value = value * -1  # # Converted to positive
			
		# #Computing the chain
		final_chain = self.polarity
		for rel in self.chain_relations:
			final_chain += ' -> ' + rel
		
		return final_pol, final_chain, value

	
	def __repr__(self):
		return 'ID:' + self.id + ' Pos:' + str(self.pos) + ' POL:' + str(self.polarity) + ' RELS:' + str(self.chain_relations)
		
		

def load_relations(filename):
	my_rels = {}
	try:
		f = open(filename)
		for line in f:
			relation, value = line.strip().split(' ')
			my_rels[relation] = float(value)
		f.close()
	except Exception as e:
		print >> sys.stderr, 'Error opening or reading file', filename
		print >> sys.stderr, str(e)
		sys.exit(-1)
	return my_rels
	
def usage(cmd):
	print 'Script for creating a sentiment polarity lexicon'
	print 'Usage: ', cmd, ' parameters'
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
	print '\t\t', cmd, ' --wn=cornetto.lmf.xml --seed-list=file_seeds.txt --relations=my_rels.txt'

def propagate_list(my_wn, seed_list_file, relations_file, log_file, out_file, seed_sense, max_depth):
	logging.debug('Settings for this run')
	logging.debug('Seed list filename ' + str(seed_list_file))
	logging.debug('Relations file: ' + str(relations_file))
	logging.debug('Log filename: ' + str(log_file))
	logging.debug('Output filename: ' + str(out_file))
	logging.debug('Seed list is senses (not synsets): ' + str(seed_sense))
	logging.debug('Maximum depth in number of relations: ' + str(max_depth))
	
		
	my_seeds = My_seeds(seed_list_file)
	my_relations = load_relations(relations_file)
	
	
	value_for_direct = 5 + sum(my_relations.values())
	my_relations['direct'] = value_for_direct
	
	logging.debug('Max depth: ' + str(max_depth))
	
	temp_folder = tempfile.mkdtemp()
	logging.debug('Created tmp folder ' + temp_folder)

	
	
	# # STEP 1 Propagate seed polarity to synsets:
	for cnt, (synset, polarity, pos) in enumerate(my_seeds):
				
		if cnt % max(1, int(5 * my_seeds.length() / 100)) == 0 :
			logging.debug('Processed ' + str(cnt) + ' seeds of ' + str(my_seeds.length()))
		already_tagged = []
		already_visited = set()
		# # FIRST seed
		
		if seed_sense:  # Map the sense to synset:
			synset = my_wn.sense_to_synset(synset)
		
		new_syn = My_synset(synset)
		new_syn.set_polarity(polarity, ['direct#' + synset])

		already_tagged.append(new_syn)
		
		keep_looping = True
		while keep_looping:
			keep_looping = False
			for source_synset in already_tagged:
				if source_synset.id not in already_visited:
					already_visited.add(source_synset.id)
					for relation in my_relations.keys():  # #For each relation type:
						# # Get the synset related through this relation
						targets_synset = my_wn.get_relateds_synset(source_synset.id, relation)	
						for target_synset in targets_synset:
							new_chain_relation = source_synset.chain_relations[:]
							new_chain_relation.append(relation + '#' + target_synset)
							new_synset = My_synset(target_synset)
							new_synset.set_polarity(source_synset.polarity, new_chain_relation)
							already_tagged.append(new_synset)
							depth = len(new_chain_relation)
							if depth >= max_depth:
								already_visited.add(target_synset)  # # For not explore it later...
							else:
								keep_looping = True
		# # NEXT SEED
		
		for synset in already_tagged:
			filename = os.path.join(temp_folder, synset.id)
			f = open(filename, 'a')
			f.write(synset.polarity + '\t' + '\t'.join(synset.chain_relations) + '\n')
			f.close()
		del already_tagged
		del already_visited
			
	# # The final step is to resolve each synset with all the posible chains:
	log = None
	if log_file != None:
	  log = codecs.open(log_file, 'w', encoding='utf-8')
	
	final_solutions = {}
	logging.debug('Resolving synsets')

	total_synsets = len(glob.glob(os.path.join(temp_folder, '*')))
	for cnt, filename in enumerate(glob.glob(os.path.join(temp_folder, '*'))):
		
		# # Load all the info for the synset
		synset_id = filename[filename.rfind('/') + 1:]
		
		# # To avoid seed changing of polarity because of different paths
		seed_polarity = my_seeds.get_polarity(synset_id)
		if seed_polarity is not None:  # It's a seed!
			final_solutions[synset_id] = (seed_polarity, value_for_direct)
			continue
		
		f = open(filename)
		possible_chains = []
		for line in f:
			fields = line.strip().split()
			polarity = fields[0]
			relations = fields[1:]
			new_synset = My_synset(synset_id)
			new_synset.set_polarity(polarity, relations)
			possible_chains.append(new_synset)
		f.close()
			
				
		if cnt % max(int(10 * total_synsets / 100), 1) == 0 :
			logging.debug('Resolved ' + str(cnt) + ' synsets of ' + str(total_synsets))

		if log != None: print >> log, 'Resolving synset :', synset_id
		
		options_for_synset = []
		for my_synset in possible_chains:
			final_pol, final_chain, value = my_synset.resolve_synset(my_relations)
			options_for_synset.append((final_pol, final_chain, value))
		options_for_synset.sort(key=operator.itemgetter(2), reverse=True)
		
		if log != None:
			for fp, fc, fv in options_for_synset:
				print >> log, '	Pol:', fp
				print >> log, '	Val:', fv
				print >> log, '	Rel:', fc
				print >> log, '	' + '=' * 100
			
		best_value = options_for_synset[0][2]
		num_pos = num_neg = num_neu = 0
		for fp, fc, fv in options_for_synset:
			if fv == best_value:
				if fp == 'positive': num_pos += 1
				elif fp == 'negative': num_neg += 1
				elif fp == 'neutral': num_neu += 1
			else:
				break
		if log != None:
			print >> log, '	Num_pos:', num_pos
			print >> log, '	Num neg:', num_neg
			print >> log, '	Num neu:', num_neu
			final_pol = ''
		
		if num_neu > num_pos and num_neu > num_neg:
			final_pol = 'neutral'
		else:
			if num_pos > num_neg:	final_pol = 'positive'
			elif num_neg > num_pos: final_pol = 'negative'
			else: final_pol = 'neutral'
			
		if log != None:
			print >> log, '	Final_pol:', final_pol, best_value
			print >> log, '	' + '**' * 100
			print >> log, '	' + '**' * 100
			
		final_solutions[synset_id] = (final_pol, best_value)
				
	f = codecs.open(out_file, 'w', 'utf-8')

	
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

	
	for synset, pos, pol, value, lemmas in data:
		print >> f, synset + ';' + pos + ';' + pol + ';' + str(value / maxim) + ';' + lemmas + ';-1'
	f.close()
			
	logging.debug('Output in file ' + out_file)

	if log != None: log.close()
		
		
	if True:
		shutil.rmtree(temp_folder)
	logging.debug('Deleted temp folder ' + temp_folder)

	
def load_results(filename):
	# Format --> n_n-502975;N;neutral;0.15625;baklucht;-1
	fic = open(filename, 'r')
	system_out = {}
	for line in fic:
		synset_id, pos, polarity, score, words, freq = line.strip().split(';')
		system_out[synset_id] = polarity
	fic.close()
	return system_out
	
	
	
def resolve_polarity(list_polarities):
	count_for_pol = defaultdict(int)
	for pol in list_polarities:
		count_for_pol[pol]+=1
	vector_pols = sorted(count_for_pol.items(),key=operator.itemgetter(1),reverse=True)
	tied = sum(1 for p,c in vector_pols if c==vector_pols[0][1])
	if tied==1:
		return vector_pols[0][0]
	else:
		return 'neutral'
	
def map_gold_to_lemma(gold_standard_syn,my_wn):
	gold_standard_lem = []
	polarities_for_lemma = {}
	for polarity, synset, pos in gold_standard_syn:
		lemmas = my_wn.lemmas_for_synset.get(synset)
		if lemmas is not None:
			for lemma in lemmas:
				if (lemma,pos) not in polarities_for_lemma:
					polarities_for_lemma[(lemma,pos)] = [polarity]
				else:
					polarities_for_lemma[(lemma,pos)].append(polarity)
				
		##gold_standard_lem.append((polarity, synset, pos))
	for (lemma,pos),l in polarities_for_lemma.items():
		final_polarity = resolve_polarity(l)
		gold_standard_lem.append((final_polarity,lemma,pos))
	return gold_standard_lem


def map_system_to_lemma(system_out):
	system_out_lem = {}
	polarities_for_lemma = {}
	for synset, polarity in system_out.items():
		lemmas = my_wn.lemmas_for_synset.get(synset)
		if lemmas is not None:
			for lemma in lemmas:
				if lemma not in polarities_for_lemma:
					polarities_for_lemma[lemma] = [polarity]
				else:
					polarities_for_lemma[lemma].append(polarity)
		
	for lemma, l in polarities_for_lemma.items():
		final_polarity = resolve_polarity(l)
		system_out_lem[lemma] = final_polarity
	return system_out_lem
	
def evaluate(system_out, gold_standard):
	# # Load the gold
	results = {}
   	gold = {}
   	for polarity, synset, pos in gold_standard:
   		gold[synset] = polarity

	for synset_gold, polarity_gold in gold.items():
		if polarity_gold not in results:
			results[polarity_gold] = (0, 0, 0, 0)

		polarity_system = system_out.get(synset_gold)
		
		# #Uncomment next line to get all the outputs of the system
		# print synset_gold,polarity_gold,polarity_system

		total, ok, wrong, none = results[polarity_gold]
		if polarity_system is None:
			results[polarity_gold] = (total + 1, ok, wrong, none + 1)
		elif polarity_system == polarity_gold:  # # OK!!
			results[polarity_gold] = (total + 1, ok + 1, wrong, none)
		else:
			results[polarity_gold] = (total + 1, ok, wrong + 1, none)
	# End for
	
	# # Printing results
	total = sum(total for (total, _, _, _) in results.values())
	ok = sum(ok for (_, ok, _, _) in results.values())
	wr = sum(wr for (_, _, wr, _) in results.values())
	print_results(total, ok, wr)
		
	for polarity, (total, ok, wrong, none) in results.items():
		print '  ', polarity
		print_results(total, ok, wrong, '    ')
	print
	return results

def print_results(total, ok, wrong, sep=''):
	prec = ok * 100.0 / (ok + wrong)
	rec = ok * 100.0 / total
	f1 = 2 * prec * rec / (prec + rec)
	none = total - ok - wrong
	print sep + 'Total: %d\tOk:%d\tWrong:%d\tNone:%d' % (total, ok, wrong, none)
	print sep + 'Precision: %3.2f' % prec
	print sep + 'Recall   : %3.2f' % rec
	print sep + 'F1 score : %3.2f' % f1
	

def show_results(results):
	overall_results = {}
	for n, result_fold in enumerate(results):
		print '######## Evaluation of the fold', n, '#########'
		overall_total = sum(total for (total, _, _, _) in result_fold.values())
		overall_ok = sum(ok for (_, ok, _, _) in result_fold.values())
		overall_wr = sum(wr for (_, _, wr, _) in result_fold.values())
		print_results(overall_total, overall_ok, overall_wr)
		
		for polarity, (total, ok, wrong, none) in result_fold.items():
			print '  ', polarity
			print_results(total, ok, wrong, '    ')
			 
			if polarity not in overall_results:
				t, o, w, e = (0, 0, 0, 0)
			else:
				t, o, w, e = overall_results[polarity]
			
			overall_results[polarity] = (t + total, o + ok, w + wrong, none + e)
		print '#' * 25
		print
	
	print
	print '****** OVERALL EVALUATION **********'
	overall_total = sum(total for (total, ok, wr, none) in overall_results.values())
	overall_ok = sum(ok for (total, ok, wr, none) in overall_results.values())
	overall_wr = sum(wr for (total, ok, wr, none) in overall_results.values())
	print_results(overall_total, overall_ok, overall_wr)
	for polarity, (total, ok, wrong, none) in overall_results.items():
		print '  ', polarity
		print_results(total, ok, wrong, '    ')
	print '*' * 100
	
		
			
   
   
if __name__ == '__main__':
	logging.basicConfig(stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
	seed_list_file = None
	wn_file = None
	relations_file = None
	log_file = None
	out_file = None
	seed_sense = False
	max_depth = 5
	num_folds = None
	try:
		opts, args = getopt.getopt(sys.argv[1:], "h", ["seed-list=", "wn=", "relations=", "out=", "log=", "max-depth=", "seed-sense", "num-folds="])
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
			elif opt == '--num-folds':
				num_folds = int(arg)
	except getopt.GetoptError, e:
		print 'ERROR: ', str(e)
		print
		usage(sys.argv[0])
		sys.exit(-1)


		
	if wn_file == None:
		print >> sys.stderr, 'Wornet file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	if seed_list_file == None:
		print >> sys.stderr, 'Seed list required'
		usage(sys.argv[0])
		sys.exit(-1)

	if relations_file == None:
		print >> sys.stderr, 'Relations file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	if out_file == None and num_folds is None:
		print >> sys.stderr, 'Output file required'
		usage(sys.argv[0])
		sys.exit(-1)
		
	#Loading wordnet only once
	logging.debug('Wordnet: ' + str(wn_file))
	my_wn = My_wordnet(wn_file)
		
	if num_folds is not None:
		if out_file is not None:
			print >> sys.stderr, 'Output file given but will not be used as num-folds for evaluation is present.'

		print 'Doing FCV with ', num_folds, 'FCV'
		i = 0
		results = []
		for list_train, list_test in get_training_test(seed_list_file, num_folds):
			# Write the training to a temporal file that will be the
			input_seed_list_fic = tempfile.NamedTemporaryFile(delete=False)
			for polarity, synset, pos in list_train:  # # polarity, synset,pos
				input_seed_list_fic.write('%s/%s/%s\n' % (synset, polarity, pos))
			input_seed_list_fic.close()
			logging.debug('RUNNING FOLD ' + str(i))
			
			output_file = tempfile.NamedTemporaryFile(delete=False)
			output_file.close()
			
			propagate_list(my_wn, input_seed_list_fic.name, relations_file, log_file, output_file.name, seed_sense, max_depth)
			
			system_out = load_results(output_file.name)
			
			logging.debug('Output file:' + output_file.name)
			logging.debug('len out ' + str(len(system_out)))
			
			if True:  # Mapping synsets to lemmas for do lemma-based evaluation
				list_test = map_gold_to_lemma(list_test,my_wn)  # Mapping to lemma
				system_out = map_system_to_lemma(system_out)

			
			result_eval = evaluate(system_out, list_test)
			results.append(result_eval)
			os.remove(input_seed_list_fic.name)
			os.remove(output_file.name)
			
			# DO THE EVALUATION!!!
			i += 1
		# Show the results for each fold
		show_results(results)
		
		# # Begin with the evaluation
	else:	
		# # Calling to the propagator
		propagate_list(my_wn, seed_list_file, relations_file, log_file, out_file, seed_sense, max_depth)
	

				
