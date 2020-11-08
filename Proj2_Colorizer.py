import cv2
import glob
import os
import torch
import numpy as np
from torchvision import transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score

from ColorNet import ColorNet

#Boolean, true if you have a trained model to load.
loadModel = False
ModelPath = '/Users/nkroeger/Documents/UF_Grad/2020\ Fall/DL4CG/Part2/DeepColorization'

torch.manual_seed(0)
# torch.set_default_tensor_type('torch.FloatTensor')
torch.set_default_tensor_type('torch.DoubleTensor')

def scale_transform(image):
	rand = np.random.uniform(low = 0.6, high = 1.0)
	image[0,:,:] = image[0,:,:]*rand
	image[1,:,:] = image[1,:,:]*rand
	image[2,:,:] = image[2,:,:]*rand
	return image

def show_image(image):
	image = np.uint8(torch.squeeze(image.permute(1, 2, 0)))
	# import pdb; pdb.set_trace()
	switched = [2,1,0]
	image = image[:,:,switched]
	imgplot = plt.imshow(image)

	plt.show()
	print("Image displayed")


#750 images. 750 x 3 x 128 x 128
NumImages = 750
data = torch.empty(NumImages, 3, 128, 128)
c = 0
for file in glob.glob('face_images/*.jpg'):
	img = cv2.imread(file) #B, G, R
	img = torch.from_numpy(np.asarray(img))
	img = img.permute(2, 0, 1)
	data[c, :, :, :] = img
	c = c + 1

RandomIndices = torch.randperm(NumImages)
data = data[RandomIndices, :, :, :]


### test train split ###
NumTrainImages = 675
NumTestImages = 75

train = data[:675, :, :, :]
test = data[675:, :, :, :]

### data aug ###
trainset = torch.empty(NumTrainImages*10, 3, 128, 128)
trainset[:675, :, :, :] = train
# horizontal_flip

horizontal_transform = transforms.Compose([
	    #transforms.ToPILImage(),
	    transforms.RandomHorizontalFlip(p=1.0),
	    #transforms.ToTensor()
	])
c = 0
for i in np.arange(NumTrainImages, 4*NumTrainImages, 3):

	trainset[i, :, :, :] = horizontal_transform(data[c, :, :, :])
	trainset[i+1, :, :, :] = horizontal_transform(data[c, :, :, :])
	trainset[i+2, :, :, :] = horizontal_transform(data[c, :, :, :])
	c = c + 1

crop_transform = transforms.Compose([
	    #transforms.ToPILImage(),
	    transforms.RandomResizedCrop(128,scale = (0.5,1.0),ratio = (1.0,1.0)),
	    #transforms.ToTensor()
	])

c = 0
for i in np.arange(4*NumTrainImages, 7*NumTrainImages, 3):

	trainset[i, :, :, :] = crop_transform(data[c, :, :, :])
	trainset[i+1, :, :, :] = crop_transform(data[c, :, :, :])
	trainset[i+2, :, :, :] = crop_transform(data[c, :, :, :])
	c = c + 1

c = 0
for i in np.arange(7*NumTrainImages, 10*NumTrainImages, 3):

	trainset[i, :, :, :] = scale_transform(torch.squeeze(data[c, :, :, :]))
	trainset[i+1, :, :, :] = scale_transform(torch.squeeze(data[c, :, :, :]))
	trainset[i+2, :, :, :] = scale_transform(torch.squeeze(data[c, :, :, :]))
	c = c + 1
# show_image(trainset[1,:,:,:])
# show_image(torch.squeeze(trainset[678,:,:,:]))
# show_image(torch.squeeze(trainset[6749,:,:,:]))
# show_image(torch.squeeze(trainset[4700,:,:,:]))

### Convert from RGB to LAB for TRAIN SET ###
trainset_LAB = np.zeros((NumTrainImages*10, 128,128,3))
for i in range(0,NumTrainImages*10):
	trainset_img = torch.squeeze(trainset[i,:,:,:])
	trainset_img = trainset_img.permute(1, 2, 0)
	trainset_LAB[i,:,:,:] = cv2.cvtColor(np.float32(trainset_img.numpy()), cv2.COLOR_BGR2LAB)

### Convert from RGB to LAB for TEST SET ###
for i in range(NumTestImages):
    testset_img = torch.squeeze(test[i,:,:,:])
    testset_img = testset_img.permute(1, 2, 0)
    testset_LAB[i,:,:,:] = cv2.cvtColor(np.float32(testset_img.numpy()), cv2.COLOR_BGR2LAB)

