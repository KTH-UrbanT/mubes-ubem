import numpy as np
import math
import os


def BetaDistVal(min,max):
    Val = min + (np.random.beta(2, 1.3) * (max - min))
    return Val

def sigmoid(x,coef):
  return 1 / (1 + math.exp(-x*coef))

def NormVar(x):
    var = [((i-min(x))/(max(x)-min(x))) for i in x]
    return var

def SigmoFile(Season,width,AnnualLoad,name):
    x = np.linspace(-1, 1, 8761)
    y = NormVar([sigmoid(i,width) for i in x])
    Conso = AnnualLoad
    if 'Summer' in Season:
        time = [i*(8760/2)+(8760/2) for i in x]
        val = [Conso*i for i in y]
        dval = np.diff(val)
    else:
        p1 = [i - 0.5 for i in y[round(len(y) / 2):]]
        p2 = [i + 0.5 for i in y[1:round(len(y) / 2)]]
        y1 = p1 + p2
        time = [i*8760 for i in y]
        val = [Conso*i for i in y1]
        val.append(val[-1])
        dval = np.diff(val)
    Write2file(dval, name)


def Write2file(val,name):
    with open(name, 'w') as f:
        for item in val:
            f.write("%s\n" % item)

def BuildData(name,path,min,max,building):
    #we alsways start on midnight
    nbocc = []
    TsetUp =[]
    TsetLo = []
    FirstDayofWeek = 0 #the foirst day is a Monday
    for i in range(8760):
        HrperDay = i%24                 #this will gives us values between 0 and 24hours
        DayofWeek = int(i % (24 * 7) / 24) + FirstDayofWeek # this will give the day of the week (0 is for Mondays)
        WE = False if DayofWeek < 6 else True  #this will gove a 1 when we are on weekends
        if HrperDay<int(building.Officehours[0][:building.Officehours[0].find(':')]) or HrperDay>int(building.Officehours[1][:building.Officehours[1].find(':')]):# or WE:
            nbocc.append(0)
            TsetUp.append(50)
            TsetLo.append(21)
        else:
            nbocc.append(BetaDistVal(min,max))
            TsetUp.append(50)
            TsetLo.append(21)
    Write2file(nbocc,path+name)
    Write2file(TsetUp,path+'SetPointUp.txt')
    Write2file(TsetLo,path+'SetPointLo.txt')

if __name__ == '__main__' :
    print('ProbGenerator Main')