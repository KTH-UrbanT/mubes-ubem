# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import numpy as np
import math
import os


def BetaDistVal(min,max):
    Val = min + (np.random.beta(2, 1.3) * (max - min))
    return Val

def sigmoid(x,coef):
  return 1 / (1 + math.exp(-x*coef))

def NormVar(x):
    try:
        var = [((i-min(x))/(max(x)-min(x))) for i in x]
    except:
        var = x
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

def BuildTempSetPoints(name,path,Values,Hours):
    #we always start on midnight
    SetPoint =[]
    FirstDayofWeek = 0 #the first day is a Monday
    for i in range(8760):
        HrperDay = i%24                 #this will gives us values between 0 and 24hours
        DayofWeek = (int(i % (24 * 7) / 24) + FirstDayofWeek)%7 # this will give the day of the week (0 is for Mondays)
        WE = False if DayofWeek < 5 else True  #this will gove a 1 when we are on weekends
        if HrperDay<int(Hours[0][:Hours[0].find(':')]) or HrperDay>int(Hours[1][:Hours[1].find(':')]):# or WE:
            SetPoint.append(float(Values[1]))
        else:
            SetPoint.append(float(Values[0]))
    Write2file(SetPoint,os.path.join(path,name))

def BuildOccupancyFile(name,path,min,max,building):
    #we always start on midnight
    nbocc = []
    FirstDayofWeek = 0 #the first day is a Monday
    for i in range(8760):
        HrperDay = i%24                 #this will gives us values between 0 and 24hours
        DayofWeek = (int(i % (24 * 7) / 24) + FirstDayofWeek)%7 # this will give the day of the week (0 is for Mondays)
        WE = False if DayofWeek < 5 else True  #this will gove a 1 when we are on weekends
        if HrperDay<int(building.Office_Open[:building.Office_Open.find(':')]) or HrperDay>int(building.Office_Close[:building.Office_Close.find(':')]):# or WE:
            nbocc.append(0)
        else:
            nbocc.append(BetaDistVal(min,max))
    Write2file(nbocc,os.path.join(path,name))

if __name__ == '__main__' :
    print('ProbGenerator Main')