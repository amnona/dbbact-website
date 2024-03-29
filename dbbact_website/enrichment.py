import requests

import numpy as np
from .mini_dsfdr import dsfdr
from .utils import debug, get_dbbact_server_address
from collections import defaultdict


def calour_enrichment(seqs1, seqs2, term_type="term"):
    '''
    Do dbbact term and annotation enrichment analysis for 2 lists of sequences (comparing first to second list of sequences)

    Parameters
    ----------
    seqs1:list of str
        first set of sequences (ACGT)
    seqs1:list of str
        second set of sequences (ACGT)
    term_type : str (optional)
        type of the term to analyze for enrichment. can be:
        "term" : analyze the terms per annotation (not including parent terms)
        "annotation" : analyze the annotations associated with each sequence

    Returns
    -------
    err : str
        empty if ok, otherwise the error encountered
    term_list : list of str
        the terms which are enriched
    pvals : list of float
        the p-value for each term
    odif : list of float
        the effect size for each term
    '''
    import calour as ca

    db = ca.database._get_database_class('dbbact')

    # set the same seed (since we use a random permutation test)
    np.random.seed(2018)

    all_seqs = set(seqs1).union(set(seqs2))
    seqs2 = list(all_seqs - set(seqs1))
    if len(seqs2) == 0:
        return 'No sequences remaining in background fasta after removing the sequences of interest', None, None, None
    all_seqs = list(all_seqs)

    # get the annotations for the sequences
    info = {}
    info['sequence_terms'], info['sequence_annotations'], info['annotations'] = get_seq_annotations_fast(all_seqs)

    terms_df, resmat, features_df = db.db.term_enrichment(seqs1, seqs2, info['annotations'], info['sequence_annotations'], term_type=term_type)
    print(terms_df)
    return '', terms_df['feature'].values, terms_df['qval'], terms_df['odif']


def getannotationstrings2(cann):
    """
    get a nice string summary of a curation

    input:
    cann : dict from /sequences/get_annotations (one from the list)
    output:
    cdesc : str
        a short summary of each annotation
    """
    cdesc = ''
    if cann['description']:
        cdesc += cann['description'] + ' ('
    if cann['annotationtype'] == 'diffexp':
        chigh = []
        clow = []
        call = []
        for cdet in cann['details']:
            if cdet[0] == 'all':
                call.append(cdet[1])
                continue
            if cdet[0] == 'low':
                clow.append(cdet[1])
                continue
            if cdet[0] == 'high':
                chigh.append(cdet[1])
                continue
        cdesc += ' high in '
        for cval in chigh:
            cdesc += cval + ' '
        cdesc += ' compared to '
        for cval in clow:
            cdesc += cval + ' '
        cdesc += ' in '
        for cval in call:
            cdesc += cval + ' '
    elif cann['annotationtype'] == 'isa':
        cdesc += ' is a '
        for cdet in cann['details']:
            cdesc += 'cdet,'
    elif cann['annotationtype'] == 'contamination':
        cdesc += 'contamination'
    else:
        cdesc += cann['annotationtype'] + ' '
        for cdet in cann['details']:
            cdesc = cdesc + ' ' + cdet[1] + ','

    if len(cdesc) >= 1 and cdesc[-1] == ',':
        cdesc = cdesc[:-1]
    return cdesc


def get_seq_annotations_fast(sequences):
    debug(2, 'get_seq_annotations_fast for %d sequences' % len(sequences))
    rdata = {}
    rdata['sequences'] = sequences
    res = requests.get(get_dbbact_server_address() + '/sequences/get_fast_annotations', json=rdata)
    if res.status_code != 200:
        debug(5, 'error getting fast annotations for sequence list')
        return None, None, None
    res = res.json()
    debug(2, 'got %d total annotations' % len(res['annotations']))

    sequence_terms = {}
    sequence_annotations = {}
    for cseq in sequences:
        sequence_terms[cseq] = []
        sequence_annotations[cseq] = []
    for cseqannotation in res['seqannotations']:
        cpos = cseqannotation[0]
        # need str since json dict is always string
        cseq = sequences[cpos]
        sequence_annotations[cseq].extend(cseqannotation[1])
        for cannotation in cseqannotation[1]:
            for k, v in res['annotations'][str(cannotation)]['parents'].items():
                if k == 'high' or k == 'all':
                    for cterm in v:
                        sequence_terms[cseq].append(cterm)
                elif k == 'low':
                    for cterm in v:
                        sequence_terms[cseq].append('-' + cterm)

    annotations = res['annotations']

    # replace the string in the key with an int (since in json key is always str)
    keys = list(annotations.keys())
    for cid in keys:
        annotations[int(cid)] = annotations.pop(cid)

    # count total associations
    total_annotations = 0
    for cseq_annotations in sequence_annotations.values():
        total_annotations += len(cseq_annotations)
    debug(2, 'Got %d associations' % total_annotations)

    return sequence_terms, sequence_annotations, annotations


