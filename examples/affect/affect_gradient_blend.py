import sys
import os

sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
import torch
from torch import nn

from fusions.common_fusions import Concat
from datasets.affect.get_data import get_dataloader
from unimodals.common_models import GRU, MLP, Transformer

from training_structures.gradient_blend import train, test
import training_structures

from private_test_scripts.all_in_one import all_in_one_train

# mosi_raw.pkl, mosei_raw.pkl, sarcasm.pkl, humor.pkl
traindata, validdata, test_robust = \
    get_dataloader('/home/paul/MultiBench/mosi_raw.pkl', task='classification', robust_test=True, max_pad=True)

# mosi/mosei
encoders=[Transformer(35,70).cuda(), \
    Transformer(74,150).cuda(),\
    Transformer(300,600).cuda()]
head=MLP(820,512,2).cuda()

unimodal_heads=[MLP(70,32,2).cuda(),MLP(150,64,2).cuda(),MLP(600,256,2).cuda()]

# humor/sarcasm
# encoders=[GRU(371,512,dropout=True,has_padding=True).cuda(), \
#     GRU(81,256,dropout=True,has_padding=True).cuda(),\
#     GRU(300,600,dropout=True,has_padding=True).cuda()]
# head=MLP(1368,512,1).cuda()

fusion = Concat().cuda()

# training_structures.gradient_blend.criterion = nn.L1Loss()

train(encoders, head, unimodal_heads, fusion, traindata, validdata, 100, gb_epoch=20, lr=1e-3, AUPRC=False, classification=True, optimtype=torch.optim.AdamW, savedir='mosi_best_gb.pt', weight_decay=0.1)

print("Testing:")
model = torch.load('mosi_besf_gb.pt').cuda()

test(model, test_robust, dataset='mosi', auprc=False)

# test(model=model, test_dataloaders_all=test_robust, dataset='mosi', is_packed=True, criterion=torch.nn.L1Loss(), task='posneg-classification')