### Convert LAB to data & labels FOR TRAIN SET ###
trainset_LAB          = torch.from_numpy(trainset_LAB)
trainset_L_channel    = np.zeros((NumTrainImages*10, 1, 128, 128))
trainset_a_b_channels = np.zeros((NumTrainImages*10, 2, 128, 128))
for i in range(0, NumTrainImages*10):
	temp_squeezed_img = torch.squeeze(trainset_LAB[i,:,:,:]) #[1,128,128,3] -> [128,128,3]

	#Split LAB channels into their own variables
	trainset_L_channel[i,:,:,:], a_channel[i,:,:,:], b_channel[i,:,:,:] = cv2.split(np.float32(temp_squeezed_img))

	#Normalize L channel from [0,100] -> [0,1]
	trainset_L_channel[i,:,:,:] = trainset_L_channel[i,:,:,:]/100.0
	#Normalize a channel from [-110,110] -> [-1,1]
	trainset_a_b_channels[i,0,:,:] = (2.0*(a_channel[i,:,:,:] + 110.0)/220.0) - 1.0
	#Normalize b channel from [-110,110] -> [-1,1]
	trainset_a_b_channels[i,1,:,:] = (2.0*(b_channel[i,:,:,:] + 110.0)/220.0) - 1.0
#Convert to torch
trainset_L_channel    = torch.from_numpy(trainset_L_channel)
trainset_a_b_channels = torch.from_numpy(trainset_a_b_channels)


### Convert LAB to data & labels FOR TEST SET ###
testset_LAB          = torch.from_numpy(testset_LAB)
testset_L_channel    = np.zeros((NumTestImages, 1, 128, 128))
testset_a_b_channels = np.zeros((NumTestImages, 2, 128, 128))
for i in range(0, NumTestImages):
	temp_squeezed_img = torch.squeeze(testset_LAB[i,:,:,:]) #[1,128,128,3] -> [128,128,3]

	#Split LAB channels into their own variables
	testset_L_channel[i,:,:,:], a_channel[i,:,:,:], b_channel[i,:,:,:] = cv2.split(np.float32(temp_squeezed_img))

	#Normalize L channel from [0,100] -> [0,1]
	testset_a_b_channels[i,:,:,:] = testset_L_channel[i,:,:,:]/100.0
	#Normalize a channel from [-110,110] -> [-1,1]
	testset_a_b_channels[i,0,:,:] = (2.0*(a_channel[i,:,:,:] + 110.0)/220.0) - 1.0
	#Normalize b channel from [-110,110] -> [-1,1]
	testset_a_b_channels[i,1,:,:] = (2.0*(b_channel[i,:,:,:] + 110.0)/220.0) - 1.0
#Convert to torch
testset_L_channel    = torch.from_numpy(testset_L_channel)
testset_a_b_channels = torch.from_numpy(testset_a_b_channels)


### TRAINING ###
# Colorizer
def train_Colorizer(ColorModel, optimizer, loss, L_channel, a_b_channels):
	tr_loss = 0
	if torch.cuda.is_available():
		L_channel = L_channel.cuda()
		a_b_channels = a_b_channels.cuda()

	optimizer.zero_grad()
	pred = ColorNet(L_channel)

	predError = loss(pred, a_b_channels)
	predError.backward()
	optimizer.step()

	tr_loss = predError.item()
	print("Loss: " ,tr_loss)
	train_loss.append(tr_loss)

ColorModel = ColorNet()
optimizer  = torch.optim.Adam(ColorModel.parameters(), lr=0.01)
loss       = torch.nn.MSELoss()

if torch.cuda.is_available():
	ColorModel = ColorModel.cuda()
	loss = loss.cuda()

train_loss = []
epochs  = 100
BatchSize = 10
#Train over several epochs
for i in range(0, epochs):
	print("epoch: ", i+1 )
    #Get batches of size: BatchSize
    for i in np.arange(0, NumTrainImages*10, BatchSize):
        L_channel_batch    = trainset_L_channel[i:(i+10), :, :, :]
        a_b_channels_batch = trainset_a_b_channels[i:(i+10), :, :, :]
        train_Colorizer(ColorModel, optimizer, loss, L_channel_batch, a_b_channels_batch)

#Plot training error
plt.plot(train_loss)
plt.ylabel("Train error")
plt.xlabel("Epochs")
plt.savefig("Colorizer_Loss.png")

###
#Save the model
torch.save(ColorModel.state_dict(), ModelPath)

#Load model
if loadModel == True:
    ColorModel = ColorNet()
    ColorModel.torch.load(ModelPath)

###
#Prediction on test set
ColorModel.eval() #Since we have batchnorm layers
with torch.no_grad(): #Don't update the weights
    if torch.cuda.is_available():
        testset_L_channel = testset_L_channel.cuda()
    pred = model(testset_L_channel)

# test set loss
testSetLoss = loss(pred, testset_a_b_channels)


# Merge LAB channels, ronvert to RGB and visualize