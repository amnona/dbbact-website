from collections import defaultdict
import urllib
from flask import render_template

from utils import debug
from Site_Main_Flask import draw_cloud


def calculate_score(annotations, seqannotations, term_info):
	'''Get the enrichment score for each term in seqs compared to all of dbBact
	'''
	# calculate the per-term score
	term_scores = defaultdict(float)
	for cseqid, cannotation_ids in seqannotations:
		cannotations = [annotations[cid] for cid in cannotation_ids]
		cterm_scores = get_annotation_term_counts(cannotations)
		for cterm, cscore in cterm_scores.items():
			term_scores[cterm] += cscore

	# normalize by number of sequences total in database for each term
	for cterm in term_scores:
		term_scores[cterm] = term_scores[cterm] / term_info[cterm]['total_sequences']
	return term_scores


def get_annotation_term_counts(annotations, exp_annotations=None, score_method='all_mean'):
	'''Get the annotation type corrected count for all terms in annotations

	Parameters
	----------
	annotations : list of dict
		list of annotations where the feature is present
	dict of {expid:int : dict of {term:str : total:int}}
		from self._get_exp_annotations()
	score_method: str (optional)
			The method to use for score calculation:
			'all_mean' : score is the mean (per experiment) of the scoring for the term out of all annotations that have the term
			'sum' : score is sum of all annotations where the term appears (experiment is ignored)

	Returns
	-------
		dict of {term: score}
		note: lower in terms are "-"+term
	'''
	term_count = defaultdict(int)

	for cannotation in annotations:
		details = cannotation['details']
		annotation_type = cannotation['annotationtype']
		if annotation_type == 'common':
			cscore = 1
		elif annotation_type == 'highfreq':
			cscore = 1
		elif annotation_type == 'other':
			cscore = 0.5
		elif annotation_type == 'contamination':
			cscore = 1
			details = [('all','contamination')]
		elif annotation_type == 'other':
			cscore = 0
		elif annotation_type == 'diffexp':
			cscore = None
		else:
			debug(4, 'unknown annotation type %s encountered (annotationid %d). skipped' % (annotation_type, cannotation['annotationid']))
			continue
		for cdetail in details:
			ctype = cdetail[0]
			cterm = cdetail[1]
			if ctype == 'all':
				cscore = 1
			elif ctype == 'high':
				cscore = 2
			elif ctype == 'low':
				# if low - change the term to "-term" - i.e. lower in term
				cterm = '-' + cterm
				cscore = 1
			else:
				debug(4, 'unknown detail type %s encountered for annotation %d' % (ctype, cannotation['annotationid']))

			if score_method == 'all_mean':
				scale_factor = exp_annotations[cannotation['expid']][cterm]
				if scale_factor == 0:
					debug(4,'scale factor=0. term %s, exp %d, annotationid %d, score %d, scale %d' % (cterm, cannotation['expid'], cannotation['annotationid'], cscore, scale_factor))
					scale_factor = 1
			else:
				scale_factor = 1

			# fix for differential abundance
			term_count[cterm] += cscore / scale_factor
	return term_count


def draw_group_wordcloud(annotations, seqannotations, term_info):
	wpart = ''

	term_scores = calculate_score(annotations, seqannotations, term_info)
	debug(1, 'drawing group wordcloud')
	wordcloud_image = draw_cloud(term_scores, num_high_term=None, num_low_term=None, term_frac=None)

	wordcloudimage=urllib.parse.quote(wordcloud_image)
	if wordcloudimage:
		wpart += render_template('wordcloud.html', wordcloudimage=urllib.parse.quote(wordcloud_image))
	else:
		wpart += '<p></p>'
	return wpart


def draw_group_annotation_details(annotations, seqannotations, term_info, include_word_cloud=True):
	'''
	Create table entries for a list of annotations

	Parameters
	----------
	annotations : list of dict of annotation details (from REST API)
	term_info : dict of dict or None (optional)
		None (default) to skip relative word cloud.
		Otherwise need to have information about all ontology terms to be drawn
		dict of {term: dict} where
			term : ontology term (str)
			dict: pairs of:
				'total_annotations' : int
				'total_sequences' : int
	show_relative_freqs: bool (optional)
		False to draw absolute term abundance word cloud
		(i.e. term size based on how many times we see the term in the annotations)
		True to draw relative term abundance word cloud
		(i.e. term size based on how many times we see the term in the annotations divided by total times we see the term in the database)

	Returns
	-------
	wpart : str
		html code for the annotations table
	'''
	# The output webpage part
	wpart = ''

	# draw the wordcloud
	if include_word_cloud is True:
		wpart += draw_group_wordcloud(annotations, seqannotations, term_info)

	wpart += render_template('tabs.html')

	# # draw the annotation table
	# wpart += draw_annotation_table(annotations)

	# # wpart += '<div style="-webkit-column-count: 3; -moz-column-count: 3; column-count: 3;">\n'

	# # draw the ontology term list
	# wpart += draw_ontology_list(annotations, term_info)

	wpart += '    </div>\n'
	wpart += '  </div>\n'
	return wpart

