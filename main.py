"""ML engineer challenge

Automatically generated by Colaboratory.

"""

from google.colab import drive
drive.mount('/content/drive')

!pip install numpy
!pip install tensorflow
!pip install matplotlib

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input
import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras import mixed_precision

# Enable mixed precision
mixed_precision.set_global_policy('mixed_float16')

# Path of train and test data
train_dir = "/content/drive/MyDrive/klimb_llm_optimization_challenge/seg_train"
test_dir = "/content/drive/MyDrive/klimb_llm_optimization_challenge/seg_test"

# Data configs
batch_size = 16
img_height = 150
img_width = 150

# Load a subset of train data
train_ds = tf.keras.utils.image_dataset_from_directory(
    train_dir,
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size)
train_ds = train_ds.take(100)  # Load only 100 batches for training

# Load a subset of test data
test_ds = tf.keras.utils.image_dataset_from_directory(
    test_dir,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size)
test_ds = test_ds.take(20)  # Load only 20 batches for evaluation

# Training the MASTER Model - using Transfer Learning
# Here we are using a smaller base model
base_model = keras.applications.ResNet50(
    weights='imagenet',
    input_shape=(img_height, img_width, 3),
    include_top=False)

base_model.trainable = False

inputs = keras.Input(shape=(img_height, img_width, 3))
x = base_model(inputs, training=False)
x = keras.layers.GlobalAveragePooling2D()(x)
outputs = keras.layers.Dense(6)(x)

master_model = keras.Model(inputs, outputs)

# Use a faster optimizer
optimizer = keras.optimizers.RMSprop()

master_model.compile(
    optimizer=optimizer,
    loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=[keras.metrics.SparseCategoricalAccuracy()],
)

epochs = 10
early_stop = EarlyStopping(monitor='val_loss', patience=5)

master_model.fit(train_ds, epochs=epochs, callbacks=[early_stop])

# Generate results on test data
results = master_model.evaluate(test_ds)
print(f"Test accuracy with trained master model: {results[1] * 100:.2f}%")

"""# Student model

"""

import tensorflow as tf
from tensorflow.keras import layers, models

def train_student_model(base_model, train_ds, test_ds, img_height, img_width):
    # Define the student model architecture
    student_inputs = layers.Input(shape=(img_height, img_width, 3))
    x = base_model(student_inputs, training=False)  # Use the base model as a layer
    x = layers.Flatten()(x)
    x = layers.Dense(128, activation='relu')(x)
    student_outputs = layers.Dense(6)(x)
    student_model = models.Model(student_inputs, student_outputs)

    # Compile the student model
    student_model.compile(optimizer='adam',
                          loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                          metrics=[keras.metrics.SparseCategoricalAccuracy()])

    # Train the student model using the dataset
    student_model.fit(train_ds, epochs=10, validation_data=test_ds)

    return student_model

# Train the student model
student_model = train_student_model(base_model, train_ds, test_ds, 150, 150)

# Evaluate and compare the master and student models
print(f"Model size: {student_model.count_params() * 4 / (1024 ** 2):.2f} MB")
print(f"Model size: {master_model.count_params() * 4 / (1024 ** 2):.2f} MB")
print(f"Model size ratio: {student_model.count_params() / master_model.count_params():.2f}")

# Calculate latency (time taken for a single prediction)
import time

start_time = time.time()
_ = base_model.predict(test_ds.take(1))
master_latency = time.time() - start_time
print(f"Master model latency: {master_latency * 1000:.2f} ms")

start_time = time.time()
_ = student_model.predict(test_ds.take(1))
student_latency = time.time() - start_time
print(f"Student model latency: {student_latency * 1000:.2f} ms")

# Load a sample image for testing
sample_image = np.random.rand(1, img_height, img_width, 3)  # Single random image

# Perform inference on the sample image using the student_model
predictions = student_model.predict(sample_image)
predicted_class = np.argmax(predictions)

print(f"Predicted class: {predicted_class}")
