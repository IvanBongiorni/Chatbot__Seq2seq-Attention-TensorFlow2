"""
Author: Ivan Bongiorni,     https://github.com/IvanBongiorni
2020-03-08

DATA PRE-PROCESSING TOOLBOX FOR amazonhelp TWEETS

The code is intended to be used as follows: it's a local module containing a main wrapper function: get_Amazon_dataset().
It should be called from the main Notebook or script, provided the right path to the Twitter Customer Support Dataset
in order to get the already vectorized Q and A matrices. Additionally, a Python dictionary char2idx is returned too,
providing a mapping between characters and numerical indexes.

Data are pre-processed for character embedding RNNs.
"""

def generate_alphabet():
    import string

    alphabet = string.printable
    alphabet = alphabet.replace('ABCDEFGHIJKLMNOPQRSTUVWXYZ', '')
    alphabet = alphabet.replace('[\\]^_`{|}~', '')
    alphabet = alphabet.replace('\t\n\r\x0b\x0c', '')
    alphabet = alphabet.replace(';<=>', '')
    alphabet = alphabet.replace('*+', '')
    # alphabet += '§' # ö'
    return alphabet


def check_language(tweet):
    ''' Uses langdetect to check for English tweets. Non-English tweets won't be
    considered. List remove_for_langdetect is meant to fix recurrent errors in
    Japanese tweets that get mistaken for English. '''
    import langdetect

    remove_for_langdetect = [
        'amazon fire tv stick', 'fire tv stick', 'amazonfiretvstick', 'amazonmusicunlimited',
        'amazon kindle unlimited', 'amazon echo dot', 'prime music'
    ]

    # this block prevents some 'ja' to be detected as 'en'
    if any([ element in tweet for element in remove_for_langdetect ]):
        for element in remove_for_langdetect:
            tweet = tweet.replace(element, '')

    # return 'en' for no language tweets like single emoji's
    try:
        return langdetect.detect(tweet)
    except:
        return 'en'


def clean_text(tweet):
    '''
    This is the main, initial pre-processing function of texts. It executes the
    following steps:
        - Removes unwanted chars, such as utf-8 and emoji's
        - Replaces URLs with char §
        - Replaces order numbers with char ö
        - Collapses multiple spaces into one, and trims final str
    (It is to be iterated on whole dataset column with list comprehension.)

    Further processing must be differentiated between Customers and Company tweets.
    '''
    import string
    import re
    import numpy as np
    import pandas as pd

    # Removal of unwanted chars / patterns
    tweet = tweet.replace('\t', ' ') # space or new line chars to subst with space
    tweet = tweet.replace('\n', ' ')
    tweet = tweet.replace('\r', ' ')
    tweet = tweet.replace('\x0b', ' ')
    tweet = tweet.replace('\x0c', ' ')
    tweet = tweet.replace('\u200b', ' ')
    tweet = tweet.replace('\u200d', ' ')
    tweet = tweet.replace(';', ",")
    tweet = tweet.replace('‘', "'")
    tweet = tweet.replace('‘', "'")
    tweet = tweet.replace('´', "'")
    tweet = tweet.replace('`', "'")
    tweet = tweet.replace('’', "'")
    tweet = tweet.replace('”', "'")
    tweet = tweet.replace('“', "'")

    tweet = tweet.replace('\{', "\(")
    tweet = tweet.replace('\}', "\)")
    tweet = tweet.replace('\[', "\(")
    tweet = tweet.replace('\]', "\)")

    tweet = tweet.replace('&amp;', '&')
    tweet = tweet.replace('@amazonhelp', '') # Remove '@amazonhelp'

    tweet = re.sub(r'@[0-9]+', '', tweet) # reference id's (e.g. '@12345')
    tweet = re.sub(r'(\^\w*)$', '', tweet) # Remove final signature (e.g.: ... ^ib)
    tweet = tweet.replace('\u200d♂️', '') # recurrent two emoji codes
    tweet = tweet.replace('\u200d♀️', '')

    # Removes ref to tweet parts, e.g.: "... (1/2)"
    tweet = re.sub(r"\([0-9]/[0-9]\)", "", tweet)

    # Substitution of elements with anonymized tags
    tweet = re.sub(r'https?://\S+|www\.\S+', '§', tweet) # Replace URLs with char §
    # tweet = re.sub(r'\w{3}-\w{7}-\w{7}', 'ö', tweet) # Replace order numbers with char ö

    tweet = re.sub(' +', ' ', tweet)  # collapse multiple spaces left into one
    tweet = tweet.strip() # trim left and right spaces
    return tweet


