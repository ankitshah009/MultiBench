import sys
import os

sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
import torch

from fusions.common_fusions import Concat
from datasets.affect.get_data import get_dataloader

from training_structures.Supervised_Learning import train, test

from unimodals.MVAE import TSEncoder,TSDecoder
from unimodals.common_models import MLP
from torch import nn
from objective_functions.objectives_for_supervised_learning import MFM_objective
from utils.helper_modules import Sequential2

classes=2
n_latent=256
dim_0=35
dim_1=74
dim_2=300
timestep=50

# mosi_raw.pkl, mosei_raw.pkl, sarcasm.pkl, humor.pkl
traindata, validdata, test_robust = get_dataloader('/home/paul/MultiBench/mosi_raw.pkl', task='classification', robust_test=False, max_pad=True, max_seq_len=timestep)

encoders=[TSEncoder(dim_0,30,n_latent,timestep,returnvar=False).cuda(), TSEncoder(dim_1,30,n_latent,timestep,returnvar=False).cuda(), TSEncoder(dim_2,30,n_latent,timestep,returnvar=False).cuda()]

decoders=[TSDecoder(dim_0,30,n_latent,timestep).cuda(), TSDecoder(dim_1,30,n_latent,timestep).cuda(), TSDecoder(dim_2,30,n_latent,timestep).cuda()]

fuse=Sequential2(Concat(),MLP(3*n_latent,n_latent,n_latent//2)).cuda()

intermediates=[MLP(n_latent,n_latent//2,n_latent//2).cuda(),MLP(n_latent,n_latent//2,n_latent//2).cuda(),MLP(n_latent,n_latent//2,n_latent//2).cuda()]

head=MLP(n_latent//2,20,classes).cuda()

argsdict = {'decoders':decoders,'intermediates':intermediates}

additional_modules=decoders+intermediates

objective=MFM_objective(2.0,[torch.nn.MSELoss(),torch.nn.MSELoss(),torch.nn.MSELoss()],[1.0,1.0,1.0])

train(encoders,fuse,head,traindata,validdata,200,additional_modules,objective=objective,objective_args_dict=argsdict, save='mosi_mfm_best.pt')

print("Testing:")
model = torch.load('mosi_mfm_best.pt').cuda()

test(model=model, test_dataloaders_all=test_robust, dataset='mosi', is_packed=False)
