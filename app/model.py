import tensorflow as tf
from tensorflow.keras import layers, Sequential
import pathlib
import numpy as np

# Directory containing the dataset
data_dir = pathlib.Path('/Users/muzeffertagiyev/Desktop/last_thesis_app/images_data/image_dataset')

# Image parameters
batch_size = 32
img_height = 250
img_width = 250

# Data preprocessing
train_ds = tf.keras.utils.image_dataset_from_directory(
    data_dir,
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    data_dir,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=(img_height, img_width),
    batch_size=batch_size
)

# Data augmentation
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical", input_shape=(img_height, img_width, 3)),
    layers.RandomRotation(0.15),
    layers.RandomZoom(0.1),
    layers.RandomBrightness(0.2),
    layers.RandomContrast(0.2)
])

# Pre-trained model (EfficientNetB0)
base_model = tf.keras.applications.EfficientNetB0(
    include_top=False, weights='imagenet', input_shape=(img_height, img_width, 3)
)

base_model.trainable = False

# Model architecture
model = Sequential([
    data_augmentation,
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(len(train_ds.class_names), activation='softmax')
])

# Compile the model
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Set a random seed for reproducibility
seed = 123
tf.random.set_seed(seed)
np.random.seed(seed)

# Early stopping callback
callbacks = tf.keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=3,
    restore_best_weights=True
)

# Train the model for more epochs
history = model.fit(train_ds, validation_data=val_ds, epochs=20, callbacks=[callbacks])


model.save("final_model")