def _get_term_features(features, feature_terms):
    '''Get numpy array of score of each term for each feature

    Parameters
    ----------
    features : list of str
        A list of DNA sequences
    feature_terms : dict of {feature: list of tuples of (term, amount)}
        The terms associated with each feature in exp
        feature (key) : str the feature (out of exp) to which the terms relate
        feature_terms (value) : list of tuples of (str or int the terms associated with this feature, count)

    Returns
    -------
    numpy array of T (terms) * F (features)
        total counts of each term (row) in each feature (column)
    list of str
        list of the terms corresponding to the numpy array rows
    '''
    # get all terms
    terms = {}
    cpos = 0
    for cfeature, ctermlist in feature_terms.items():
        for cterm, ccount in ctermlist:
            if cterm not in terms:
                terms[cterm] = cpos
                cpos += 1

    tot_features_inflated = 0
    feature_pos = {}
    for cfeature in features:
        ctermlist = feature_terms[cfeature]
        feature_pos[cfeature] = tot_features_inflated
        tot_features_inflated += len(ctermlist)

    # populate the matrix
    res = np.zeros([len(terms), len(features)])
    for idx, cfeature in enumerate(features):
        for cterm, ctermcount in feature_terms[cfeature]:
            res[terms[cterm], idx] += ctermcount

    term_list = sorted(terms, key=terms.get)
    debug(2, 'created terms X features matrix with %d terms (rows), %d features (columns)' % (res.shape[0], res.shape[1]))
    return res, term_list


def _get_term_features_inflated(features, feature_terms):
    '''Get numpy array of score of each term for each feature. This is the inflated version (used for card mean) to overcome the different number of annotations per feature. But slower and not memory efficient

    Parameters
    ----------
    features : list of str
        A list of DNA sequences
    feature_terms : dict of {feature: list of tuples of (term, amount)}
        The terms associated with each feature in exp
        feature (key) : str the feature (out of exp) to which the terms relate
        feature_terms (value) : list of tuples of (str or int the terms associated with this feature, count)

    Returns
    -------
    numpy array of T (terms) * F (inflated features)
        total counts of each term (row) in each feature (column)
    list of str
        list of the terms corresponding to the numpy array rows
    '''
    # get all terms
    terms = {}
    cpos = 0
    for cfeature, ctermlist in feature_terms.items():
        for cterm, ccount in ctermlist:
            if cterm not in terms:
                terms[cterm] = cpos
                cpos += 1

    tot_features_inflated = 0
    feature_pos = {}
    for cfeature in features:
        ctermlist = feature_terms[cfeature]
        feature_pos[cfeature] = tot_features_inflated
        tot_features_inflated += len(ctermlist)

    res = np.zeros([len(terms), tot_features_inflated])

    for cfeature in features:
        for cterm, ctermcount in feature_terms[cfeature]:
            res[terms[cterm], feature_pos[cfeature]] += ctermcount
    term_list = sorted(terms, key=terms.get)
    debug(2, 'created terms X features matrix with %d terms (rows), %d features (columns)' % (res.shape[0], res.shape[1]))
    return res, term_list


def _get_all_annotation_string_counts(features, sequence_annotations, annotations):
    feature_annotations = {}
    for cseq, annotations_list in sequence_annotations.items():
        if cseq not in features:
            continue
        newdesc = []
        for cannotation in annotations_list:
            cdesc = getannotationstrings2(annotations[cannotation])
            newdesc.append((cdesc, 1))
        feature_annotations[cseq] = newdesc
    return feature_annotations


def _get_all_term_counts(features, feature_annotations, annotations):
    '''Get counts of all terms associated with each feature

    Parameters
    ----------
    features: list of str
        the sequences to get the terms for
    feature_annotations: dict of {feature (str): annotationIDs (list of int))
        the list of annotations each feature appears in
    annotations: dict of {annotationsid (int): annotation details (dict)}
        all the annotations in the experiment

    Returns
    -------
    dict of {feature (str): annotation counts (list of (term(str), count(int)))}
    '''
    feature_terms = {}
    for cfeature in features:
        annotation_list = [annotations[x] for x in feature_annotations[cfeature]]
        feature_terms[cfeature] = get_annotation_term_counts(annotation_list)
    return feature_terms