def process_x_text(tweet, alphabet):
    ''' Processing of Input tweets: all chars that are not in the chosen
    alphabet will be sustituted with char ü '''
    import re

    tweet = [ char if char in alphabet else 'ü' for char in tweet ]
    tweet = ''.join(tweet)

    tweet = re.sub(' +', ' ', tweet)  # collapse multiple spaces left into one
    tweet = tweet.strip() # trim left and right spaces
    return tweet


def process_y_text(tweet, alphabet):
    ''' Processing of Response: all chars that are not in the chosen
    alphabet will be eliminated. Eventual multiple spaces will be collapsed '''
    import re

    tweet = [ char if char in alphabet else ' ' for char in tweet ]
    tweet = ''.join(tweet)

    tweet = re.sub(' +', ' ', tweet)  # collapse multiple spaces left into one
    tweet = tweet.strip() # trim left and right spaces
    return tweet


def organize_QA_dataframe(df, alphabet):
    '''
    Builds Q/A dataset. Steps:
    1. Pick Q tweets that started a chat and attach relative A.
    2. Filter for selected company
    3. Process text: Turn all lowercase; Keep English tweets only; Keep just complete
       tweets - not with (1/2) or (2/2); Call text cleant_text(), for both and separate
       for Q and A
    '''
    import numpy as np
    import pandas as pd

    # Pick clients' tweets that started a chat
    exchanges = df[ df['inbound'] & (df['in_response_to_tweet_id'].isna()) ]

    # Attach relative answers
    exchanges = exchanges.merge(df[['author_id', 'text', 'in_response_to_tweet_id']],
                                left_on = 'tweet_id',
                                right_on = 'in_response_to_tweet_id')
    # Filter for current company
    exchanges = exchanges[ exchanges['author_id_y'] == 'AmazonHelp' ]
    exchanges = exchanges[['text_x', 'text_y']]  # Keep useful cols

    # Turn all lowercase
    exchanges['text_x'] = exchanges['text_x'].str.lower()
    exchanges['text_y'] = exchanges['text_y'].str.lower()

    # Keep only 'en' tweets
    exchanges['english_x'] = [ check_language(tweet) for tweet in exchanges['text_x'].tolist() ]
    exchanges['english_y'] = [ check_language(tweet) for tweet in exchanges['text_y'].tolist() ]
    exchanges = exchanges[ (exchanges['english_x'] == 'en') & (exchanges['english_y'] == 'en') ]
    exchanges.drop(['english_x', 'english_y'], axis = 1, inplace = True)

    # Keep just complete tweets - not (1/2) or (2/2)'s
    exchanges = exchanges[ (~exchanges['text_y'].str.endswith('(1/2)')) & (~exchanges['text_y'].str.endswith('(2/2)')) ]

    # Main text cleaning
    exchanges['text_x'] = [ clean_text(tweet) for tweet in exchanges['text_x'].tolist() ]
    exchanges['text_y'] = [ clean_text(tweet) for tweet in exchanges['text_y'].tolist() ]

    # Differentiate cleaning for Q and A
    exchanges['text_x'] = [ process_x_text(tweet, alphabet) for tweet in exchanges['text_x'].tolist() ]
    exchanges['text_y'] = [ process_y_text(tweet, alphabet) for tweet in exchanges['text_y'].tolist() ]

    return exchanges


