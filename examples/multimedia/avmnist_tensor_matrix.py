import sys
import os
sys.path.append(os.getcwd())
from training_structures.Supervised_Learning import train, test
from fusions.common_fusions import Concat,MultiplicativeInteractions2Modal
from datasets.avmnist.get_data import get_dataloader
from unimodals.common_models import LeNet,MLP,Constant
from torch import nn
import torch

traindata, validdata, testdata = get_dataloader('/home/pliang/yiwei/avmnist/_MFAS/avmnist')
channels=3
encoders=[LeNet(1,channels,3).cuda(),LeNet(1,channels,5).cuda()]
head=MLP(channels*32,100,10).cuda()

fusion=MultiplicativeInteractions2Modal([channels*8,channels*32],channels*32,'matrix',True).cuda()
#fusion=MultiplicativeInteractions2Modal([channels*32,channels*8],channels*32,'vector',True,flip=True).cuda()

train(encoders,fusion,head,traindata,validdata,100,optimtype=torch.optim.SGD,lr=0.01,weight_decay=0.0001)

print("Testing:")
model=torch.load('best.pt').cuda()
test(model,testdata,no_robust=True)


