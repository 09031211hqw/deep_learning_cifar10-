#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "purelove"
__date__ = "2019/1/6 21:56"
import pickle
import os
import tensorflow as tf
import numpy as np

cifar_dir = './cifar-10-batches-py'
# dict_keys([b'batch_label', b'labels', b'data', b'filenames'])
# CIFAR-10 是一个包含60000张图片的数据集。其中每张照片为32*32的彩色照片，每个像素点包括RGB三个数值，数值范围 0 ~ 255。

def load_data(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f, encoding='bytes')
        return data[b'data'], data[b'labels']


# tensorfloa 的dataset 也可以实现shuffle_data
class CifarData:
    """
    mini batch 训练  shuffle使得数据之前没有联系 更具有泛化能力
    """

    def __init__(self, filenames, need_shuffle):
        all_datas = []
        all_labels = []
        for filename in filenames:
            data, labels = load_data(filename)
            # for item, labels in zip(data, labels):
            #     if labels in [0, 1]:
            all_datas.append(data)
            all_labels.append(labels)
        self._data = np.vstack(all_datas)
        self._data = self._data / 127.5 - 1  # 归一化
        """
        # 纵向合并
        [
        [1 2 3]
        [4 5 6]
        [7 8 9]
        ]"""
        self.num_examples = self._data.shape[0]
        self._need_shuffle = need_shuffle
        self._labels = np.hstack(all_labels)
        self.indicator = 0  # 指明当前数据集遍历到哪个位置
        """
        # 横向合并
        [1 0 1]
        """
        if self._need_shuffle:
            self._shuffle_data()
        #  [0,1,2,3,4,5] -> [5,2,3,4,1,0]

    def _shuffle_data(self):
        p = np.random.permutation(self.num_examples)
        self._data = self._data[p]
        self._labels = self._labels[p]

    def next_batch(self, batch_size):
        """
        返回batch_size个样本
        :param batch_size:
        :return:
        """
        end_indicator = self.indicator + batch_size
        if end_indicator > self.num_examples:
            if self._need_shuffle:
                self._shuffle_data()
                self.indicator = 0
                end_indicator = batch_size
            else:
                raise Exception("没有更多数据遍历完了.")
        if end_indicator > self.num_examples:
            raise Exception("batch_size比数据集还有大")
        batch_data = self._data[self.indicator: end_indicator]
        batch_labels = self._labels[self.indicator: end_indicator]
        self.indicator = end_indicator
        return batch_data, batch_labels

# 迁移学习
train_filnames = [os.path.join(cifar_dir, 'data_batch_%d' % i) for i in range(1, 6)]  # 所有的数据
test_data_filenames = [os.path.join(cifar_dir, 'test_batch')]

train_data = CifarData(train_filnames, need_shuffle=True)
test_data = CifarData(test_data_filenames, need_shuffle=False)

x = tf.placeholder(tf.float32, [None, 3072])  # None 输入的样本是不确定的
y = tf.placeholder(tf.int64, [None])
x_reshape = tf.reshape(x, [-1, 3, 32, 32])
x_transpose = tf.transpose(x_reshape, perm=[0, 2, 3, 1])
# VGG 卷积层后面继续添加卷积层
# [Test ] Step: 10000, acc: 0.73850
conv1_1 = tf.layers.conv2d(x_transpose,
                           filters=32,  # 输出通道数量=卷积核数量
                           kernel_size=(3, 3),
                           padding='same',  # 参数有两个一个是same, 一个是valid ，保证得到的新图与原图的shape相同；VALID则表示不需要填充，valid会减小
                           # strides=(2, 2),  # 步长  卧槽  这个步长要非常注意，  设置为2 准确率下降很多，图像信息丢失越多
                           activation=tf.nn.relu,
                           name='conv1_1')
conv1_2 = tf.layers.conv2d(conv1_1,
                           filters=32,  # 输出通道数量=卷积核数量
                           kernel_size=(3, 3),
                           padding='same',  # 参数有两个一个是same, 一个是valid ，保证得到的新图与原图的shape相同；VALID则表示不需要填充，valid会减小
                           # strides=(2, 2),  # 步长
                           activation=tf.nn.relu,
                           name='conv1_2')

