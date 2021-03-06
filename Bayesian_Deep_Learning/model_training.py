import os
import sys
sys.path.insert(0, '/home/raul/Desktop/Million_Song_Dataset')
import time
import tensorflow as tf
import numpy as np
from mlp.data_providers import MSD10GenreDataProvider, MSD25GenreDataProvider

import pickle
def load_from_file(filename):
    """ Load object from file
    """
    object = []
    f = open(filename + '.pckl', 'rb')
    object = pickle.load(f)
    f.close()
    return object
def save_to_file(filename, object):
    """ Save object to file
    """
    f = open(filename + '.pckl', 'wb')
    pickle.dump(object, f)
    f.close()

train_data = MSD10GenreDataProvider('train', batch_size=50)
valid_data = MSD10GenreDataProvider('valid', batch_size=50)

def fully_connected_layer(inputs, input_dim, output_dim, nonlinearity=tf.nn.relu):
    weights = tf.Variable(
        tf.truncated_normal(
            [input_dim, output_dim], stddev=2. / (input_dim + output_dim)**0.5), 
        'weights')
    biases = tf.Variable(tf.zeros([output_dim]), 'biases')
    outputs = nonlinearity(tf.matmul(inputs, weights) + biases)
    return outputs, weights, biases

def conv_layer_maxpooling(inputs, image_height, image_width, in_channels, out_channels, kernel_height, kernel_width, nonlinearity=tf.nn.relu):
    weigths = tf.Variable(
        tf.truncated_normal(
            [kernel_height, kernel_width, in_channels, out_channels], stddev=2. / (kernel_height+ kernel_width+ in_channels+ out_channels) ** 0.5), 
        'weights')  
    biases = tf.Variable(tf.zeros([out_channels]), 'biases')
    inputs_1 = tf.reshape(inputs, [50, image_height, image_width, in_channels])
    strides = [1,1,1,1]
    padding = "VALID"
    output_no_bias = tf.nn.conv2d(inputs_1, weigths, strides, padding)
    output_no_pooling = tf.nn.bias_add(output_no_bias, biases)
    #we add pooling to reduce the dimensionality
    pooling_size = 2
    ksize = [1,pooling_size,1,1]
    strides2 = [1,pooling_size,1,1]
    output = tf.nn.max_pool(output_no_pooling, ksize, strides2, padding)
    temp = tf.reshape(output, [50, int(np.ceil(    (image_height-(kernel_height -1))/pooling_size   )) * out_channels])
    outputs = nonlinearity(temp)  
    return outputs, weigths, biases

inputs = tf.placeholder(tf.float32, [None, train_data.inputs.shape[1]], 'inputs')
targets = tf.placeholder(tf.float32, [None, train_data.num_classes], 'targets')
num_hidden = 200
kernels=50
kernel_height=3
in_channels=1

with tf.name_scope('layer-1'):
    hidden_1, hidden1_weights, biases_1 = conv_layer_maxpooling(inputs, 120, 25, 1, kernels, kernel_height, 25)
with tf.name_scope('layer-2'):
    hidden_2, hidden2_weights, biases_2 = conv_layer_maxpooling(hidden_1,  int(np.ceil(    (120-(kernel_height -1))/2   )), kernels, 1, kernels, kernel_height, kernels)
with tf.name_scope('layer-3'):
    hidden_3, hidden3_weights, biases_3 = fully_connected_layer(hidden_2,     (   int(np.ceil(    (int(np.ceil(    (120-(kernel_height -1))/2   )) -(kernel_height -1))/2   ))  )    * kernels, num_hidden)
with tf.name_scope('output-layer'):
    outputs, hidden4_weights, biases_4 = fully_connected_layer(hidden_3, num_hidden, train_data.num_classes, tf.identity)

with tf.name_scope('error'):
    beta = 0.01
    error = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(outputs, targets)
                           + beta * tf.nn.l2_loss(hidden1_weights) 
                           + beta * tf.nn.l2_loss(hidden2_weights) 
                           + beta * tf.nn.l2_loss(hidden3_weights) 
                          )

with tf.name_scope('accuracy'):
    accuracy = tf.reduce_mean(tf.cast(
            tf.equal(tf.argmax(outputs, 1), tf.argmax(targets, 1)), 
            tf.float32))
    
with tf.name_scope('train'):
    train_step = tf.train.AdamOptimizer().minimize(error)

init = tf.global_variables_initializer()

with tf.Session() as sess:
    sess.run(init)
    err_val = {}
    acc_val = {}
    for e in range(100):
        running_error = 0.
        running_accuracy = 0.
        run_start_time = time.time()
        for input_batch, target_batch in train_data:
            _, batch_error, batch_acc = sess.run(
                [train_step, error, accuracy],
                feed_dict={inputs: input_batch, targets: target_batch})
            running_error += batch_error
            running_accuracy += batch_acc
        run_time = time.time() - run_start_time
        running_error /= train_data.num_batches
        running_accuracy /= train_data.num_batches
        print('End of epoch {0:02d}: err(train)={1:.2f} acc(train)={2:.2f} time={3:.2f}'
              .format(e + 1, running_error, running_accuracy, run_time))
        valid_error = 0.
        valid_accuracy = 0.
        for input_batch, target_batch in valid_data:
            batch_error, batch_acc = sess.run(
                [error, accuracy], 
                feed_dict={inputs: input_batch, targets: target_batch})
            valid_error += batch_error
            valid_accuracy += batch_acc
        valid_error /= valid_data.num_batches
        valid_accuracy /= valid_data.num_batches
        err_val[e + 1] = valid_error
        acc_val[e + 1] = valid_accuracy            
        print('                 err(valid)={0:.2f} acc(valid)={1:.2f}'
            .format(valid_error, valid_accuracy))
    hidden1_weights_bestmodel = hidden1_weights.eval()
    hidden2_weights_bestmodel = hidden2_weights.eval()
    hidden3_weights_bestmodel = hidden3_weights.eval()
    hidden4_weights_bestmodel = hidden4_weights.eval()
    biases_1_bestmodel = biases_1.eval()
    biases_2_bestmodel = biases_2.eval()
    biases_3_bestmodel = biases_3.eval()
    biases_4_bestmodel = biases_4.eval()

save_to_file('data/hidden1_bestmodel',  hidden1_weights_bestmodel)
save_to_file('data/hidden2_bestmodel',  hidden2_weights_bestmodel)
save_to_file('data/hidden3_bestmodel',  hidden3_weights_bestmodel)
save_to_file('data/hidden4_bestmodel',  hidden4_weights_bestmodel)
save_to_file('data/biases_1_bestmodel',  biases_1_bestmodel)
save_to_file('data/biases_2_bestmodel',  biases_2_bestmodel)
save_to_file('data/biases_3_bestmodel',  biases_3_bestmodel)
save_to_file('data/biases_4_bestmodel',  biases_4_bestmodel)