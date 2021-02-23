#this file is just a tank of utilities for ploting stuff mainly.
#It creates the figures and the plots

import matplotlib.pyplot as plt
from matplotlib import gridspec

#this function enable to create a two subplots figure with ratio definition between the two plots
def createDualFig(title,ratio):
    fig_name = plt.figure()
    gs = gridspec.GridSpec(10,1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:round(ratio*10), 0])
    ax0.grid()
    ax1 = plt.subplot(gs[round(ratio*10)+1:, 0])
    ax1.grid()
    plt.tight_layout()
    plt.title(title)
    return {'fig_name' : fig_name, 'ax0': ax0, 'ax1' : ax1}

#this function enable to create a single graph areas
def createSimpleFig():
    fig_name = plt.figure()
    gs = gridspec.GridSpec(4, 1, left=0.1, bottom = 0.1)
    ax0 = plt.subplot(gs[:, 0])
    ax0.grid()
    plt.tight_layout()
    return {'fig_name' : fig_name, 'ax0': ax0}

#basic plots
def plotBasicGraph(fig_name,ax0,varx,vary,varxname,varyname,title,sign):
    plt.figure(fig_name)
    ax0.plot(varx, vary,sign,label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    plt.title(title)

#this plots variables realtively to their maximum value
def plotRelative2Max(fig_name,ax0,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    relval = [vary[i] / max(vary) for i in range(len(vary))]
    ax0.plot(varx, relval,label= varyname)
    ax0.set_xlabel(varxname)
    ax0.legend()
    print(min(relval))

#this plots variables dimensioless values (from 0-1)
def plotDimLess(fig_name,ax0,varx,vary,varxname,varyname,varname):
    plt.figure(fig_name)
    xval = [(varx[i] -min(varx)) / (max(varx)-min(varx)) for i in range(len(varx))]
    yval = [(vary[i] - min(vary)) / (max(vary) - min(vary)) for i in range(len(vary))]
    ax0.plot(xval, yval,'.',label= varname)
    ax0.set_xlabel(varxname)
    ax0.set_ylabel(varyname)
    ax0.legend()

#this plots in 2 subplots basic values and error, vary is thus a list of list, the first one being the reference
def plotBasicWithError(fig_name,ax0,ax1,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    for id,xvar in enumerate(vary):
        ax0.plot(varx, vary[id], 's',label= varyname[id])
    ax0.legend()
    ax0.set_xlabel(varxname)
    for id,xvar in enumerate(vary):
        ax1.plot(varx, [(vary[id][i] - vary[0][i]) / vary[0][i] * 100 for i in range(len(vary[0]))], 'x')

#this one I don't really get it yet...why I have done this....
def plot2Subplots(fig_name,ax0,ax1,varx,vary,varxname,varyname):
    plt.figure(fig_name)
    ax = [ax0,ax1]
    for i in len(varx):
        ax[i].plot(varx[i], vary[i])
        ax[i].set_xlabel(varxname)
        ax[i].set_ylabel(varyname)
        ax[i].grid()