# 16*16
pooling1 = tf.layers.max_pooling2d(conv1_2,
                                   (2, 2),  # kernel size
                                   (2, 2),  # stride
                                   name='pool1')

conv2_1 = tf.layers.conv2d(pooling1,
                           32,  # output channel number
                           (3, 3),  # kernel size
                           padding='same',
                           activation=tf.nn.relu,
                           name='conv2_1')
conv2_2 = tf.layers.conv2d(conv2_1,
                           32,  # output channel number
                           (3, 3),  # kernel size
                           padding='same',
                           activation=tf.nn.relu,
                           name='conv2_2')

# 8 * 8
pooling2 = tf.layers.max_pooling2d(conv2_2,
                                   (2, 2),  # kernel size
                                   (2, 2),  # stride
                                   name='pool2')

conv3_1 = tf.layers.conv2d(pooling2,
                           32,  # output channel number
                           (3, 3),  # kernel size
                           padding='same',
                           activation=tf.nn.relu,
                           name='conv3_1')
conv3_2 = tf.layers.conv2d(conv3_1,
                           32,  # output channel number
                           (3, 3),  # kernel size
                           padding='same',
                           activation=tf.nn.relu,
                           name='conv3_2')

# 4 * 4 * 32
pooling3 = tf.layers.max_pooling2d(conv3_2,
                                   (2, 2),  # kernel size
                                   (2, 2),  # stride
                                   name='pool3')
# [None, 4 * 4 * 32]
# 展平
flatten = tf.layers.flatten(pooling3)
# 全连接
y_ = tf.layers.dense(flatten, 10)

# e*x/sum(e*x)
# [[0.1, 0.2 ...], [0.2, 0.2, ...]]  # 每个样本都有一个概率分布

# p_y = tf.nn.softmax(y_)
# y_one_hot = tf.one_hot(y, 10, dtype=tf.float32)
# loss = tf.reduce_mean(tf.square(y_one_hot - p_y))


loss = tf.losses.sparse_softmax_cross_entropy(labels=y, logits=y_)
scale = 0.001  # l1正则化参数

# with tf.name_scope("loss"):
#     xentropy = tf.losses.sparse_softmax_cross_entropy(labels=y, logits=y_)
#     #loss = tf.losses.sparse_softmax_cross_entropy(labels=y, logits=y_)
#     base_loss = tf.reduce_mean(xentropy, name="avg_xentropy")
#     reg_loss = tf.reduce_sum(tf.abs(w))
#     loss = tf.add(base_loss, scale * reg_loss, name="loss")

predict = tf.argmax(y_, 1)  # 输出对应位置的值
# 1,0,1,0...
corrected = tf.equal(predict, y)
accuracy = tf.reduce_mean(tf.cast(corrected, tf.float64))
with tf.name_scope('train_op'):
    train_op = tf.train.AdamOptimizer(1e-3).minimize(loss)

init = tf.global_variables_initializer()
batch_size = 20
train_steps = 10000  # [Test ] Step: 10000, acc: 0.67350
test_steps = 100
# mini batch训练
with tf.Session() as sess:
    sess.run(init)
    for i in range(train_steps):
        batch_data, batch_labels = train_data.next_batch(batch_size)
        loss_val, accuracy_val, _ = sess.run([loss, accuracy, train_op],
                                             feed_dict={
                                                 x: batch_data,
                                                 y: batch_labels
                                             })
        if (i + 1) % 100 == 0:
            print("train step :%d , loss:%4.5f, acc:%4.5f" %
                  (i + 1, loss_val, accuracy_val))

        if (i + 1) % 1000 == 0:
            test_data = CifarData(test_data_filenames, False)
            all_test_acc_val = []
            for j in range(test_steps):
                test_batch_data, test_batch_labels = test_data.next_batch(batch_size)
                test_accuracy_val = sess.run([
                    accuracy
                ], feed_dict=
                {x: test_batch_data,
                 y: test_batch_labels}
                )
                all_test_acc_val.append(test_accuracy_val)
            test_acc = np.mean(all_test_acc_val)
            print('[Test ] Step: %d, acc: %4.5f' % (i + 1, test_acc))

#  迁移学习
# 1 保存模型（第三方）
# 2 载入模型
# 3 冻结前面几层，训练后面基层