def get_annotation_term_counts(annotations):
    '''Get the annotation type corrected count for all terms in annotations

    Parameters
    ----------
    annotations : list of dict
        list of annotations

    Returns
    -------
        list of tuples (term, count)
    '''
    term_count = defaultdict(int)
    for cannotation in annotations:
        if cannotation['annotationtype'] == 'common':
            for cdesc in cannotation['details']:
                term_count[cdesc[1]] += 1
            continue
        if cannotation['annotationtype'] == 'dominant':
            for cdesc in cannotation['details']:
                term_count[cdesc[1]] += 2
            continue
        if cannotation['annotationtype'] == 'other':
            for cdesc in cannotation['details']:
                term_count[cdesc[1]] += 0.5
            continue
        if cannotation['annotationtype'] == 'contamination':
            term_count['contamination'] += 1
            continue
        if cannotation['annotationtype'] in ['diffexp', 'positive correlation', 'negative correlation']:
            for cdesc in cannotation['details']:
                if cdesc[0] == 'all':
                    term_count[cdesc[1]] += 1
                    continue
                if cdesc[0] == 'high':
                    term_count[cdesc[1]] += 2
                    continue
                if cdesc[0] == 'low':
                    term_count[cdesc[1]] -= 2
                    continue
                debug(4, 'unknown detail type %s encountered' % cdesc[0])
            continue
        if cannotation['annotationtype'] == 'other':
            continue
        debug(4, 'unknown annotation type %s encountered' % cannotation['annotationtype'])
    res = []
    for k, v in term_count.items():
        # flip and add '-' to term if negative
        if v < 0:
            k = '-' + k
            v = -v
        res.append((k, v))
    return res


def enrichment(seqs1, seqs2, term_type="term"):
    '''
    Do dbbact term and annotation enrichment analysis for 2 lists of sequences (comparing first to second list of sequences)

    Parameters
    ----------
    seqs1:list of str
        first set of sequences (ACGT)
    seqs1:list of str
        second set of sequences (ACGT)
    term_type : str (optional)
        type of the term to analyze for enrichment. can be:
        "term" : analyze the terms per annotation (not including parent terms)
        "annotation" : analyze the annotations associated with each sequence


    Returns
    -------
    err : str
        empty if ok, otherwise the error encountered
    term_list : list of str
        the terms which are enriched
    pvals : list of float
        the p-value for each term
    odif : list of float
        the effect size for each term
    '''
    # set the same seed (since we use a random permutation test)
    np.random.seed(2018)

    all_seqs = set(seqs1).union(set(seqs2))
    seqs2 = list(all_seqs - set(seqs1))
    if len(seqs2) == 0:
        return 'No sequences remaining in background fasta after removing the sequences of interest', None, None, None
    all_seqs = list(all_seqs)

    # get the annotations for the sequences
    info = {}
    info['sequence_terms'], info['sequence_annotations'], info['annotations'] = get_seq_annotations_fast(all_seqs)

    if term_type == 'term':
        debug(2, 'getting all_term counts')
        feature_terms = _get_all_term_counts(all_seqs, info['sequence_annotations'], info['annotations'])
    elif term_type == 'annotation':
        debug(2, 'getting all_annotation string counts')
        feature_terms = _get_all_annotation_string_counts(all_seqs, info['sequence_annotations'], info['annotations'])
    else:
        debug(8, 'strange term_type encountered: %s' % term_type)

    # count the total number of terms
    all_terms_set = set()
    for cterms in feature_terms.values():
        for (cterm, ccount) in cterms:
            all_terms_set.add(cterm)
    debug(2, 'found %d terms associated with all sequences (%d)' % (len(all_terms_set), len(all_seqs)))

    debug(2, 'getting seqs1 feature array')
    feature_array, term_list = _get_term_features(seqs1, feature_terms)
    debug(2, 'getting seqs2 feature array')
    bg_array, term_list = _get_term_features(seqs2, feature_terms)

    debug(2, 'bgarray: %s, feature_array: %s' % (bg_array.shape, feature_array.shape))
    all_feature_array = np.hstack([feature_array, bg_array])

    labels = np.zeros(all_feature_array.shape[1])
    labels[:feature_array.shape[1]] = 1

    debug(2, 'starting dsfdr for enrichment')
    keep, odif, pvals = dsfdr(all_feature_array, labels, method='meandiff', transform_type=None, alpha=0.1, numperm=1000, fdr_method='dsfdr')
    keep = np.where(keep)[0]
    if len(keep) == 0:
        debug(2, 'no enriched terms found')
    term_list = np.array(term_list)[keep]
    odif = odif[keep]
    pvals = pvals[keep]
    si = np.argsort(odif)
    odif = odif[si]
    pvals = pvals[si]
    term_list = term_list[si]
    return '', term_list, pvals, odif
