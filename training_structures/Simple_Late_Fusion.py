from tqdm import tqdm

from sklearn.metrics import accuracy_score, f1_score
import torch
from torch import nn
from torch.nn import functional as F
from torch.optim.lr_scheduler import ExponentialLR

from utils.AUPRC import AUPRC
from objective_functions.regularization import RegularizationLoss
#import pdb

softmax = nn.Softmax()

class MMDL(nn.Module):
    def __init__(self,encoders,fusion,head,has_padding=False):
        super(MMDL,self).__init__()
        self.encoders = nn.ModuleList(encoders)
        self.fuse = fusion
        self.head = head
        self.has_padding=has_padding
    
    def forward(self,inputs,training=False):
        outs = []
        if self.has_padding:
            for i in range(len(inputs[0])):
                outs.append(self.encoders[i]([inputs[0][i],inputs[1][i]], training=training))
        else:
            for i in range(len(inputs)):
                outs.append(self.encoders[i](inputs[i], training=training))
        out = self.fuse(outs, training=training)
        return self.head(out, training=training)


def train(
    encoders,fusion,head,train_dataloader,valid_dataloader,total_epochs,is_packed=False,
    early_stop=False,task="classification",optimtype=torch.optim.RMSprop,lr=0.001,weight_decay=0.0,
    criterion=nn.CrossEntropyLoss(),regularization=False,auprc=False,save='best.pt'):
    
    model = MMDL(encoders,fusion,head,is_packed).cuda()
    op = optimtype(model.parameters(),lr=lr,weight_decay=weight_decay)
    #scheduler = ExponentialLR(op, 0.9)
    bestvalloss = 10000
    bestacc = 0
    bestf1 = 0
    patience = 0
    
    if regularization:
        regularize = RegularizationLoss(criterion, model, 1e-11)
    
    for epoch in range(total_epochs):
        totalloss = 0.0
        totalloss1 = 0.0
        totalloss2 = 0.0
        totals = 0
        model.train()
        for j in train_dataloader:
            #print([i for i in j[:-1]])
            op.zero_grad()
            if is_packed:
                with torch.backends.cudnn.flags(enabled=False):
                    out=model([[i.cuda() for i in j[0]], j[1]],training=True)
                    #print(j[-1])
                    loss1=criterion(out,j[-1].cuda())
                    loss2=regularize(out, [[i.cuda() for i in j[0]], j[1]]) if regularization else 0
                    loss = loss1+loss2
            else:
                out=model([i.float().cuda() for i in j[:-1]],training=True)
                #print(out, j[-1])
                loss=criterion(out,j[-1].float().cuda())
            totalloss += loss * len(j[-1])
            totals+=len(j[-1])
            if regularization:
                totalloss1 += loss1 * len(j[-1])
                totalloss2 += loss2 * len(j[-1])
                loss.backward(retain_graph=True)
            else:
                loss.backward()
            op.step()
        if regularization:
            print("Epoch "+str(epoch)+" train loss: "+str(totalloss1/totals)+" reg loss: "+str(totalloss2/totals))
        else:
            print("Epoch "+str(epoch)+" train loss: "+str(totalloss/totals))
        
        model.eval()
        with torch.no_grad():
            totalloss = 0.0
            pred = []
            true = []
            pts = []
            for j in valid_dataloader:
                if is_packed:
                    out=model([[i.cuda() for i in j[0]], j[1]],training=False)
                else:
                    out = model([i.float().cuda() for i in j[:-1]],training=False)
                loss = criterion(out,j[-1].float().cuda())
                totalloss += loss*len(j[-1])
                if task == "classification":
                    pred.append(torch.argmax(out, 1))
                elif task == "multilabel":
                    pred.append(torch.sigmoid(out).round())
                true.append(j[-1])
                if auprc:
                    #pdb.set_trace()
                    sm=softmax(out, 1)
                    pts += [(sm[i][1].item(), j[-1][i].item()) for i in range(j[-1].size(0))]
        true = torch.cat(true, 0).cpu().numpy()
        pred = torch.cat(pred, 0).cpu().numpy()
        totals = true.shape[0]
        valloss=totalloss/totals
        if task == "classification":
            acc = accuracy_score(true, pred)
            print("Epoch "+str(epoch)+" valid loss: "+str(valloss)+\
                " acc: "+str(acc))
            if acc>bestacc:
                patience = 0
                bestacc=acc
                print("Saving Best")
                torch.save(model,save)
            else:
                patience += 1
            if early_stop and patience > 20:
                break
        elif task == "multilabel":
            f1_micro = f1_score(true, pred, average="micro")
            f1_macro = f1_score(true, pred, average="macro")
            print("Epoch "+str(epoch)+" valid loss: "+str(valloss)+\
                " f1_micro: "+str(f1_micro)+" f1_macro: "+str(f1_macro))
            if f1_macro>bestf1:
                patience = 0
                bestf1=f1_macro
                print("Saving Best")
                torch.save(model,save)
            else:
                patience += 1
            if early_stop and patience > 20:
                break
        elif task == "regression":
            print("Epoch "+str(epoch)+" valid loss: "+str(valloss))
            if valloss<bestvalloss:
                patience = 0
                bestvalloss=valloss
                print("Saving Best")
                torch.save(model,save)
            else:
                patience += 1
            if early_stop and patience > 20:
                break
        if auprc:
            print("AUPRC: "+str(AUPRC(pts)))
        
        #scheduler.step()


def test(
    model,test_dataloader,is_packed=False,
    criterion=nn.CrossEntropyLoss(),task="classification",auprc=False):
    with torch.no_grad():
        totalloss = 0.0
        pred=[]
        true=[]
        pts=[]
        for j in test_dataloader:
            if is_packed:
                out=model([[i.cuda() for i in j[0]], j[1]],training=False)
            else:
                out = model([i.float().cuda() for i in j[:-1]],training=False)
            loss = criterion(out,j[-1].float().cuda())
            #print(torch.cat([out,j[-1].cuda()],dim=1))
            totalloss += loss*len(j[-1])
            if task == "classification":
                pred.append(torch.argmax(out, 1))
            elif task == "multilabel":
                pred.append(torch.sigmoid(out).round())
            true.append(j[-1])
            if auprc:
                #pdb.set_trace()
                sm=softmax(out, 1)
                pts += [(sm[i][1].item(), j[-1][i].item()) for i in range(j[-1].size(0))]
        true = torch.cat(true, 0).cpu().numpy()
        pred = torch.cat(pred, 0).cpu().numpy()
        totals = true.shape[0]
        testloss=totalloss/totals
        if task == "classification":
            print("acc: "+str(accuracy_score(true, pred)))
        elif task == "multilabel":
            print(" f1_micro: "+str(f1_score(true, pred, average="micro"))+\
                " f1_macro: "+str(f1_score(true, pred, average="macro")))
        elif task == "regression":
            print("mse: "+str(testloss))
        if auprc:
            print("AUPRC: "+str(AUPRC(pts)))