def vectorize_tweet(tweet, char2idx):
    ''' chars --> np.array(idx)    To be iterated by vectorize_dataset().
    Out-of-alphabet chars set to 0 for RNN masking. '''
    import numpy as np

    chars_vector = [ char for char in tweet ]
    chars_vector = [ char2idx[char] if char in char2idx.keys() else 0 for char in chars_vector ]
    chars_vector = np.array(chars_vector)
    return chars_vector


def vectorize_dataset(df, char2idx):
    '''
    Exports final Q and A numpy matrices. Steps:
        Iterates vectorization on each Q and A list of tweets
        Left-zero pads each vectorize sequence to same max length
        Packs both into single np.array's
        Sets common datatype
    '''
    import numpy as np

    Q = [ vectorize_tweet(tweet, char2idx) for tweet in df['text_x'].tolist() ]
    A = [ vectorize_tweet(tweet, char2idx) for tweet in df['text_y'].tolist() ]

    max_length = max(len(max(Q, key=len)), len(max(A, key=len)))
    Q = [ np.concatenate([ np.zeros((max_length-len(q))), q ]) for q in Q ]
    A = [ np.concatenate([ np.zeros((max_length-len(a))), a ]) for a in A ]

    Q = np.stack(Q)
    A = np.stack(A)

    Q = Q.astype(np.float32)
    A = A.astype(np.float32)
    return Q, A


def train_test_val_split(Q, A, val_size, test_size, seed):
    import numpy as np
    import sklearn

    # np.random.seed(seed)
    # perm = np.random.permutation(np.array(range(Q.shape[0])))
    # Q = Q[ perm , : ]
    # A = A[ perm , : ]

    # shuffle
    Q, A = sklearn.utils.shuffle(Q, A, random_state = seed)

    # Compute cutoffs to make splits
    train_val_cutoff = int( Q.shape[0] * (1-(val_size+test_size)) )
    val_test_cutoff = int( Q.shape[0] * (1 - test_size) )

    Q_train = Q[ 0:train_val_cutoff , : ]
    A_train = A[ 0:train_val_cutoff , : ]

    Q_val = Q[ train_val_cutoff:val_test_cutoff , : ]
    A_val = A[ train_val_cutoff:val_test_cutoff , : ]

    Q_test = Q[ val_test_cutoff: , : ]
    A_test = A[ val_test_cutoff: , : ]

    return Q_train, A_train, Q_val, A_val, Q_test, A_test


def get_amazon_dataset(params):
    ''' Main wrapper of the whole pipe. Returns ready-to-use dataset
    of @amazonhelp customer support tweets '''
    import time
    import string
    import re
    import numpy as np
    import pandas as pd
    import langdetect

    from pdb import set_trace as BP

    # Load data
    df = pd.read_csv('{}twcs.csv'.format(params['data_path']))

    # Generate alphabet
    alphabet = generate_alphabet()
    print('\tGeneration of alphabet of size {}.'.format(len(alphabet)))
    
    # Mapping char-index for vectorization
    char2idx = { char[1]: char[0] for char in enumerate(alphabet, 1) }
    print('\tCreation of dictionary for vectorization.')

    print('\tCleaning and processing of text data...')
    start = time.time()
    df = organize_QA_dataframe(df, alphabet)
    print('\t... Done in {}ss.'.format(round(time.time()-start, 2)))

    Q, A = vectorize_dataset(df, char2idx)
    print('\tVectorization of characters.')

    Q_train, A_train, Q_val, A_val, Q_test, A_test = train_test_val_split(Q = Q, A = A,
                                                                          val_size = params['val_test_size'][0],
                                                                          test_size = params['val_test_size'][1],
                                                                          seed = params['seed'])
    print('\tTrain-Validation-Test split.')

    # Expand dimensions for compatibility with model output
    A_train = np.expand_dims(A_train, axis = -1)
    A_val = np.expand_dims(A_val, axis = -1)
    A_test = np.expand_dims(A_test, axis = -1)

    return Q_train, A_train, Q_val, A_val, Q_test, A_test, char2idx