def draw_wordcloud(annotations, term_info=None, show_relative_freqs=False):
	'''
	draw the wordcloud (image embedded in the html)

	Parameters
	----------
	annotations : annotation
		The list of annotations to process for annotation ontology terms
	term_info: dict or None
		a dict with the total annotations per ontology term or None to skip relative abundance word cloud
	show_relative_freqs: bool (optional)
		False to draw absolute term abundance word cloud
		(i.e. term size based on how many times we see the term in the annotations)
		True to draw relative term abundance word cloud
		(i.e. term size based on how many times we see the term in the annotations divided by total times we see the term in the database)

	Returns
	-------
	wpart : str
		an html webpage part with the wordcloud embedded
	'''
	wpart = ''

	# draw the wordcloud
	# termstr = ''
	# total frequencies of each term (not only leaves) in dbbact

	num_term = defaultdict(int)
	num_low_term = defaultdict(int)
	num_high_term = defaultdict(int)
	for cannotation in annotations:
		for cdetail in cannotation['details']:
			if cdetail[0] == 'all' or cdetail[0] == 'high':
				orig_term = cdetail[1]
				if 'website_sequences' in cannotation:
					# if it's high freq. it's worth more
					if cannotation['annotationtype'] == 'highfreq':
						factor = 2
					else:
						factor = 1
					num_to_add = factor * len(cannotation['website_sequences'])
					num_high_term[orig_term] += num_to_add
					num_term[orig_term] += num_to_add
			elif cdetail[0] == 'low':
				orig_term = cdetail[1]
				if 'website_sequences' in cannotation:
					num_low_term[orig_term] += len(cannotation['website_sequences'])
					num_term[orig_term] += len(cannotation['website_sequences'])

	# calculate the relative enrichment of each term (if term_info is supplied)
	term_frac = None
	if term_info is not None:
		debug(1, 'drawing relative frequencies wordcloud')
		# do the relative freq. word cloud
		term_frac = {}
		for cterm in num_term:
			if cterm not in term_info:
				debug(2, 'term %s not in term_info!' % cterm)
				continue
			# if we don't have enough statistics about the term, ignore it
			# so we need at least 4 annotations with this term.
			# Otherwise we get a lot of discretization effect (i.e. 100% of the times we observe this term are fish,
			# but we have 1 fish annotation)
			if term_info[cterm]['total_annotations'] < 4:
				debug(2, 'term %s has <4 (%d) total annotations' % (cterm, term_info[cterm]['total_annotations']))
				continue
			if num_term[cterm] == 0:
				debug(4,'numterm for %s is 0' % cterm)
				continue
			# we use -2 to give lower weight to low. num
			term_frac[cterm] = num_term[cterm] / term_info[cterm]['total_annotations']
		# wordcloud_image = draw_cloud(term_frac, num_high_term=num_high_term, num_low_term=num_low_term)
		# wordcloud_image = draw_cloud(num_term, num_high_term=num_high_term, num_low_term=num_low_term, term_frac=term_frac)
		# wpart += render_template('wordcloud.html', wordcloudimage=urllib.parse.quote(wordcloud_image))

	if show_relative_freqs:
		debug(1, 'drawing relative freq. wordcloud')
		# draw relative frequencies
		if len(term_frac) == 0:
			debug(4, 'not enough info for relative freq - switching to absolute')
			wordcloud_image = draw_cloud(num_term, num_high_term=num_high_term, num_low_term=num_low_term, term_frac=term_frac)
		else:
			wordcloud_image = draw_cloud(term_frac, num_high_term=num_high_term, num_low_term=num_low_term, term_frac=term_frac)
	else:
		debug(1, 'drawing absolute count wordcloud')
		# draw absolute frequencies
		wordcloud_image = draw_cloud(num_term, num_high_term=num_high_term, num_low_term=num_low_term, term_frac=term_frac)

	wordcloudimage=urllib.parse.quote(wordcloud_image)
	if wordcloudimage:
		wpart += render_template('wordcloud.html', wordcloudimage=urllib.parse.quote(wordcloud_image))
	else:
		wpart += '<p></p>'
	return wpart
