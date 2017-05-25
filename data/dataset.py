from tensorflow.contrib.learn.python.learn.datasets import base
import tensorflow as tf
import os
from datetime import datetime, timedelta
import numpy
import json
import operator
import re
import math
import random
from textblob import TextBlob as tb

word_counter = {}
tweet_counter = 0

flags = tf.app.flags
FLAGS = flags.FLAGS

def getWords(text):
    return re.compile('\w+').findall(text)


class Topic:
    def __init__(self, file_path):
        # parsing data
        self.parse_data = []
        data_file = open(file_path)
        for l in data_file:
            try:
                j = json.loads(l)
                text = j['text'].decode()
                self.parse_data.append((datetime.strptime(j['created_at'], "%a %b %d %H:%M:%S +0000 %Y"), text))
                words = getWords(text)
                for word in words:
                    if word in word_counter:
                        word_counter[word] += 1
                    else:
                        word_counter[word] = 1
                global tweet_counter
                tweet_counter += 1
            except:
                pass
        # sort according to date
        self.parse_data.sort()

    # get feature from the topic : interval - hour
    # output : array of feature
    def get_feature(self, interval):
        # each document_set

        def tf(word, blob):
            return float(blob.words.count(word)) / float(len(blob.words))

        def n_containing(word, bloblist):
            return float(sum(1 for blob in bloblist if word in blob.words))

        def idf(word, bloblist):
            return float(math.log(len(bloblist)) / float(1 + n_containing(word, bloblist)))

        def tfidf(word, blob, bloblist):
            return float(tf(word, blob) * float(idf(word, bloblist)))

        def twit_to_tf_dict(text):
            blob = tb(text)
            return {word: tf(word, blob) for word in blob.words}

        def normalize(vector):
            s = sum(vector)
            return [float(i)/s for i in vector]

        self.tf_data = []
        for date, text in self.parse_data:
            self.tf_data.append(twit_to_tf_dict(text))

        features = []
        while self.tf_data:
            global word_counter
            vector = {}
            for w in word_counter:
                vector[w] = 0.0
            length = random.randint(interval[0], interval[1])
            for i in range(length):
                for w in self.tf_data[0]:
                    if w in vector:
                        vector[w] += self.tf_data[0][w]
                self.tf_data.pop(0)
                if not self.tf_data:
                    break
            features.append(numpy.array(normalize(vector.values())))
        features = numpy.array(features)
        return features


class DataSet:
    def __init__(self, features, labels):
        self._features = features
        self._labels = labels
        self._epochs_completed = 0
        self._index_in_epoch = 0
        self._num_examples = len(features)

    def next_batch(self, batch_size):
        """Return the next `batch_size` examples from this data set."""
        start = self._index_in_epoch
        self._index_in_epoch += batch_size
        if self._index_in_epoch > self._num_examples:
            # Finished epoch
            self._epochs_completed += 1
            # Shuffle the data
            perm = numpy.arange(self._num_examples)
            numpy.random.shuffle(perm)
            self._features = self._features[perm]
            self._labels = self._labels[perm]
            # Start next epoch
            start = 0
            self._index_in_epoch = batch_size
            assert batch_size <= self._num_examples
        end = self._index_in_epoch
        return self._features[start:end], self._labels[start:end]


# read data from files in directory
def read_data_sets(train_ratio, validation_ratio, interval):
    features = []  # array of features
    topics = {} # array of topics
    labels = [] # array of labels
    for dirname, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            file_path = os.path.join(dirname, filename)
            # only files that contain 'Information' or 'Rumor' in its name
            if "nonrumor" in file_path or "rumor" in file_path:
                print(file_path)
                new_topic = Topic(file_path)
                topics[file_path] = new_topic

    # sort word_counter
    global word_counter, tweet_counter

    # extract top FLAGS.K words
    word_counter = sorted(word_counter.items(), key=operator.itemgetter(1), reverse=True)[:FLAGS.K]
    word_counter = [w[0] for w in word_counter]

    # print total number of tweets
    print("Processed total %s tweets" % tweet_counter)

    # get feature after count finishes
    for file_path in topics:
        print("feature from %s" % file_path)
        features.append(topics[file_path].get_feature(interval=interval))
        if "nonrumor" in file_path:
            labels.append(0)
        else:
            labels.append(1)

    # length of feature and label should be same
    assert len(features) == len(labels)

    # split train/test set according to ratio
    train_size = int(train_ratio*len(features))
    train_features = features[:train_size]
    train_labels = labels[:train_size]
    train = DataSet(train_features, train_labels)

    validation_size = int(validation_ratio*len(features))
    validation_features = features[train_size:train_size+validation_size]
    validation_labels = labels[train_size:train_size+validation_size]
    validation = DataSet(validation_features, validation_labels)

    test_features = features[train_size+validation_size:]
    test_labels = labels[train_size+validation_size:]
    test = DataSet(test_features, test_labels)
    return base.Datasets(train=train, validation=validation, test=test)

read_data_sets(train_ratio=.8, validation_ratio=.1, interval=[5,15])

